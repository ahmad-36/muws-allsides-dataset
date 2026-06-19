import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import run_scraper
from bs4 import BeautifulSoup

DOMAIN = "justthenews.com"

def parse(html, url):
    soup = BeautifulSoup(html, "html.parser")

    h1_candidates = soup.select("h1")
    headline = ""
    for h in h1_candidates:
        text = h.get_text(strip=True)
        if text and "subscribe" not in text.lower() and len(text) > 10:
            headline = text
            break

    if not headline:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("headline"):
                    headline = data["headline"]
                    break
            except Exception:
                pass

    paras = soup.select("article p")
    body = "\n\n".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
    if body:
        return headline, body

    for sel in ["div.field--body p", "div.node-content p", "main p"]:
        paras = soup.select(sel)
        body = "\n\n".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
        if body:
            return headline, body

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("articleBody"):
                return data.get("headline", headline), data["articleBody"]
        except Exception:
            pass

    return headline, ""

if __name__ == "__main__":
    run_scraper(DOMAIN, parse)
