"""
Bundesagentur fur Arbeit Jobborse'deki Praktikum/Trainee ilanlarini tarar.
Almanya'daki binlerce sirketin staj ilanini tek kaynaktan getirir.

Herkese acik API (bundesAPI/jobsuche-api):
  GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs
  Header: X-API-Key: jobboerse-jobsuche
  angebotsart=34 -> Praktikum/Trainee
"""
import requests

from lib.config import REQUEST_HEADERS

API_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"  # v4 artik 403 donuyor
SEARCH_TERMS = ["Industrial Engineering", "Wirtschaftsingenieur", "Supply Chain", "Logistik",
                "Produktion", "Operations", "Lean", "Prozessoptimierung"]
PAGE_SIZE = 100
MAX_PAGES = 5


def scrape() -> list[dict]:
    session = requests.Session()
    headers = dict(REQUEST_HEADERS)
    headers["X-API-Key"] = "jobboerse-jobsuche"
    offers = {}

    for term in SEARCH_TERMS:
        try:
            for page in range(1, MAX_PAGES + 1):
                params = {"was": term, "angebotsart": 34, "size": PAGE_SIZE, "page": page}
                resp = session.get(API_URL, params=params, headers=headers, timeout=25)
                if resp.status_code != 200:
                    break
                jobs = resp.json().get("stellenangebote", [])
                if not jobs:
                    break
                for job in jobs:
                    refnr = job.get("refnr", "")
                    title = job.get("titel") or job.get("beruf", "")
                    if not refnr or not title:
                        continue
                    ort = job.get("arbeitsort") or {}
                    offers[refnr] = {
                        "title": title,
                        "company": job.get("arbeitgeber", ""),
                        "location": ", ".join(p for p in (ort.get("ort"), ort.get("land")) if p),
                        "country": ort.get("land", ""),
                        "url": f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}",
                        "description": "",
                    }
                if len(jobs) < PAGE_SIZE:
                    break
        except Exception as e:
            print(f"[HATA] Arbeitsagentur ('{term}') scrape edilemedi: {e}")

    return list(offers.values())


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["company"], "|", r["location"], "|", r["url"])
