import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import run_scraper
from bs4 import BeautifulSoup

DOMAIN = "forbes.com"

def parse(html, url):
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.select_one("h1")
    headline = h1.get_text(strip=True) if h1 else ""

    paras = soup.select("div.article-body p")
    body = "\n\n".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
    if body:
        return headline, body

    paras = soup.select("article p")
    body = "\n\n".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
    if body:
        return headline, body

    return headline, body

if __name__ == "__main__":
    run_scraper(DOMAIN, parse)
