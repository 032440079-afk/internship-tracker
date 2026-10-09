"""
Arbeitnow is ilanı panosundaki (agirlikli Almanya/Avrupa) staj ilanlarini tarar.

Herkese acik API:
  GET https://www.arbeitnow.com/api/job-board-api?page=N
"""
import requests

from lib.config import REQUEST_HEADERS, INTERNSHIP_KEYWORDS
from lib.dates import parse_date

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 15


def _is_internship(job: dict) -> bool:
    if any("intern" in (t or "").lower() for t in job.get("job_types", [])):
        return True
    title = (job.get("title") or "").lower()
    return any(kw in title for kw in INTERNSHIP_KEYWORDS)


def scrape() -> list[dict]:
    session = requests.Session()
    offers = {}

    try:
        for page in range(1, MAX_PAGES + 1):
            resp = session.get(API_URL, params={"page": page}, headers=REQUEST_HEADERS, timeout=25)
            if resp.status_code != 200:
                break
            jobs = resp.json().get("data", [])
            if not jobs:
                break
            for job in jobs:
                if not _is_internship(job) or not job.get("url") or not job.get("title"):
                    continue
                offers[job["url"]] = {
                    "title": job["title"],
                    "company": job.get("company_name", ""),
                    "location": job.get("location", ""),
                    "country": "",
                    "url": job["url"],
                    # Aciklama bos birakiliyor: uzun metinde "international" gibi kelimeler "intern" filtresini yaniltiyor.
                    "description": "",
                    "postedDate": parse_date(job.get("created_at")),
                }
    except Exception as e:
        print(f"[HATA] Arbeitnow scrape edilemedi: {e}")

    return list(offers.values())


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["company"], "|", r["location"], "|", r["url"])
