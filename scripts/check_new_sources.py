"""Yeni eklenen sirketleri tek tek dener; Firestore/Telegram'a dokunmaz. Gecici kontrol scripti."""
import sys
sys.path.insert(0, ".")
from scrapers import company_nim_fallback as nim, company_successfactors as sf, company_workday as wd

# 2. tur: sadece ikinci partide eklenenler (ilk parti run 37465628265'te test edildi)
NEW_NIM = {"Michelin", "Alstom", "Atlas Copco", "Signify", "Nokia"}
NEW_SF = {"SKF", "Volvo Cars"}
NEW_WD = {"NXP", "ZEISS"}

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
