"""
Amazon stajlarini tarar (Avrupa Operations/Logistics stajlari dahil).

amazon.jobs kimlik dogrulamasi gerektirmeyen bir arama JSON'u sunar:
  GET https://www.amazon.jobs/en/search.json?base_query=intern&result_limit=100&offset=N
"""
import requests

from lib.config import REQUEST_HEADERS

SEARCH_URL = "https://www.amazon.jobs/en/search.json"
QUERIES = ["intern", "internship"]
RESULTS_PER_PAGE = 100
MAX_PAGES = 20


def scrape() -> list[dict]:
    session = requests.Session()
    offers = {}

    for query in QUERIES:
        try:
            for page in range(MAX_PAGES):
                params = {"base_query": query, "result_limit": RESULTS_PER_PAGE, "offset": page * RESULTS_PER_PAGE}
                resp = session.get(SEARCH_URL, params=params, headers=REQUEST_HEADERS, timeout=25)
                if resp.status_code != 200:
                    break
                jobs = resp.json().get("jobs", [])
                if not jobs:
                    break
                for job in jobs:
                    title = job.get("title", "")
                    path = job.get("job_path", "")
                    if not title or not path:
                        continue
                    url = f"https://www.amazon.jobs{path}"
                    offers[url] = {
                        "title": title,
                        "company": "Amazon",
                        "location": job.get("normalized_location") or job.get("location", ""),
                        "country": job.get("country_code", ""),
                        "url": url,
                        "description": job.get("description_short", ""),
                    }
        except Exception as e:
            print(f"[HATA] Amazon ('{query}') scrape edilemedi: {e}")

    return list(offers.values())


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["location"], "|", r["url"])
