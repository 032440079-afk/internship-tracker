"""5. tur: yeni aday sirketleri dener; Firestore/Telegram'a dokunmaz. Gecici kontrol scripti."""
import sys
import requests
sys.path.insert(0, ".")
from lib.config import REQUEST_HEADERS
from scrapers import company_nim_fallback as nim, company_successfactors as sf, company_workday as wd, company_amazon as amz


def report(name, offers):
    print(f"RESULT | {name} | {len(offers)} ilan", flush=True)
    for o in offers[:3]:
        print(f"    - {o.get('title')} | {o.get('location')} | {o.get('url')}", flush=True)


def swap(mod, attr, items, label):
    orig = getattr(mod, attr)
    setattr(mod, attr, items)
    try:
        report(label, mod.scrape())
    finally:
        setattr(mod, attr, orig)


def probe_get(label, url):
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        print(f"PROBE | {label} | status={r.status_code} final={r.url}", flush=True)
    except Exception as e:
        print(f"PROBE | {label} | HATA {e}", flush=True)


# SuccessFactors
for name, search, base in [
    ("Epiroc", "https://www.careerprofile.epiroc.com/search/", "https://www.careerprofile.epiroc.com"),
    ("Endress+Hauser", "https://careers.endress.com/search/", "https://careers.endress.com"),
    ("Schindler", "https://job.schindler.com/Schindler/search/", "https://job.schindler.com"),
    ("Pirelli", "https://jobs.pirelli.com/search/", "https://jobs.pirelli.com"),
    ("Grundfos", "https://jobs.grundfos.com/search/", "https://jobs.grundfos.com"),
]:
    swap(sf, "COMPANIES", [{"name": name, "search_url": search, "base_url": base}], f"{name} [sf]")

# Workday
for tenant, sites in [("sandvik", ["sandvik-careers", "Sandvik", "External", "Careers"]),
                      ("gea", ["GEA_Careers", "GEA", "External", "Careers"]),
                      ("hilti", ["Hilti", "External", "Careers", "Hilti_Careers"])]:
    probe_get(f"{tenant} workday root", f"https://{tenant}.wd3.myworkdayjobs.com/")
    for site in sites:
        swap(wd, "COMPANIES", [{"name": tenant, "tenant": tenant, "wd_host": "wd3", "site": site}], f"{tenant} [wd] {site}")

# Amazon
report("Amazon [search.json]", amz.scrape())

# Yapay zeka yolu
for name, url in [
    ("Rheinmetall", "https://www.rheinmetall.com/de/karriere/aktuelle-stellenangebote"),
    ("BSH", "https://jobs.bsh-group.de/en/"),
    ("Alfa Laval", "https://career.alfalaval.com/en/jobs"),
    ("Hilti", "https://careers.hilti.group/en/jobs/"),
    ("MAN Truck & Bus", "https://www.man.eu/career"),
]:
    swap(nim, "TARGETS", [{"name": name, "url": url}], f"{name} [nim] {url}")
