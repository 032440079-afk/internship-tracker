"""
Greenhouse tabanli kariyer sitelerini tarar (AB InBev).

Greenhouse kimlik dogrulamasi gerektirmeyen genel bir Job Board API sunar:
  GET https://boards-api.greenhouse.io/v1/boards/<board>/jobs
"""
import requests

from lib.config import REQUEST_HEADERS
from lib.dates import parse_date, parse_relative

COMPANIES = [
    {"name": "AB InBev", "board": "abinbev"},
]


def _scrape_company(name: str, board: str, session: requests.Session):
    resp = session.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", headers=REQUEST_HEADERS, timeout=25)
    resp.raise_for_status()

    offers = []
    for job in resp.json().get("jobs", []):
        title = job.get("title", "")
        url = job.get("absolute_url", "")
        if not title or not url:
            continue
        offers.append({
            "title": title,
            "company": name,
            "location": (job.get("location") or {}).get("name", ""),
            "country": "",
            "url": url,
            "description": "",
            "postedDate": parse_date(job.get("first_published") or job.get("updated_at")),
        })
    return offers


def scrape() -> list[dict]:
    all_offers = []
    session = requests.Session()

    for company in COMPANIES:
        try:
            all_offers.extend(_scrape_company(company["name"], company["board"], session))
        except Exception as e:
            print(f"[HATA] {company['name']} scrape edilemedi: {e}")

    return all_offers


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["company"], "|", r["location"], "|", r["url"])
