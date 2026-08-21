"""
Kaynak: https://jobs.continental.com/en/a-z-liste/

Continental'in kariyer portali Cloudflare korumasi kullanmiyor, duz
requests ile calisiyor. Sayfa TYPO3 tabanli, sayfalama linkleri
cHash icerdigi icin tahmin edilemiyor -- bu yuzden her sayfadan
"sonraki sayfa" linkini cikarip onu takip ediyoruz (link crawling).

HTML yapisi:
  Ilan linki: <a href="/en/detail-page/job-detail/REFxxxxx-p-.../slug/">Baslik</a>
  Sayfalama: sayi linkleri (1, 2, 3, ...) sayfa altinda
"""
import re
import requests
from bs4 import BeautifulSoup

from lib.config import REQUEST_HEADERS

START_URL = "https://jobs.continental.com/en/a-z-liste/"
MAX_PAGES = 10  # guvenlik limiti

JOB_URL_PATTERN = re.compile(r"/en/detail-page/job-detail/")


def _parse_page(html: str, base_url: str = "https://jobs.continental.com"):
    soup = BeautifulSoup(html, "lxml")
    offers = []
    seen = set()

    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if not JOB_URL_PATTERN.search(href):
            continue
        url = href if href.startswith("http") else f"{base_url}{href}"
        if url in seen:
            continue
        seen.add(url)

        title = a.get_text(strip=True)
        if not title:
            continue

        offers.append({
            "title": title,
            "company": "Continental",
            "location": "",
            "country": "",

            "url": url,
            "description": "",
        })

    return offers


def _find_next_page_url(html: str, current_page: int, base_url: str = "https://jobs.continental.com"):
    soup = BeautifulSoup(html, "lxml")
    target = str(current_page + 1)
    for a in soup.select("a[href]"):
        if a.get_text(strip=True) == target:
            href = a.get("href", "")
            return href if href.startswith("http") else f"{base_url}{href}"
    return None


def scrape() -> list[dict]:
    all_offers = []
    url = START_URL
    page_num = 1

    session = requests.Session()

    while url and page_num <= MAX_PAGES:
        resp = session.get(url, headers=REQUEST_HEADERS, timeout=25)
        resp.raise_for_status()
        html = resp.text

        page_offers = _parse_page(html)
        if not page_offers:
            break
        all_offers.extend(page_offers)

        next_url = _find_next_page_url(html, page_num)
        if not next_url or next_url == url:
            break
        url = next_url
        page_num += 1

    return all_offers


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["url"])
