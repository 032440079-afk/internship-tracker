"""
Bundesagentur fur Arbeit Jobborse'deki Praktikum/Trainee ilanlarini tarar.
Almanya'daki binlerce sirketin staj ilanini tek kaynaktan getirir.

Herkese acik API (bundesAPI/jobsuche-api):
  GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs
  Header: X-API-Key: jobboerse-jobsuche
  Yanit (v6): ergebnisliste[] -> stellenangebotsTitel, firma, referenznummer, stellenlokationen[].adresse
  angebotsart=34 -> Praktikum/Trainee
"""
import requests

from lib.config import REQUEST_HEADERS
from lib.dates import parse_date, parse_relative

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
                jobs = resp.json().get("ergebnisliste", [])
                if not jobs:
                    break
                for job in jobs:
                    refnr = job.get("referenznummer", "")
                    title = job.get("stellenangebotsTitel") or job.get("hauptberuf", "")
                    if not refnr or not title:
                        continue
                    lok = (job.get("stellenlokationen") or [{}])[0].get("adresse") or {}
                    offers[refnr] = {
                        "title": title,
                        "company": job.get("firma", ""),
                        "location": ", ".join(p for p in (lok.get("ort"), (lok.get("land") or "").title()) if p),
                        "country": lok.get("land", ""),
                        "url": f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}",
                        # angebotsart=34 ile hepsi staj; baslikta "Praktikum" gecmese de staj filtresinden gecsin
                        "description": "Praktikum/Trainee",
                        "postedDate": parse_date(job.get("aktuelleVeroeffentlichungsdatum")
                                                 or job.get("modifikationsTimestamp")),
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
