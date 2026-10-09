"""
SmartRecruiters tabanli kariyer sitelerini tarar (Bosch).

SmartRecruiters kimlik dogrulamasi gerektirmeyen genel bir Posting API sunar:
  GET https://api.smartrecruiters.com/v1/companies/<company>/postings?limit=100&offset=N
"""
import requests

from lib.config import REQUEST_HEADERS
from lib.dates import parse_date, parse_relative

COMPANIES = [
    {"name": "Bosch", "company_id": "BoschGroup"},
]

RESULTS_PER_PAGE = 100
MAX_PAGES = 60


def _scrape_company(name: str, company_id: str, session: requests.Session):
    api_url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
    all_offers = []

    for page in range(MAX_PAGES):
        params = {"limit": RESULTS_PER_PAGE, "offset": page * RESULTS_PER_PAGE}
        resp = session.get(api_url, params=params, headers=REQUEST_HEADERS, timeout=25)
        if resp.status_code != 200:
            break

        data = resp.json()
        postings = data.get("content", [])
        if not postings:
            break

        for job in postings:
            title = job.get("name", "")
            job_id = job.get("id", "")
            if not title or not job_id:
                continue
            loc = job.get("location") or {}
            location = ", ".join(p for p in (loc.get("city"), loc.get("country", "").upper()) if p)
            all_offers.append({
                "title": title,
                "company": name,
                "location": location,
                "country": loc.get("country", ""),
                "url": f"https://jobs.smartrecruiters.com/{company_id}/{job_id}",
                "description": "",
                "postedDate": parse_date(job.get("releasedDate")),
            })

        if (page + 1) * RESULTS_PER_PAGE >= data.get("totalFound", 0):
            break

    return all_offers


def scrape() -> list[dict]:
    all_offers = []
    session = requests.Session()

    for company in COMPANIES:
        try:
            all_offers.extend(_scrape_company(company["name"], company["company_id"], session))
        except Exception as e:
            print(f"[HATA] {company['name']} scrape edilemedi: {e}")

    return all_offers


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["company"], "|", r["location"], "|", r["url"])
