"""Yeni eklenen sirketleri tek tek dener; Firestore/Telegram'a dokunmaz. Gecici kontrol scripti."""
import sys
sys.path.insert(0, ".")
from scrapers import company_nim_fallback as nim, company_successfactors as sf, company_workday as wd

NEW_NIM = {"Mercedes-Benz", "Audi", "Bosch", "Daimler Truck", "Volvo Group", "Stellantis", "Siemens",
           "Siemens Energy", "ABB", "Schneider Electric", "Bayer", "Henkel", "Nestle", "P&G",
           "DHL Group", "DSV (DB Schenker)", "Kuehne+Nagel"}
NEW_SF = {"Schaeffler", "BASF"}
NEW_WD = {"Airbus"}

def report(name, offers):
    print(f"RESULT | {name} | {len(offers)} ilan")
    for o in offers[:3]:
        print(f"    - {o.get('title')} | {o.get('location')} | {o.get('url')}")

for t in nim.TARGETS:
    if t["name"] not in NEW_NIM:
        continue
    orig = nim.TARGETS
    nim.TARGETS = [t]
    report(t["name"], nim.scrape())
    nim.TARGETS = orig

for mod, names in ((sf, NEW_SF), (wd, NEW_WD)):
    orig = mod.COMPANIES
    for c in orig:
        if c["name"] in names:
            mod.COMPANIES = [c]
            report(c["name"], mod.scrape())
    mod.COMPANIES = orig
