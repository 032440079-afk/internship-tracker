"""
Workday tabanli kariyer sitelerini tarar (KION Group, Roche, Unilever, ASML, Maersk, LEGO, Electrolux, Kone, TRUMPF, Novartis, Sanofi, GSK, AstraZeneca, Philips, Airbus, NXP, ZEISS, Valeo).

Workday, kimlik dogrulamasi gerektirmeyen genel bir JSON API sunar:
  POST https://<tenant>.<wd_host>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs
  Body: {"appliedFacets": {}, "limit": N, "offset": N, "searchText": ""}
"""
import requests

from lib.config import REQUEST_HEADERS
from lib.dates import parse_date, parse_relative

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
    {"name": "Airbus", "tenant": "ag", "wd_host": "wd3", "site": "Airbus"},
    {"name": "NXP", "tenant": "nxp", "wd_host": "wd3", "site": "careers"},
    {"name": "ZEISS", "tenant": "zeissgroup", "wd_host": "wd3", "site": "External"},
    {"name": "Valeo", "tenant": "valeo", "wd_host": "wd3", "site": "valeo_jobs"},
]

RESULTS_PER_PAGE = 20
MAX_PAGES = 100  # 30 sayfa (600 ilan) Airbus/NXP/ZEISS gibi buyuk sirketlerde yetmiyordu
# Toplam ilani MAX_PAGES sayfayi asan sirketlerde stajlar listenin sonunda kalabiliyor: kelimeyle ayrica aranir
INTERNSHIP_QUERIES = ["intern", "internship", "praktikum", "praktikant", "stage", "stagiaire"]
QUERY_MAX_PAGES = 10


def _scrape_company(name: str, tenant: str, wd_host: str, site: str, session: requests.Session):
    all_offers, total = _search(name, tenant, wd_host, site, session, "", MAX_PAGES)
    if total and total > MAX_PAGES * RESULTS_PER_PAGE:
        seen = {o["url"] for o in all_offers}
        before = len(all_offers)
        for q in INTERNSHIP_QUERIES:
            found, _ = _search(name, tenant, wd_host, site, session, q, QUERY_MAX_PAGES)
            for o in found:
                if o["url"] not in seen:
                    seen.add(o["url"])
                    all_offers.append(o)
        print(f"[workday] {name}: {total} ilandan {MAX_PAGES * RESULTS_PER_PAGE} tanesi okunabildi, staj aramasiyla"
              f" {len(all_offers) - before} ilan daha bulundu")
    return all_offers


def _search(name: str, tenant: str, wd_host: str, site: str, session: requests.Session, query: str, max_pages: int):
    """(ilanlar, sitenin bildirdigi toplam ilan sayisi) dondurur."""
    api_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    base_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/{site}"

    headers = dict(REQUEST_HEADERS)
    headers["Content-Type"] = "application/json"

    all_offers = []
    offset = 0
    total = None

    while offset < max_pages * RESULTS_PER_PAGE:
        body = {
            "appliedFacets": {},
            "limit": RESULTS_PER_PAGE,
            "offset": offset,
            "searchText": query,
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

            posted, approx = parse_relative(job.get("postedOn", ""))
            all_offers.append({
                "title": title,
                "company": name,
                "location": job.get("locationsText", ""),
                "country": "",
                "url": f"{base_url}{path}",
                "description": "",
                "postedDate": posted,
                "postedApprox": approx,  # "30+ Days Ago": gercek tarih daha eski olabilir
            })

        offset += RESULTS_PER_PAGE
        if total is not None and offset >= total:
            break

    return all_offers, total


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
