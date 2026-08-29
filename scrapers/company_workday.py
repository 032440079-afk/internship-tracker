"""
Workday tabanli kariyer sitelerini tarar (KION Group, Roche, Unilever, ASML, Maersk, LEGO, Electrolux, Kone, TRUMPF, Novartis, Sanofi, GSK, AstraZeneca, Philips).

Workday, kimlik dogrulamasi gerektirmeyen genel bir JSON API sunar:
  POST https://<tenant>.<wd_host>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs
  Body: {"appliedFacets": {}, "limit": N, "offset": N, "searchText": ""}
"""
import requests

from lib.config import REQUEST_HEADERS

COMPANIES = [
    {"name": "KION Group", "tenant": "kiongroup", "wd_host": "wd3", "site": "KIONGroup"},
    {"name": "Roche", "tenant": "roche", "wd_host": "wd3", "site": "roche-ext"},
    {"name": "Unilever", "tenant": "unilever", "wd_host": "wd3", "site": "Unilever_Experienced_Professionals"},
    {"name": "Unilever Early Careers", "tenant": "unilever", "wd_host": "wd3", "site": "Unilever_Early_Careers"},
    {"name": "ASML", "tenant": "asml", "wd_host": "wd3", "site": "ASMLEXT1"},
    {"name": "Maersk", "tenant": "maersk", "wd_host": "wd3", "site": "Maersk_Careers"},
    {"name": "LEGO", "tenant": "lego", "wd_host": "wd103", "site": "LEGO_External"},
    {"name": "Electrolux", "tenant": "electrolux", "wd_host": "wd3", "site": "ElectroluxCareerSite"},
    {"name": "Kone", "tenant": "kone", "wd_host": "wd3", "site": "Careers"},
    {"name": "TRUMPF", "tenant": "trumpf", "wd_host": "wd3", "site": "TRUMPF_Graduates_and_Professionals"},
    {"name": "Novartis", "tenant": "novartis", "wd_host": "wd3", "site": "Novartis_Careers"},
    {"name": "Sanofi", "tenant": "sanofi", "wd_host": "wd3", "site": "SanofiCareers"},
    {"name": "GSK", "tenant": "gsk", "wd_host": "wd5", "site": "GSKCareers"},
    {"name": "AstraZeneca", "tenant": "astrazeneca", "wd_host": "wd3", "site": "Careers"},
    {"name": "Philips", "tenant": "philips", "wd_host": "wd3", "site": "jobs-and-careers"},
]

RESULTS_PER_PAGE = 20
MAX_PAGES = 30


def _scrape_company(name: str, tenant: str, wd_host: str, site: str, session: requests.Session):
    api_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    base_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/{site}"

    headers = dict(REQUEST_HEADERS)
    headers["Content-Type"] = "application/json"

    all_offers = []
    offset = 0
    total = None

    while offset < MAX_PAGES * RESULTS_PER_PAGE:
        body = {
            "appliedFacets": {},
            "limit": RESULTS_PER_PAGE,
            "offset": offset,
            "searchText": "",
        }

        resp = session.post(api_url, json=body, headers=headers, timeout=25)
        if resp.status_code != 200:
            break

        data = resp.json()
        if total is None:
            total = data.get("total", 0)

        postings = data.get("jobPostings", [])
        if not postings:
            break

        for job in postings:
            title = job.get("title", "")
            path = job.get("externalPath", "")
            if not title or not path:
                continue

            all_offers.append({
                "title": title,
                "company": name,
                "location": job.get("locationsText", ""),
                "country": "",
                "url": f"{base_url}{path}",
                "description": "",
            })

        offset += RESULTS_PER_PAGE
        if total is not None and offset >= total:
            break

    return all_offers


def scrape() -> list[dict]:
    all_offers = []
    session = requests.Session()

    for company in COMPANIES:
        try:
            offers = _scrape_company(
                company["name"], company["tenant"], company["wd_host"], company["site"], session
            )
            all_offers.extend(offers)
        except Exception as e:
            print(f"[HATA] {company['name']} scrape edilemedi: {e}")

    return all_offers

if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["company"], "|", r["location"], "|", r["url"])
