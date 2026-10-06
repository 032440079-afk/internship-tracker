"""
Ana pipeline. Her scraper modülünün `scrape() -> list[dict]` fonksiyonunu
çağırır, alakalı olanları filtreler, yeni olanları Firestore'a kaydeder
ve Telegram bildirimi atar.

Her offer dict'i şu alanları içermeli:
  title, company, location, country, source, url, description (opsiyonel), postedDate (opsiyonel)

Çalıştırma:
  python run.py                 -> tüm scraper'ları çalıştırır
  python run.py --dry-run       -> Firestore'a yazmadan / bildirim atmadan sadece sonuçları yazdırır
  python run.py --source stageplaza  -> sadece belirtilen kaynağı çalıştırır
"""
import argparse
import importlib
import traceback

from lib import store, notify, export_html, ai_filter
from lib.filters import is_relevant

# Aktif scraper modülleri. Her biri scrapers/ altında, scrape() fonksiyonu içerir.
SCRAPER_MODULES = [
    # "scrapers.erasmus_careers",  # Cloudflare IP bloğu — GitHub Actions datacenter IP'si engelliyor
    "scrapers.stageplaza",
    "scrapers.company_continental",
      "scrapers.company_nim_fallback",
    "scrapers.company_successfactors",
    "scrapers.company_workday",
    "scrapers.company_smartrecruiters",
    "scrapers.company_greenhouse",
    "scrapers.arbeitnow",
    "scrapers.company_amazon",
    "scrapers.arbeitsagentur",
    # "scrapers.company_zf",
    # "scrapers.company_festo",
]


def run(dry_run: bool = False, only_source: str | None = None):
    total_found = 0
    total_new = 0

    for module_name in SCRAPER_MODULES:
        source_key = module_name.split(".")[-1]
        if only_source and only_source != source_key:
            continue

        print(f"\n=== {source_key} ===")
        try:
            mod = importlib.import_module(module_name)
            offers = mod.scrape()
        except Exception:
            print(f"[HATA] {source_key} scrape edilemedi:")
            traceback.print_exc()
            continue

        print(f"{len(offers)} ilan bulundu (filtre öncesi)")
        total_found += len(offers)

        candidates = []
        seen_urls = set()
        for offer in offers:
            relevant, matches = is_relevant(
                offer.get("title", ""), offer.get("description", ""), offer.get("location", "")
            )
            if not relevant or offer["url"] in seen_urls:
                continue
            seen_urls.add(offer["url"])
            offer["matched_keywords"] = matches
            offer["source"] = source_key
            if not dry_run and not store.is_new_offer(offer["url"]):
                continue  # zaten kayıtlı, atla
            candidates.append(offer)

        # Anahtar kelime filtresinden geçen yeni ilanları yapay zekâyla ikinci kez ele
        for offer in ai_filter.filter_offers(candidates):
            total_new += 1
            if dry_run:
                print(f"  [YENİ-DRY] {offer['title']} — {offer.get('company')} — {offer['url']}")
                continue
            store.save_offer(offer)
            notify.notify_new_offer(offer)
            print(f"  [YENİ] {offer['title']} — {offer.get('company')}")

    print(f"\nToplam bulunan: {total_found} | Alakalı + yeni: {total_new}")

    if not dry_run:
        try:
            export_html.generate()
        except Exception as e:
            print(f"[HATA] export_html basarisiz: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Firestore/Telegram olmadan test et")
    parser.add_argument("--source", type=str, default=None, help="Sadece tek kaynağı çalıştır")
    args = parser.parse_args()

    run(dry_run=args.dry_run, only_source=args.source)
