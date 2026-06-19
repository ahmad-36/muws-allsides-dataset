import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import run_scraper
from bs4 import BeautifulSoup

DOMAIN = "theguardian.com"


def _extract_images(soup):
    images = []
    seen = set()
    article = soup.find("article")
    scope = article if article else soup

    for fig in scope.find_all("figure"):
        img = fig.find("img")
        if not img:
            pic = fig.find("picture")
            if pic:
                img = pic.find("img")
        if img:
            src = img.get("src", "")
            if src and src.startswith("http") and src not in seen:
                seen.add(src)
                alt = img.get("alt", "")
                cap = fig.find("figcaption")
                caption = cap.get_text(" ", strip=True) if cap else ""
                images.append({"url": src, "alt": alt, "caption": caption})

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            if isinstance(data, dict) and "image" in data:
                img_data = data["image"]
                items = img_data if isinstance(img_data, list) else [img_data]
                for item in items:
                    img_url = item.get("url", "") if isinstance(item, dict) else str(item)
                    if img_url and img_url not in seen:
                        seen.add(img_url)
                        images.append({"url": img_url, "alt": ""})
        except Exception:
            pass

    if not images:
        og = soup.find("meta", property="og:image")
        if og:
            src = og.get("content", "")
            if src:
                images.append({"url": src, "alt": ""})

    return images


def parse(html, url):
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.select_one("h1")
    headline = h1.get_text(strip=True) if h1 else ""

    images = _extract_images(soup)

    body_div = soup.select_one("div.article-body-commercial-selector")
    if body_div:
        parts = []
        for child in body_div.children:
            if not hasattr(child, "name") or not child.name:
                continue
            if child.name in ("h2", "h3"):
                text = child.get_text(strip=True)
                if text:
                    parts.append(f"\n## {text}\n")
            elif child.name == "p":
                text = child.get_text(" ", strip=True)
                if len(text) >= 20:
                    parts.append(text)
        body = "\n\n".join(parts)
        if body:
            return headline, body, images

    paras = soup.select("article p")
    if paras:
        body = "\n\n".join(p.get_text(" ", strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
        if body:
            return headline, body, images

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("articleBody"):
                return data.get("headline", headline), data["articleBody"], images
        except Exception:
            pass

    return headline, "", images

if __name__ == "__main__":
    run_scraper(DOMAIN, parse)
