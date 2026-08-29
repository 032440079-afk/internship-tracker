"""
Firestore'daki tum ilanlari okuyup filtrelenebilir, tek dosyalik bir
HTML sayfasi (docs/index.html) uretir. GitHub Pages ile bu dosya
https://<kullanici>.github.io/internship-tracker/ adresinden
tarayicida acilabilir, Telegram disinda goruntuleme/filtreleme saglar.
"""
import json
from datetime import datetime, timezone
from lib import store

OUTPUT_PATH = "docs/index.html"

def _fetch_all_offers() -> list[dict]:
    store._init()
    docs = store._db.collection("offers").order_by("scrapedAt", direction="DESCENDING").stream()
    offers = []
    for doc in docs:
        d = doc.to_dict()
        scraped = d.get("scrapedAt")
        offers.append({
            "title": d.get("title", ""), "company": d.get("company", ""),
            "location": d.get("location", ""), "source": d.get("source", ""),
            "url": d.get("url", ""), "scrapedAt": scraped.isoformat() if scraped else "",
        })
    return offers

def generate():
    offers = _fetch_all_offers()
    data_json = json.dumps(offers, ensure_ascii=False)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json).replace("__GENERATED_AT__", generated_at).replace("__TOTAL__", str(len(offers)))
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[export_html] {len(offers)} ilan yazildi -> {OUTPUT_PATH}")

HTML_TEMPLATE = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Staj Ilanlari</title>
<style>
body{font-family:-apple-system,Arial,sans-serif;margin:0;padding:20px;background:#0f1117;color:#e6e6e6}
h1{font-size:20px;margin-bottom:4px}
.meta{color:#888;font-size:13px;margin-bottom:16px}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
input[type=text]{flex:1;min-width:200px}
input,select{padding:8px 10px;border-radius:6px;border:1px solid #333;background:#1a1d27;color:#eee;font-size:14px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #262a35}
th{background:#1a1d27;cursor:pointer;position:sticky;top:0}
tr:hover{background:#171a22}
a{color:#6ea8fe;text-decoration:none}
a:hover{text-decoration:underline}
.count{color:#aaa;font-size:13px;margin-bottom:8px}
</style></head>
<body>
<h1>Staj Ilanlari</h1>
<div class="meta">Son guncelleme: __GENERATED_AT__ &middot; Toplam kayit: __TOTAL__</div>
<div class="controls">
<input type="text" id="search" placeholder="Baslik veya sirket ara...">
<select id="companyFilter"><option value="">Tum sirketler</option></select>
<select id="sourceFilter"><option value="">Tum kaynaklar</option></select>
</div>
<div class="count" id="count"></div>
<table><thead><tr>
<th data-key="title">Baslik</th><th data-key="company">Sirket</th><th data-key="location">Konum</th><th data-key="scrapedAt">Tarih</th>
</tr></thead><tbody id="rows"></tbody></table>
<script>
const DATA = __DATA_JSON__;
const searchEl = document.getElementById('search');
const companyEl = document.getElementById('companyFilter');
const sourceEl = document.getElementById('sourceFilter');
const rowsEl = document.getElementById('rows');
const countEl = document.getElementById('count');
[...new Set(DATA.map(o => o.company))].sort().forEach(c => { const o = document.createElement('option'); o.value = c; o.textContent = c; companyEl.appendChild(o); });
[...new Set(DATA.map(o => o.source).filter(Boolean))].sort().forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = s; sourceEl.appendChild(o); });
let sortKey = 'scrapedAt', sortDir = -1;
function render() {
  const q = searchEl.value.trim().toLowerCase(), company = companyEl.value, source = sourceEl.value;
  let filtered = DATA.filter(o => (!company || o.company === company) && (!source || o.source === source) && (!q || o.title.toLowerCase().includes(q) || o.company.toLowerCase().includes(q)));
  filtered.sort((a, b) => { const av = a[sortKey] || '', bv = b[sortKey] || ''; return av < bv ? -sortDir : av > bv ? sortDir : 0; });
  countEl.textContent = filtered.length + ' ilan gosteriliyor';
  rowsEl.innerHTML = filtered.map(o => '<tr><td><a href="' + o.url + '" target="_blank" rel="noopener">' + o.title + '</a></td><td>' + o.company + '</td><td>' + (o.location || '-') + '</td><td>' + (o.scrapedAt || '').slice(0, 10) + '</td></tr>').join('');
}
document.querySelectorAll('th').forEach(th => th.addEventListener('click', () => { const key = th.dataset.key; if (sortKey === key) sortDir *= -1; else { sortKey = key; sortDir = 1; } render(); }));
searchEl.addEventListener('input', render); companyEl.addEventListener('change', render); sourceEl.addEventListener('change', render);
render();
</script>
</body></html>
"""
