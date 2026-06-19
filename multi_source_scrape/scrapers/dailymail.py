import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import run_scraper
from bs4 import BeautifulSoup

DOMAIN = "dailymail.co.uk"

def parse(html, url):
    soup = BeautifulSoup(html, "html.parser")

    h2 = soup.select_one("h2#js-article-text")
    h1 = soup.select_one("h1")
    headline = ""
    if h2:
        headline = h2.get_text(strip=True)
    elif h1:
        headline = h1.get_text(strip=True)

    paras = soup.select("div[itemprop='articleBody'] p")
    body = "\n\n".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
    if body:
        return headline, body

    paras = soup.select("div.article-text p")
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

    return headline, body

if __name__ == "__main__":
    run_scraper(DOMAIN, parse)
