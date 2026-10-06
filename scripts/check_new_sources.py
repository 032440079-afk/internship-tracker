"""7. tur: Arbeitsagentur API teshisi; Firestore/Telegram'a dokunmaz. Gecici kontrol scripti."""
import requests

H = {"User-Agent": "Mozilla/5.0", "X-API-Key": "jobboerse-jobsuche"}
BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
for path, params in [
    ("/pc/v4/jobs", {"was": "Logistik", "angebotsart": 34, "size": 10}),
    ("/pc/v4/jobs", {"was": "Logistik", "size": 10}),
    ("/pc/v4/app/jobs", {"was": "Logistik", "angebotsart": 34, "size": 10}),
    ("/pc/v6/jobs", {"was": "Logistik", "angebotsart": 34, "size": 10}),
]:
    try:
        r = requests.get(BASE + path, params=params, headers=H, timeout=25)
        print(f"PROBE | {path} {params} | status={r.status_code} | {r.text[:300]!r}", flush=True)
    except Exception as e:
        print(f"PROBE | {path} | HATA {e}", flush=True)
