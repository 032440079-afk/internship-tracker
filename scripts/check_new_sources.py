"""4. tur: yeni aday sirketleri ve adres alternatiflerini dener; Firestore/Telegram'a dokunmaz. Gecici kontrol scripti."""
import re
import sys
import requests
sys.path.insert(0, ".")
from lib.config import REQUEST_HEADERS
from scrapers import (company_nim_fallback as nim, company_successfactors as sf, company_workday as wd,
                      company_smartrecruiters as sr, company_greenhouse as gh)


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
for name, host in [("DACHSER", "https://careers.dachser.com"), ("Hapag-Lloyd", "https://jobs.hapag-lloyd.com"),
                   ("MAHLE", "https://careers.mahle.com")]:
    swap(sf, "COMPANIES", [{"name": name, "search_url": f"{host}/search/", "base_url": host}], f"{name} [sf]")

# Workday: kok adres hangi site'a yonleniyor + aday site isimleri
for tenant, sites in [("renault", ["Renault_Group", "RenaultGroup", "Careers", "External", "Renault"]),
                      ("valeo", ["valeo_jobs", "Valeo", "Careers", "External", "Valeo_Careers"])]:
    probe_get(f"{tenant} workday root", f"https://{tenant}.wd3.myworkdayjobs.com/")
    for site in sites:
        swap(wd, "COMPANIES", [{"name": tenant, "tenant": tenant, "wd_host": "wd3", "site": site}], f"{tenant} [wd] {site}")

# SmartRecruiters (IKEA) ve Greenhouse (AB InBev)
for cid in ("IKEA", "Ingka", "IngkaGroup", "IKEAGroup"):
    swap(sr, "COMPANIES", [{"name": "IKEA", "company_id": cid}], f"IKEA [sr] {cid}")
report("AB InBev [greenhouse]", gh.scrape())

# Yapay zeka yolu
for name, url in [
    ("Thales", "https://careers.thalesgroup.com/global/en/search-results?keywords=intern"),
    ("L'Oreal", "https://careers.loreal.com/en_US/jobs/SearchJobs/intern"),
    ("Danone", "https://careers.danone.com/en-global/jobs.html"),
    ("Safran", "https://www.safran-group.com/jobs"),
    ("Rolls-Royce", "https://careers.rolls-royce.com/search-jobs/intern"),
    ("Saint-Gobain", "https://joinus.saint-gobain.com/en/search?keywords=intern"),
    ("Liebherr", "https://www.liebherr.com/en-int/career/job-vacancies"),
    ("Ferrero", "https://www.ferrerocareers.com/int/en/jobs"),
    ("Orsted", "https://orsted.com/en/careers/vacancies-list"),
    ("Valeo", "https://www.valeo.com/en/offers/list/"),
]:
    swap(nim, "TARGETS", [{"name": name, "url": url}], f"{name} [nim] {url}")
