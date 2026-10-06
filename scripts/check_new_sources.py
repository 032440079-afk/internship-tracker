"""Yeni/duzeltilmis kaynaklari ve alternatif adresleri dener; Firestore/Telegram'a dokunmaz. Gecici kontrol scripti."""
import re
import sys
import requests
sys.path.insert(0, ".")
from lib.config import REQUEST_HEADERS
from scrapers import company_nim_fallback as nim, company_successfactors as sf, company_workday as wd, company_smartrecruiters as sr


def report(name, offers):
    print(f"RESULT | {name} | {len(offers)} ilan", flush=True)
    for o in offers[:3]:
        print(f"    - {o.get('title')} | {o.get('location')} | {o.get('url')}", flush=True)


def run_nim(name, url):
    orig = nim.TARGETS
    nim.TARGETS = [{"name": name, "url": url}]
    try:
        report(f"{name} [nim] {url}", nim.scrape())
    finally:
        nim.TARGETS = orig


def run_sf(name, search_url, base_url):
    try:
        r = requests.get(search_url, headers=REQUEST_HEADERS, timeout=25)
        links = len(re.findall(r'href="[^"]*/job/', r.text))
        print(f"PROBE | {name} [sf] {search_url} | status={r.status_code} final={r.url} /job/-links={links}", flush=True)
    except Exception as e:
        print(f"PROBE | {name} [sf] {search_url} | HATA {e}", flush=True)
    orig = sf.COMPANIES
    sf.COMPANIES = [{"name": name, "search_url": search_url, "base_url": base_url}]
    try:
        report(f"{name} [sf] {search_url}", sf.scrape())
    finally:
        sf.COMPANIES = orig


def run_wd(name, tenant, host, site):
    orig = wd.COMPANIES
    wd.COMPANIES = [{"name": name, "tenant": tenant, "wd_host": host, "site": site}]
    try:
        report(f"{name} [wd] {tenant}/{site}", wd.scrape())
    finally:
        wd.COMPANIES = orig


# 1) Kesin duzeltmeler
report("Bosch [smartrecruiters]", sr.scrape())
run_sf("Volvo Group", "https://jobs.volvogroup.com/search/", "https://jobs.volvogroup.com")
run_wd("Airbus (600 siniri kalkti mi)", "ag", "wd3", "Airbus")

# 2) 0 gelenler icin alternatifler
for site in ("External_Career_Site", "Stellantis", "Careers", "External", "stellantis_careers"):
    run_wd("Stellantis", "stellantis", "wd3", site)
for site in ("Nokia", "External", "Careers"):
    run_wd("Nokia", "nokia", "wd3", site)
run_sf("Nestle", "https://jobdetails.nestle.com/search/", "https://jobdetails.nestle.com")
run_sf("BASF", "https://basf.jobs/search/", "https://basf.jobs")

for name, url in [
    ("Nokia", "https://careers.nokia.com/jobs"),
    ("Nestle", "https://www.nestle.com/jobs/search-jobs"),
    ("BASF", "https://basf.jobs/search/?q=intern"),
    ("Michelin", "https://jobs.michelinman.com/job-offer-result-list"),
    ("Michelin", "https://recrutement.michelin.fr/job-offer-result-list"),
    ("Schneider Electric", "https://careers.se.com/jobs"),
    ("Schneider Electric", "https://www.se.com/ww/en/about-us/careers/job-search/"),
    ("Audi", "https://www.audi.com/de/karriere/jobs.html"),
    ("Audi", "https://www.audi.com/en/careers/jobs.html"),
]:
    run_nim(name, url)
