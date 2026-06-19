import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import run_scraper
from bs4 import BeautifulSoup

DOMAIN = "theepochtimes.com"

def parse(html, url):
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.select_one("h1")
    headline = h1.get_text(strip=True) if h1 else ""

    paras = soup.select("div.post_content p")
    body = "\n\n".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
    if body:
        return headline, body

    for sel in ["article p", "div[class*='article'] p", "main p"]:
        paras = soup.select(sel)
        body = "\n\n".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
        if body:
            return headline, body

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("articleBody"):
                return data.get("headline", headline), data["articleBody"]
            if isinstance(data, list):
                for d in data:
                    if isinstance(d, dict) and d.get("articleBody"):
                        return d.get("headline", headline), d["articleBody"]
        except Exception:
            pass

    return headline, ""

if __name__ == "__main__":
    run_scraper(DOMAIN, parse)
