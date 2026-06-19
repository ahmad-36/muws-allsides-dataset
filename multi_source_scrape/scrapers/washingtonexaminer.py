import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import run_scraper
from bs4 import BeautifulSoup

DOMAIN = "washingtonexaminer.com"


def _extract_images(soup):
    images = []
    seen = set()
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            if isinstance(data, dict) and "image" in data:
                img = data["image"]
                img_url = img.get("url", "") if isinstance(img, dict) else str(img)
                if img_url and img_url not in seen:
                    seen.add(img_url)
                    images.append({"url": img_url, "alt": ""})
        except Exception:
            pass
    if not images:
        og = soup.find("meta", property="og:image")
        if og:
            src = og.get("content", "")
            if src and src not in seen:
                images.append({"url": src, "alt": ""})
    article = soup.find("article")
    if article:
        for fig in article.find_all("figure"):
            if fig.find_parent(class_=lambda c: c and "explore-more" in str(c)):
                continue
            img = fig.find("img")
            if img:
                src = img.get("src", "")
                if src and src.startswith("http") and src not in seen:
                    seen.add(src)
                    images.append({"url": src, "alt": img.get("alt", "")})
    return images


def parse(html, url):
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    headline = h1.get_text(strip=True) if h1 else ""

    images = _extract_images(soup)

    article = soup.find("article", class_="fn-body")
    if not article:
        article = soup.find("article")

    if article:
        parts = []
        for el in article.find_all(["h2", "h3", "p"]):
            if el.find_parent(class_=lambda c: c and "explore-more" in str(c)):
                continue
            if el.name in ("h2", "h3"):
                text = el.get_text(strip=True)
                if text:
                    parts.append(f"\n## {text}\n")
            elif el.name == "p":
                text = el.get_text(" ", strip=True)
                if len(text) >= 20:
                    parts.append(text)
        body = "\n\n".join(parts)
        if body:
            return headline, body, images

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            if isinstance(data, dict) and data.get("articleBody"):
                return data.get("headline", headline), data["articleBody"], images
        except Exception:
            pass

    paras = soup.select("article p, main p")
    body = "\n\n".join(p.get_text(" ", strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
    return headline, body, images


if __name__ == "__main__":
    run_scraper(DOMAIN, parse)
