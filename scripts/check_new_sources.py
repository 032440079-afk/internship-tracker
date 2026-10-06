"""6. tur: toplayici kaynaklar (Arbeitsagentur, Arbeitnow); Firestore/Telegram'a dokunmaz. Gecici kontrol scripti."""
import sys
sys.path.insert(0, ".")
from lib.filters import is_relevant
from scrapers import arbeitsagentur, arbeitnow

for name, mod in [("Arbeitsagentur", arbeitsagentur), ("Arbeitnow", arbeitnow)]:
    offers = mod.scrape()
    relevant = [o for o in offers if is_relevant(o["title"], o.get("description", ""), o.get("location", ""))[0]]
    print(f"RESULT | {name} | {len(offers)} ilan | filtreden gecen {len(relevant)}", flush=True)
    for o in relevant[:8]:
        print(f"    - {o['title']} | {o['company']} | {o['location']} | {o['url']}", flush=True)
