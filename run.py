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
from datetime import datetime
import importlib
import traceback

from lib import store, notify, export_html, ai_filter, application, config, eligibility, tracking
from lib.filters import is_relevant, fix_mojibake
from lib.job_details import JobPageReader

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


def _read_job_text(reader: JobPageReader, url: str) -> str:
    try:
        return reader.read(url)
    except Exception as e:
        print(f"    [SAYFA-HATA] {type(e).__name__}")
        return ""


def _send_application(offer: dict, job_text: str):
    """Ilana gore CV + on yazi uretip Telegram'a gonderir. Icerik loglanmaz (Actions loglari herkese acik)."""
    try:
        files = application.build_application(offer, job_text)
        paths = [files["cv"]] + ([files["cover_letter"]] if files["cover_letter"] else [])
        notify.send_application_files(offer, paths, files["match"])
        if files["match"]:
            store.save_match(store.url_hash(offer["url"]), files["match"])
        score = f"%{files['match']['score']}" if files["match"] else "-"
        print(f"    [CV] {files['changes']} bölüm uyarlandı, uygunluk: {score}, ön yazı: {'var' if files['cover_letter'] else 'yok'}"
              f" (çıkarılan cümle: {files['letter_sentences_removed']}, ilan metni: {len(job_text)} karakter)")
    except Exception as e:
        print(f"    [CV-HATA] {type(e).__name__}")


def run(dry_run: bool = False, only_source: str | None = None):
    total_found = 0
    total_new = 0
    ineligible = []
    notified_titles = set()
    applications_made = 0
    reader = None
    make_applications = not dry_run and application.available()
    if not dry_run:
        # Saatlik takip isi gecikirse diye: bekleyen "Basvurdum / Gorusme ..." buton basmalarini burada da isle
        try:
            tracking.sync_allowed()
            notify._run(tracking.process_updates())
        except Exception as e:
            print(f"[tracking] islenemedi: {type(e).__name__}")
    if not dry_run and not make_applications:
        print("[CV] Ana CV veya NVIDIA_API_KEY yok; CV/ön yazı üretimi kapalı.")

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

        dated = sum(1 for o in offers if o.get("postedDate"))
        print(f"{len(offers)} ilan bulundu (filtre öncesi), {dated} tanesinde yayın tarihi var")
        total_found += len(offers)

        candidates = []
        seen_urls = set()
        for offer in offers:
            for field in ("title", "company", "location"):
                offer[field] = fix_mojibake(offer.get(field, ""))
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
            if dry_run:
                total_new += 1
                print(f"  [YENİ-DRY] {offer['title']} — {offer.get('company')} — {offer['url']}")
                continue
            # Ayni sirketin ayni baslikli ilani (ornegin farkli sehirler) bir kez bildirilir; digerleri sadece kaydedilir
            title_key = (offer["title"].strip().lower(), (offer.get("company") or "").strip().lower())
            if title_key in notified_titles:
                store.save_offer(offer)
                print(f"  [TEKRAR] {offer['title']} — {offer.get('company')} — {offer.get('location')}")
                continue
            notified_titles.add(title_key)
            # Ilan metni: sinif / donem sarti kontrolu ve CV uyarlamasi icin
            job_text = ""
            if config.NVIDIA_API_KEY:
                if reader is None:
                    reader = JobPageReader().__enter__()
                job_text = _read_job_text(reader, offer["url"])
            offer["eligible"], reason, evidence = eligibility.check(offer, job_text)
            store.save_offer(offer)  # uygun olmasa da kaydedilir ki her gun yeniden kontrol edilmesin
            if not offer["eligible"]:
                ineligible.append((offer, reason, evidence))
                print(f"  [SINIF-ŞARTI] {offer['title']} — {offer.get('company')} — {reason}")
                continue
            total_new += 1
            notify.notify_new_offer(offer)
            print(f"  [YENİ] {offer['title']} — {offer.get('company')}")
            if make_applications and applications_made < config.MAX_APPLICATIONS_PER_RUN:
                _send_application(offer, job_text)
                applications_made += 1

        # Tarayiciyi kaynak bitince kapat: sonraki scraper'lar kendi Playwright'larini acabilsin
        if reader is not None:
            reader.__exit__(None, None, None)
            reader = None

    print(f"\nToplam bulunan: {total_found} | Alakalı + yeni: {total_new} | Sınıf şartıyla elenen: {len(ineligible)}"
          f" | CV üretilen: {applications_made}")

    if ineligible:
        notify.send_ineligible_summary(ineligible)

    if not dry_run and datetime.now().weekday() == 0:  # pazartesi: herkese kendi haftalik basvuru ozeti
        try:
            notify._run(tracking.send_weekly_summaries())
        except Exception as e:
            print(f"[tracking] ozet gonderilemedi: {type(e).__name__}")

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
