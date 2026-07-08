"""
AllSides crawler — unified CLI.
================================
One tool for everything that used to be spread over full_scrape.py,
repair_dataset.py, fix_remaining_summaries.py and refresh_images.py
(pre-merge originals archived in Qbias/archive/allsides_crawler_pre_merge/).

Subcommands
-----------
crawl           Scrape the AllSides balanced-news feed into a jsonl
                (listing pages → story pages → featured L/C/R + more_*).
                Uses the CURRENT page markup for story summaries, so it
                does not reproduce the old 163-char truncation bug.
repair          Fix an existing jsonl: restore truncated story summaries,
                backfill missing stance image links, and download every
                featured stance image to output/images/<slug>/<stance>/.
fix-summaries   Whitespace-insensitive retry for summaries the strict
                repair pass missed (AllSides HTML can split words).
refresh-images  Re-fetch story pages for entries whose stored image URL
                died on the CDN, and download the current image instead.

Typical usage
-------------
    python allsides_crawler.py crawl --start 2026-06-01 --end 2026-12-31
    python allsides_crawler.py repair
    python allsides_crawler.py fix-summaries
    python allsides_crawler.py refresh-images

repair / fix-summaries / refresh-images operate in place on the canonical
dataset (default: output/allsides_jan2025_may2026.jsonl) and write a
.jsonl.bak of the previous version first. All long passes are resumable:
`repair` keeps output/repair_checkpoint.json and skips images already on
disk; interrupted runs continue where they left off.

Requires: curl_cffi (Cloudflare bypass), beautifulsoup4, aiohttp, tqdm.
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import aiohttp
from bs4 import BeautifulSoup
from curl_cffi import requests

# ── Configuration ────────────────────────────────────────────────────────────

BASE = "https://www.allsides.com"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
DATASET = OUTPUT_DIR / "allsides_jan2025_may2026.jsonl"
CHECKPOINT = OUTPUT_DIR / "repair_checkpoint.json"
IMAGES_DIR = OUTPUT_DIR / "images"

STANCES = ["left", "center", "right"]
MAX_FILENAME_LEN = 120
IMG_CONCURRENCY = 12
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

TAG_PREFIXES = [
    ("Fact Check", "FACT CHECK"),
    ("Analysis", "ANALYSIS"),
    ("Opinion", "OPINION"),
    ("News", "NEWS"),
]
OPEN_ON_RE = re.compile(r"(Open on .+?)(?:Possible Paywall)?$")

_lock = threading.Lock()


# ── HTTP ─────────────────────────────────────────────────────────────────────

def make_session():
    return requests.Session(impersonate="chrome")


def get_with_retry(session, url: str, attempts: int = 3, delay: float = 0.0):
    """GET with backoff; raises on final failure so callers never mistake a
    failed fetch for an empty page."""
    last_err = None
    for a in range(attempts):
        try:
            r = session.get(url, timeout=45)
            if delay:
                time.sleep(delay)
            if r.status_code == 200:
                return r
            last_err = RuntimeError(f"HTTP {r.status_code}")
        except Exception as e:
            last_err = e
        time.sleep(5 * (a + 1))
    raise last_err


def fetch_soup(session, url: str, delay: float = 0.0) -> BeautifulSoup:
    return BeautifulSoup(get_with_retry(session, url, delay=delay).text, "html.parser")


# ── Parsing helpers (shared by crawl and repair paths) ───────────────────────

def slug_of(story: dict) -> str:
    return story.get("headline_link", "").rstrip("/").split("/")[-1]


def is_truncated(summary: str) -> bool:
    return bool(summary) and summary.rstrip().endswith("...")


def norm_ws(t: str) -> str:
    return re.sub(r"\s+", "", t)


def parse_date(raw: str) -> str:
    cleaned = re.sub(r"^.*?•\s*", "", raw)
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", cleaned).strip()
    try:
        return datetime.strptime(cleaned, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def parse_bias(img_src: str) -> str:
    if not img_src:
        return "unknown"
    name = img_src.rsplit("/", 1)[-1].lower()
    if "leaning-left" in name:
        return "lean left"
    if "leaning-right" in name:
        return "lean right"
    if "bias-left" in name:
        return "left"
    if "bias-right" in name:
        return "right"
    if "center" in name:
        return "center"
    return "unknown"


def extract_story_summary(soup) -> str:
    """Full story description from the current markup.

    The description lives in a `div.editor-content`; when several exist, the
    right one starts with the same text as the SEO meta description. Falls
    back to the legacy selector, then to the (truncated) meta tag.
    """
    meta = soup.find("meta", attrs={"name": "description"})
    meta_txt = meta.get("content", "").strip() if meta else ""
    divs = soup.find_all("div", class_="editor-content")
    if divs:
        key = norm_ws(meta_txt[:80].removesuffix("...")) if meta_txt else ""
        for div in divs:
            text = re.sub(r"\s+", " ", div.get_text(" ", strip=True))
            if not key or norm_ws(text).startswith(key):
                if len(text) >= len(meta_txt):
                    return text
    legacy = soup.find("div", class_=lambda c: c and "story-id-page-description" in c)
    if legacy:
        return legacy.get_text(strip=True)
    return meta_txt


def parse_article_from_item(item) -> dict:
    headline_el = item.find("div", class_=lambda c: c and "leading-tight" in c)
    headline = headline_el.get_text(strip=True) if headline_el else ""
    link_el = item.find("a", href=lambda h: h and "/news/" in h)
    allsides_path = link_el["href"] if link_el else ""
    allsides_link = (BASE + allsides_path) if allsides_path.startswith("/") else allsides_path
    source_el = item.find("p", class_=lambda c: c and "news-source" in c)
    source = source_el.get_text(strip=True) if source_el else ""
    bias_img = item.find("img", alt=lambda a: a and "Bias" in str(a))
    rating_img = bias_img["src"] if bias_img else ""
    news_type_el = item.find(class_=lambda c: c and "news-type" in str(c))
    news_type = news_type_el.get_text(strip=True) if news_type_el else ""
    return {
        "headline": headline, "source": source, "allsides_link": allsides_link,
        "rating_img": rating_img, "rating": parse_bias(rating_img),
        "news_type": news_type,
    }


def parse_featured_from_container(soup) -> dict:
    featured = {}
    container = soup.find("div", class_=lambda c: c and "gap-5" in c and "mb-8" in c)
    if not container:
        return featured

    for child in container.children:
        if not (hasattr(child, "name") and child.name == "div"):
            continue
        if not child.find("div", class_=lambda c: c and "global-bias-label" in c):
            continue
        stance_cls = [c for c in child.get("class", []) if c in STANCES]
        if not stance_cls or stance_cls[0] in featured:
            continue
        stance = stance_cls[0]

        headline = ext_link = source = rating_img_url = image_link = summary = ""
        for a in child.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if "/news-source/" in href:
                if text and text != "See rating details":
                    source = text
            elif text.startswith("Open on "):
                if not ext_link:
                    ext_link = href
            elif text and not headline:
                headline = text
                ext_link = href

        img = child.find("img", alt=lambda a: a and "Bias" in str(a))
        if img:
            rating_img_url = img.get("src", "")
        article_img = child.find("img", alt=lambda a: a and "Bias" not in str(a))
        if article_img:
            image_link = article_img.get("src", "")

        for cd in child.find_all("div", class_=lambda c: c and "mt-4" in c):
            text = cd.get_text(strip=True)
            if text and not text.startswith("Open on") and len(text) > 10:
                summary = text
                break

        featured[stance] = {
            "source": source, "headline": headline, "link": ext_link,
            "rating_img": rating_img_url, "rating": parse_bias(rating_img_url),
            "summary": summary, "image_link": image_link, "news_type": "",
        }
    return featured


def fetch_article_details(session, allsides_link: str, delay: float = 0.0) -> dict:
    result = {"link": "", "summary": "", "content": "", "image_link": ""}
    if not allsides_link:
        return result
    try:
        soup = fetch_soup(session, allsides_link, delay=delay)
        ext = soup.find("a", string=lambda t: t and "Read Full Story" in str(t))
        if ext:
            result["link"] = ext.get("href", "")
        body = soup.find("div", class_="body")
        text = body.get_text(strip=True) if body else ""
        result["summary"] = text
        result["content"] = text
        pic = soup.find("picture")
        if pic:
            source = pic.find("source")
            if source:
                result["image_link"] = source.get("srcset", "")
    except Exception:
        pass
    return result


# ── Image download helpers ───────────────────────────────────────────────────

def sanitize(name: str) -> str:
    return re.sub(r"[^\w\-.]", "_", name)[:MAX_FILENAME_LEN]


def filename_from_url(url: str) -> str:
    basename = os.path.basename(unquote(urlparse(url).path)) or "image"
    basename = sanitize(basename)
    if not re.search(r"\.(jpg|jpeg|png|gif|webp|svg|bmp|avif)$", basename, re.I):
        basename += ".jpg"
    return f"000_{basename}"


def download_image(url: str, dest: Path) -> bool:
    """Synchronous single-image download (used by refresh-images)."""
    if dest.is_file() and dest.stat().st_size >= 100:
        return True
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            ctype = r.headers.get("Content-Type", "")
            if not (ctype.startswith("image/") or "octet-stream" in ctype):
                return False
            data = r.read()
        if len(data) < 100:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception:
        return False


# ── Dataset I/O ──────────────────────────────────────────────────────────────

def load_dataset(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path)]


def save_dataset(stories: list[dict], path: Path, backup: bool = True) -> None:
    if backup and path.is_file():
        shutil.copyfile(path, path.with_suffix(".jsonl.bak"))
    with open(path, "w") as f:
        for story in stories:
            f.write(json.dumps(story, ensure_ascii=False) + "\n")


# ══════════════════════════════════════════════════════════════════════════════
#  crawl — full scrape of the balanced-news feed
# ══════════════════════════════════════════════════════════════════════════════

def collect_story_urls(max_pages: int) -> list[dict]:
    session = make_session()
    all_stories, seen = [], set()
    for page in range(1, max_pages + 1):
        try:
            soup = fetch_soup(session, f"{BASE}/recent-headline-roundups?page={page}", delay=0.3)
        except Exception:
            break
        cards = soup.find_all("div", class_=lambda c: c and "clearfix" in c and "border-b" in c)
        if not cards:
            break
        new = 0
        for card in cards:
            h2 = card.find("h2")
            link_el = h2.find("a") if h2 else None
            if not link_el:
                continue
            href = link_el.get("href", "")
            if href in seen:
                continue
            seen.add(href)
            new += 1
            all_stories.append({
                "headline": link_el.get_text(strip=True),
                "headline_link": BASE + href if href.startswith("/") else href,
            })
        print(f"  listing page {page}: {len(all_stories)} stories so far", flush=True)
        if new == 0:
            break
    return all_stories


def process_story(story: dict, date_start: str, date_end: str,
                  delay: float, fetch_more: bool) -> dict | None:
    session = make_session()
    soup = fetch_soup(session, story["headline_link"], delay=delay)

    date_el = soup.find("p", class_=lambda c: c and "tracking-wide" in c) \
        or soup.find("p", class_=lambda c: c and "text-gray-500" in c)
    story["date"] = parse_date(date_el.get_text(strip=True)) if date_el else ""
    if not story["date"] or not (date_start <= story["date"] <= date_end):
        return None

    topic_el = soup.find("a", href=lambda h: h and "/topics/" in h)
    story["topic"] = (topic_el.get_text(strip=True).replace("News and Information about ", "")
                      if topic_el else "")
    story["topic_link"] = (BASE + topic_el["href"]) if topic_el else ""
    story["tags"] = [t.get_text(strip=True).rstrip(",").strip()
                     for t in soup.find_all("a", href=lambda h: h and "/tags/" in h)]
    story["summary"] = extract_story_summary(soup)

    featured = parse_featured_from_container(soup)

    items = soup.find_all("div", class_=lambda c: c and "news-item" in c)
    more_articles = {s: [] for s in STANCES}
    seen_headlines = {featured[s]["headline"] for s in featured if featured[s]["headline"]}
    for item in items:
        classes = item.get("class", [])
        for stance in STANCES:
            if stance in classes:
                art = parse_article_from_item(item)
                if art["headline"] and art["headline"] not in seen_headlines:
                    seen_headlines.add(art["headline"])
                    more_articles[stance].append(art)
                break

    for stance in STANCES:
        if stance not in featured and more_articles[stance]:
            first = more_articles[stance].pop(0)
            featured[stance] = {
                "source": first["source"], "headline": first["headline"],
                "link": "", "rating_img": first["rating_img"],
                "rating": first["rating"], "summary": "", "image_link": "",
                "news_type": first.get("news_type", ""),
                "_needs_fetch": True, "_allsides_link": first["allsides_link"],
            }

    for stance in STANCES:
        if stance in featured:
            feat = featured[stance]
            if feat.get("_needs_fetch"):
                details = fetch_article_details(session, feat.pop("_allsides_link"), delay=delay)
                feat.pop("_needs_fetch", None)
                feat["link"] = details["link"]
                feat["summary"] = details["summary"]
                feat["image_link"] = details["image_link"]
            story[stance] = feat
        else:
            story[stance] = ""

        more = []
        if fetch_more:
            for art_raw in more_articles.get(stance, []):
                details = fetch_article_details(session, art_raw["allsides_link"], delay=delay)
                more.append({
                    "source": art_raw["source"], "headline": art_raw["headline"],
                    "link": details["link"], "rating_img": art_raw["rating_img"],
                    "rating": art_raw["rating"], "image_link": details["image_link"],
                    "news_type": art_raw.get("news_type", ""),
                    "allsides_link": art_raw["allsides_link"], "content": details["content"],
                })
        story[f"more_{stance}"] = more
    return story


def clean_stance_summaries(records: list[dict]) -> dict:
    """Strip 'Open on <Source>' suffixes and tag prefixes from stance excerpts."""
    stats = {"tag_extracted": 0, "open_on_extracted": 0}
    for rec in records:
        for stance in STANCES:
            entry = rec.get(stance)
            if not isinstance(entry, dict) or not entry.get("summary"):
                continue
            summary = entry["summary"]
            news_type = entry.get("news_type", "")
            open_on_source = ""

            m = OPEN_ON_RE.search(summary)
            if m:
                open_on_source = m.group(1).replace("Open on ", "", 1)
                summary = summary[:m.start()].rstrip()
                stats["open_on_extracted"] += 1

            for prefix, nt_value in TAG_PREFIXES:
                if summary.startswith(prefix) and len(summary) > len(prefix):
                    nxt = summary[len(prefix)]
                    if nxt.isupper() or nxt == " ":
                        summary = summary[len(prefix):].lstrip()
                        news_type = news_type or nt_value
                        stats["tag_extracted"] += 1
                        break

            entry["summary"] = summary
            if news_type:
                entry["news_type"] = news_type
            if open_on_source:
                entry["open_on_source"] = open_on_source
    return stats


def cmd_crawl(args) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else \
        OUTPUT_DIR / f"allsides_crawl_{args.start}_{args.end}.jsonl"
    print(f"AllSides crawl {args.start} → {args.end}  |  workers={args.workers}")
    print(f"Output: {output_path}")

    stories = collect_story_urls(args.max_pages)
    if args.limit:
        stories = stories[: args.limit]
    print(f"{len(stories)} stories to process.")

    results, errors, skipped = [], 0, 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_story, s, args.start, args.end,
                             args.delay, not args.no_more): s for s in stories}
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                res = fut.result()
                if res is not None:
                    results.append(res)
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                print(f"  ERROR {futures[fut]['headline_link']}: {e}", file=sys.stderr)
            if i % 25 == 0:
                print(f"  {i}/{len(stories)} processed "
                      f"(kept {len(results)}, out-of-range {skipped}, errors {errors})",
                      flush=True)

    results.sort(key=lambda s: s.get("date", ""), reverse=True)
    clean = clean_stance_summaries(results)
    save_dataset(results, output_path, backup=output_path.is_file())

    n_trunc = sum(is_truncated(s.get("summary", "")) for s in results)
    print(f"\nDone. {len(results)} stories → {output_path}")
    print(f"  out-of-range: {skipped} | errors: {errors} | truncated summaries: {n_trunc}")
    print(f"  cleaned: {clean['tag_extracted']} tag prefixes, "
          f"{clean['open_on_extracted']} 'Open on' suffixes")


# ══════════════════════════════════════════════════════════════════════════════
#  repair — full summaries + missing image links + image download
# ══════════════════════════════════════════════════════════════════════════════

def needs_page_fetch(story: dict) -> bool:
    if is_truncated(story.get("summary", "")):
        return True
    return any(isinstance(story.get(s), dict) and not story[s].get("image_link")
               for s in STANCES)


def scrape_story_page(session, story: dict) -> dict:
    """Returns {"summary": str|None, "images": {stance: url}}."""
    out = {"summary": None, "images": {}}
    soup = fetch_soup(session, story["headline_link"])

    old = story.get("summary", "")
    if is_truncated(old):
        key = norm_ws(old[:80].removesuffix("..."))
        for div in soup.find_all("div", class_="editor-content"):
            text = re.sub(r"\s+", " ", div.get_text(" ", strip=True))
            if norm_ws(text).startswith(key) and len(text) > len(old):
                out["summary"] = text
                break

    featured = parse_featured_from_container(soup)
    for stance in STANCES:
        entry = story.get(stance)
        if isinstance(entry, dict) and not entry.get("image_link"):
            link = (featured.get(stance) or {}).get("image_link", "")
            if link:
                out["images"][stance] = link
    return out


def run_repair_phase1(stories: list[dict], workers: int, limit: int) -> dict:
    fixed: dict = {}
    if CHECKPOINT.is_file():
        fixed = json.loads(CHECKPOINT.read_text())
        print(f"Phase 1: resuming, {len(fixed)} story pages already scraped.")

    todo = [s for s in stories if needs_page_fetch(s) and slug_of(s) not in fixed]
    if limit:
        todo = todo[:limit]
    print(f"Phase 1: {len(todo)} story pages to fetch (workers={workers}).")

    counters = {"done": 0, "errors": 0}

    def worker(chunk):
        session = make_session()
        for story in chunk:
            try:
                res = scrape_story_page(session, story)
            except Exception as e:
                res = None
                print(f"  ERROR {story['headline_link']}: {e}", file=sys.stderr)
            with _lock:
                if res is not None:
                    fixed[slug_of(story)] = res
                    counters["done"] += 1
                else:
                    counters["errors"] += 1
                if counters["done"] % 50 == 0:
                    CHECKPOINT.write_text(json.dumps(fixed))
                    print(f"  {counters['done']}/{len(todo)} pages scraped "
                          f"({counters['errors']} errors) — checkpoint saved", flush=True)
            time.sleep(0.8)

    threads = [threading.Thread(target=worker, args=(c,))
               for c in (todo[i::workers] for i in range(workers)) if c]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    CHECKPOINT.write_text(json.dumps(fixed))
    print(f"Phase 1 done: {counters['done']} scraped, {counters['errors']} errors.")
    return fixed


def apply_repair_phase1(stories: list[dict], fixed: dict) -> None:
    n_sum = n_img = 0
    for story in stories:
        res = fixed.get(slug_of(story))
        if not res:
            continue
        if res.get("summary"):
            story["summary"] = res["summary"]
            n_sum += 1
        for stance, link in (res.get("images") or {}).items():
            entry = story.get(stance)
            if isinstance(entry, dict) and not entry.get("image_link"):
                entry["image_link"] = link
                n_img += 1
    print(f"Applied: {n_sum} full summaries, {n_img} backfilled image links.")


async def _download_one_async(session, sem, url: str, dest: Path) -> bool:
    async with sem:
        try:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return False
                ctype = resp.headers.get("Content-Type", "")
                if not (ctype.startswith("image/") or "octet-stream" in ctype):
                    return False
                data = await resp.read()
                if len(data) < 100:
                    return False
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                return True
        except Exception:
            return False


async def run_repair_phase2(stories: list[dict]) -> None:
    jobs = []
    for story in stories:
        slug = slug_of(story)
        for stance in STANCES:
            entry = story.get(stance)
            if not (isinstance(entry, dict) and entry.get("image_link")):
                continue
            url = entry["image_link"]
            if not url.startswith("http"):
                continue
            jobs.append((entry, url, IMAGES_DIR / slug / stance / filename_from_url(url)))
    print(f"Phase 2: {len(jobs)} featured images referenced.")

    pending = []
    for entry, url, dest in jobs:
        if dest.is_file() and dest.stat().st_size >= 100:
            entry["image_local_path"] = str(dest.relative_to(OUTPUT_DIR))
        else:
            pending.append((entry, url, dest))
    print(f"Phase 2: {len(jobs) - len(pending)} already on disk, {len(pending)} to download.")

    first_dest: dict[str, Path] = {}
    sem = asyncio.Semaphore(IMG_CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=45)
    ok = fail = 0
    async with aiohttp.ClientSession(timeout=timeout, headers=UA) as session:
        for i, (entry, url, dest) in enumerate(pending, 1):
            src = first_dest.get(url)
            if src and src.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
                entry["image_local_path"] = str(dest.relative_to(OUTPUT_DIR))
                ok += 1
            elif await _download_one_async(session, sem, url, dest):
                first_dest[url] = dest
                entry["image_local_path"] = str(dest.relative_to(OUTPUT_DIR))
                ok += 1
            else:
                fail += 1
            if i % 200 == 0:
                print(f"  {i}/{len(pending)} images ({fail} failed)", flush=True)
    print(f"Phase 2 done: {ok} images stored, {fail} failed.")


def cmd_repair(args) -> None:
    stories = load_dataset(Path(args.dataset))
    print(f"Loaded {len(stories)} stories from {args.dataset}.")

    fixed = run_repair_phase1(stories, args.workers, args.limit)
    apply_repair_phase1(stories, fixed)
    if not args.skip_images:
        asyncio.run(run_repair_phase2(stories))

    save_dataset(stories, Path(args.dataset))
    n_trunc = sum(is_truncated(s.get("summary", "")) for s in stories)
    n_local = sum(1 for s in stories for st in STANCES
                  if isinstance(s.get(st), dict) and s[st].get("image_local_path"))
    print(f"\nUpdated {args.dataset}")
    print(f"  summaries still truncated: {n_trunc}")
    print(f"  stance entries with a local image: {n_local}")


# ══════════════════════════════════════════════════════════════════════════════
#  fix-summaries — whitespace-insensitive retry for leftover truncations
# ══════════════════════════════════════════════════════════════════════════════

def cmd_fix_summaries(args) -> None:
    stories = load_dataset(Path(args.dataset))
    todo = [s for s in stories if is_truncated(s.get("summary", ""))]
    print(f"{len(todo)} still-truncated stories.")
    if not todo:
        print("Nothing to do.")
        return

    session = make_session()
    ok = fail = 0
    for i, story in enumerate(todo, 1):
        try:
            soup = fetch_soup(session, story["headline_link"])
        except Exception as e:
            print(f"  PAGE ERROR {story['headline_link']}: {e}")
            fail += 1
            continue
        old = story["summary"]
        key = norm_ws(old[:80].removesuffix("..."))
        best = None
        for div in soup.find_all("div", class_="editor-content"):
            text = re.sub(r"\s+", " ", div.get_text(" ", strip=True))
            if norm_ws(text).startswith(key) and len(text) > len(old):
                best = text
                break
        if best:
            story["summary"] = best
            ok += 1
        else:
            fail += 1
            print(f"  NO MATCH {story['headline_link']}")
        if i % 10 == 0:
            print(f"  {i}/{len(todo)} ({ok} fixed)", flush=True)
        time.sleep(0.8)

    save_dataset(stories, Path(args.dataset))
    left = sum(is_truncated(s.get("summary", "")) for s in stories)
    print(f"\nDone: {ok} fixed, {fail} failed. Summaries still truncated: {left}")


# ══════════════════════════════════════════════════════════════════════════════
#  refresh-images — re-fetch pages for entries whose stored image URL died
# ══════════════════════════════════════════════════════════════════════════════

def cmd_refresh_images(args) -> None:
    stories = load_dataset(Path(args.dataset))

    todo = []
    for story in stories:
        stances = [s for s in STANCES
                   if isinstance(story.get(s), dict)
                   and story[s].get("image_link")
                   and not story[s].get("image_local_path")]
        if stances:
            todo.append((story, stances))
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} stories have failed image downloads to refresh.")
    if not todo:
        print("Nothing to do.")
        return

    counters = {"pages": 0, "page_errors": 0, "ok": 0, "gone": 0, "dl_fail": 0}

    def worker(chunk):
        session = make_session()
        for story, stances in chunk:
            slug = slug_of(story)
            try:
                featured = parse_featured_from_container(
                    fetch_soup(session, story["headline_link"]))
            except Exception as e:
                with _lock:
                    counters["page_errors"] += 1
                print(f"  PAGE ERROR {slug}: {e}", file=sys.stderr)
                continue
            for stance in stances:
                entry = story[stance]
                fresh = (featured.get(stance) or {}).get("image_link", "")
                candidates = [u for u in (fresh, entry["image_link"]) if u.startswith("http")]
                got = False
                for url in candidates:
                    dest = IMAGES_DIR / slug / stance / filename_from_url(url)
                    if download_image(url, dest):
                        with _lock:
                            entry["image_link"] = url
                            entry["image_local_path"] = str(dest.relative_to(OUTPUT_DIR))
                            counters["ok"] += 1
                        got = True
                        break
                if not got:
                    with _lock:
                        counters["gone" if not fresh else "dl_fail"] += 1
            with _lock:
                counters["pages"] += 1
                if counters["pages"] % 50 == 0:
                    print(f"  {counters['pages']}/{len(todo)} pages | recovered {counters['ok']} "
                          f"| gone {counters['gone']} | dl_fail {counters['dl_fail']}", flush=True)
            time.sleep(0.8)

    threads = [threading.Thread(target=worker, args=(c,))
               for c in (todo[i::args.workers] for i in range(args.workers)) if c]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    save_dataset(stories, Path(args.dataset))
    n_local = sum(1 for s in stories for st in STANCES
                  if isinstance(s.get(st), dict) and s[st].get("image_local_path"))
    print(f"\nDone. Pages fetched: {counters['pages']} ({counters['page_errors']} errors)")
    print(f"  images recovered: {counters['ok']} | no longer on page: {counters['gone']} "
          f"| still failing: {counters['dl_fail']}")
    print(f"  total stance entries with a local image: {n_local}")


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(
        prog="allsides_crawler",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("crawl", help="scrape the balanced-news feed into a jsonl")
    p.add_argument("--start", default="2025-01-01", help="earliest story date (YYYY-MM-DD)")
    p.add_argument("--end", default="2026-12-31", help="latest story date (YYYY-MM-DD)")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    p.add_argument("--max-pages", type=int, default=100, help="listing pages to walk")
    p.add_argument("--limit", type=int, default=0, help="max stories (0 = all; for testing)")
    p.add_argument("--no-more", action="store_true",
                   help="skip the more_left/center/right article lists (much faster)")
    p.add_argument("--output", default="", help=f"output jsonl (default: "
                   f"{OUTPUT_DIR}/allsides_crawl_<start>_<end>.jsonl)")
    p.set_defaults(func=cmd_crawl)

    p = sub.add_parser("repair", help="fix summaries, backfill + download images")
    p.add_argument("--dataset", default=str(DATASET))
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--limit", type=int, default=0, help="phase-1 page fetches (0 = all)")
    p.add_argument("--skip-images", action="store_true")
    p.set_defaults(func=cmd_repair)

    p = sub.add_parser("fix-summaries", help="whitespace-insensitive summary retry")
    p.add_argument("--dataset", default=str(DATASET))
    p.set_defaults(func=cmd_fix_summaries)

    p = sub.add_parser("refresh-images", help="re-download images whose URL died")
    p.add_argument("--dataset", default=str(DATASET))
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--limit", type=int, default=0, help="max story pages (0 = all)")
    p.set_defaults(func=cmd_refresh_images)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
