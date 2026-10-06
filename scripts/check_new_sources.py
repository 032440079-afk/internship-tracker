"""8. tur: Arbeitsagentur v6 yanit yapisi. Gecici kontrol scripti."""
import json
import requests

H = {"User-Agent": "Mozilla/5.0", "X-API-Key": "jobboerse-jobsuche"}
r = requests.get("https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs",
                 params={"was": "Logistik", "angebotsart": 34, "size": 2, "page": 1}, headers=H, timeout=25)
d = r.json()
print("TOPKEYS |", [k for k in d if k != "ergebnisliste"], {k: d[k] for k in d if not isinstance(d[k], (list, dict))})
print("ITEM |", json.dumps(d["ergebnisliste"][0], ensure_ascii=False)[:3000])
