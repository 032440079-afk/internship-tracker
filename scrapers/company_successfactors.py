"""
SAP SuccessFactors tabanli kariyer sitelerini tarar (Festo, ZF).
Erisilebilir format sayfasi /search/ duz HTML donduruyor.
"""
import re
import requests
from bs4 import BeautifulSoup

from lib.config import REQUEST_HEADERS

COMPANIES = [
    {"name": "Festo", "search_url": "https://jobs.festo.com/search/"},
    {"name": "ZF", "search_url": "https://jobs.zf.com/search/"},
]

RESULTS_PER_PAGE = 25
MAX_PAGES = 25

JOB_URL_PATTERN = re.compile(r"/job/")

def _parse_page(html: str, company_name: str):
    soup = BeautifulSoup(html, "lxml")
    offers = []
    seen = set()

    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if not JOB_URL_PATTERN.search(href):
            continue
        url = href
        if url in seen:
            continue
        seen.add(url)

        title = a.get_text(strip=True)
        if not title:
            continue

        offers.append({
            "title": title,
            "company": company_name,
            "location": "",
            "country": "",
            "url": url,
            "description": "",
        })

    return offers


def _scrape_company(name: str, search_url: str, session: requests.Session):
    all_offers = []
    seen_urls = set()

    for page in range(MAX_PAGES):
        startrow = page * RESULTS_PER_PAGE
        url = search_url if startrow == 0 else f"{search_url}?startrow={startrow}"

        resp = session.get(url, headers=REQUEST_HEADERS, timeout=25)
        if resp.status_code != 200:
            break

        page_offers = _parse_page(resp.text, name)
        new_offers = [o for o in page_offers if o["url"] not in seen_urls]

        if not new_offers:
            break

        for o in new_offers:
            seen_urls.add(o["url"])
        all_offers.extend(new_offers)

    return all_offers


def scrape() -> list[dict]:
    all_offers = []
    session = requests.Session()

    for company in COMPANIES:
        try:
            offers = _scrape_company(company["name"], company["search_url"], session)
            all_offers.extend(offers)
        except Exception as e:
            print(f"[HATA] {company['name']} scrape edilemedi: {e}")

    return all_offers


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["company"], "|", r["url"])
