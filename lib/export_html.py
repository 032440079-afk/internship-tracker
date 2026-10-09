"""
Firestore'daki ilanlari okuyup tek dosyalik bir web paneli (docs/index.html) uretir; Firebase Hosting'de yayinlanir.

Sayfa herkese acik oldugu icin icine sadece herkese acik ilan bilgileri gomulur (baslik, sirket, konum, link, tarih).
Basvuru durumlari ve uygunluk skorlari sayfaya gomulmez: Google ile giris yapan izinli kullanicinin tarayicisi
bunlari dogrudan Firestore'dan okur (firestore.rules buna sadece ALLOWED_EMAILS'taki hesaplar icin izin verir).
Her kullanicinin durumlari ayridir: trackers/{email}/applications/{ilan_id}.
"""
import json
import os
from datetime import datetime, timezone
from lib import store
from lib.filters import is_europe_location, is_non_internship_role, has_excluded_keyword, fix_mojibake
OUTPUT_PATH = "docs/index.html"


def _fetch_all_offers() -> list[dict]:
    store._init()
    docs = store._db.collection("offers").order_by("scrapedAt", direction="DESCENDING").stream()
    offers = []
    for doc in docs:
        d = doc.to_dict()
        scraped = d.get("scrapedAt")
        # Sonradan eklenen filtreleri (Avrupa disi, alan disi, Werkstudent...) eski kayitlara da uygula
        if not is_europe_location(d.get("location", "")) or is_non_internship_role(d.get("title", "")) \
                or has_excluded_keyword(d.get("title", "")) or d.get("eligible") is False:
            continue
        offers.append({
            "id": doc.id,
            "title": fix_mojibake(d.get("title", "")), "company": fix_mojibake(d.get("company", "")),
            "location": fix_mojibake(d.get("location", "")), "source": d.get("source", ""),
            "url": d.get("url", ""), "scrapedAt": scraped.isoformat() if scraped else "",
            "postedDate": d.get("postedDate") or "", "postedApprox": bool(d.get("postedApprox")),
        })
    return offers


def render(offers: list[dict], generated_at: str) -> str:
    # "</" kacisi: ilan basliginda "</script>" olsa bile sayfa bozulmasin / kod calismasin
    data_json = json.dumps(offers, ensure_ascii=False).replace("</", "<\\/")
    return (HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
            .replace("__GENERATED_AT__", generated_at).replace("__TOTAL__", str(len(offers))))


def generate():
    offers = _fetch_all_offers()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(render(offers, generated_at))
    print(f"[export_html] {len(offers)} ilan yazildi -> {OUTPUT_PATH}")


HTML_TEMPLATE = r"""<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Staj Panosu</title>
<style>
:root{--bg:#0f1117;--panel:#171a23;--panel2:#1d212c;--line:#272c38;--text:#e7e9ee;--muted:#8d94a5;--accent:#6ea8fe;
--green:#4cc38a;--yellow:#e5b64a;--red:#ef6b6b;--purple:#b48cf2}
*{box-sizing:border-box}
[hidden]{display:none !important}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;margin:0;background:var(--bg);color:var(--text)}
.wrap{max-width:920px;margin:0 auto;padding:16px}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:6px}
h1{font-size:20px;margin:0}
.meta{color:var(--muted);font-size:13px;margin-bottom:14px}
.btn{border:1px solid var(--line);background:var(--panel2);color:var(--text);border-radius:8px;padding:7px 11px;font-size:13px;cursor:pointer;white-space:nowrap}
.btn:hover{border-color:#3a4152}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#0b1020;font-weight:600}
.btn.small{padding:5px 9px;font-size:12px}
.user{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:13px}
.banner{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:14px;font-size:14px;color:var(--muted)}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:120px}
.stat b{display:block;font-size:20px;color:var(--text)}
.stat span{font-size:12px;color:var(--muted)}
.tabs{display:flex;gap:6px;overflow-x:auto;margin-bottom:12px;padding-bottom:2px}
.tab{border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:999px;padding:7px 13px;font-size:14px;cursor:pointer;white-space:nowrap}
.tab.active{background:var(--panel2);color:var(--text);border-color:#3a4152}
.tab .n{color:var(--muted);margin-left:4px}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.controls input,.controls select{padding:8px 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--text);font-size:14px}
.controls input{flex:1;min-width:180px}
.count{color:var(--muted);font-size:13px;margin-bottom:8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:10px;transition:opacity .25s}
.card.leaving{opacity:.2}
.top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.title{font-size:15px;font-weight:600;color:var(--text);text-decoration:none;line-height:1.35}
.title:hover{color:var(--accent)}
.badges{display:flex;gap:6px;flex-shrink:0}
.badge{font-size:11px;font-weight:700;border-radius:6px;padding:3px 7px;white-space:nowrap}
.b-new{background:#21385f;color:#9cc3ff}
.b-hi{background:#173d2c;color:var(--green)}.b-mid{background:#3d3418;color:var(--yellow)}.b-lo{background:#3d1d1d;color:var(--red)}
.sub{color:var(--muted);font-size:13px;margin-top:4px}
.dates{color:var(--muted);font-size:12px;margin-top:3px}
.missing{margin-top:6px;display:flex;gap:5px;flex-wrap:wrap}
.chip{font-size:11px;border:1px solid var(--line);border-radius:999px;padding:2px 8px;color:var(--muted)}
.state{font-size:12px;margin-top:6px;color:var(--purple)}
.actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.more{display:block;margin:6px auto 30px}
.toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:#252a36;border:1px solid #3a4152;color:var(--text);
border-radius:10px;padding:10px 14px;font-size:14px;display:none;gap:12px;align-items:center;box-shadow:0 6px 24px #0008;z-index:10}
.toast button{background:none;border:none;color:var(--accent);font-weight:700;cursor:pointer;font-size:14px}
.empty{color:var(--muted);text-align:center;padding:30px 0}
@media (max-width:600px){.wrap{padding:12px}.stat{min-width:calc(50% - 5px)}.top{flex-direction:column}.badges{order:-1}}
</style></head>
<body><div class="wrap">
<header>
  <h1>🎯 Staj Panosu</h1>
  <div class="user" id="user"><button class="btn primary" id="login" hidden>Google ile giriş</button></div>
</header>
<div class="meta">Son güncelleme: __GENERATED_AT__ · __TOTAL__ ilan</div>
<div class="banner" id="banner" hidden></div>
<div class="stats" id="stats" hidden></div>
<div class="tabs" id="tabs" hidden></div>
<div class="controls">
  <input type="text" id="search" placeholder="Başlık, şirket veya konum ara…">
  <select id="company"><option value="">Tüm şirketler</option></select>
  <select id="sort">
    <option value="posted">En yeni yayın</option>
    <option value="found">En yeni bulunan</option>
    <option value="fit" id="sortFit" hidden>En uygun (CV)</option>
  </select>
</div>
<div class="count" id="count"></div>
<div id="list"></div>
<button class="btn more" id="more" hidden>Daha fazla göster</button>
</div>
<div class="toast" id="toast"><span id="toastText"></span><button id="undo">Geri al</button></div>

<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore-compat.js"></script>
<script>
const DATA = __DATA_JSON__;
const BY_ID = Object.fromEntries(DATA.map(o => [o.id, o]));
const STATUS = {applied:'📨 Başvurdum', interview:'🗣 Görüşme', rejected:'❌ Red', offer:'🎉 Kabul', skip:'🙈 Gizlendi'};
const APPLIED = ['applied','interview','rejected','offer'];
const TABS = [
  {key:'new', label:'Yeni', has: s => !s},
  {key:'applied', label:'Başvurdum', has: s => s === 'applied'},
  {key:'interview', label:'Görüşme', has: s => s === 'interview'},
  {key:'done', label:'Sonuçlanan', has: s => s === 'rejected' || s === 'offer'},
  {key:'skip', label:'Gizlenen', has: s => s === 'skip'},
];
const ACTIONS = {  // sekmeye gore kart butonlari
  new: ['applied', 'skip'], applied: ['interview', 'rejected', 'offer', 'reset'],
  interview: ['offer', 'rejected', 'reset'], done: ['reset'], skip: ['reset'],
};
const LABEL = {applied:'📨 Başvurdum', skip:'🙈 İlgilenmiyorum', interview:'🗣 Görüşme', rejected:'❌ Red', offer:'🎉 Kabul', reset:'↩ Yeni\'ye al'};
const $ = id => document.getElementById(id);
let db = null, user = null, profile = -1, apps = {}, matches = {}, tab = 'new', shown = 60, lastVisit = '', undoFn = null;

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl = u => /^https?:\/\//i.test(u || '') ? u : '#';
const store = {get(k){try{return localStorage.getItem(k)}catch(e){return null}}, set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
const MONTHS = ['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'];
function daysAgo(iso){ if(!iso) return null; const d = new Date(iso.length === 10 ? iso + 'T00:00:00Z' : iso); return Math.max(0, Math.floor((Date.now() - d) / 864e5)); }
function fmt(iso){ const d = new Date(iso.length === 10 ? iso + 'T00:00:00Z' : iso); return d.getUTCDate() + ' ' + MONTHS[d.getUTCMonth()]; }
function rel(n){ return n === 0 ? 'bugün' : n === 1 ? 'dün' : n + ' gün önce'; }
const statusOf = id => apps[id] && apps[id].status;

function dateLine(o){
  if (o.postedDate) {
    const n = daysAgo(o.postedDate);
    return '📅 Yayın: ' + (o.postedApprox ? '30+ gün önce' : rel(n) + ' (' + fmt(o.postedDate) + ')');
  }
  return '📅 Yayın tarihi bilinmiyor · bulundu: ' + (o.scrapedAt ? rel(daysAgo(o.scrapedAt)) + ' (' + fmt(o.scrapedAt) + ')' : '-');
}

// Uygunluk skoru giris yapan kisinin kendi CV'sine gore: Kaan'inki (profil 0) dogrudan alanlarda, digerleri "p1" vb.
function myMatch(id){
  const d = matches[id]; if (!d || profile < 0) return null;
  const m = profile === 0 ? d : d['p' + profile];
  return m && typeof m.score === 'number' ? m : null;
}

function fitBadge(id){
  const m = myMatch(id); if (!m) return '';
  const cls = m.score >= 70 ? 'b-hi' : m.score >= 40 ? 'b-mid' : 'b-lo';
  return '<span class="badge ' + cls + '" title="' + m.met + '/' + m.total + ' temel şart CV\'nde var">%' + m.score + ' uygun</span>';
}

function card(o){
  const s = statusOf(o.id), a = apps[o.id];
  const isNew = lastVisit && o.scrapedAt > lastVisit && !s;
  const m = myMatch(o.id);
  let state = '';
  if (s && a) {
    const t = a.updatedAt && a.updatedAt.toDate ? a.updatedAt.toDate() : null;
    const n = t ? Math.floor((Date.now() - t) / 864e5) : null;
    state = '<div class="state">' + STATUS[s] + (n !== null ? ' · ' + (s === 'applied' ? n + ' gündür cevap bekleniyor' : rel(n)) : '') + '</div>';
  }
  const actions = user ? (ACTIONS[tab] || []).map(k => '<button class="btn small" data-id="' + o.id + '" data-act="' + k + '">' + LABEL[k] + '</button>').join('') : '';
  return '<div class="card" id="c-' + o.id + '"><div class="top"><a class="title" href="' + esc(safeUrl(o.url)) + '" target="_blank" rel="noopener">' + esc(o.title) + '</a>'
    + ((isNew || fitBadge(o.id)) ? '<div class="badges">' + (isNew ? '<span class="badge b-new">YENİ</span>' : '') + fitBadge(o.id) + '</div>' : '') + '</div>'
    + '<div class="sub">' + esc(o.company || '-') + ' · ' + esc(o.location || 'konum yok') + '</div>'
    + '<div class="dates">' + dateLine(o) + '</div>'
    + (m && m.missing && m.missing.length ? '<div class="missing">' + m.missing.map(x => '<span class="chip">Eksik: ' + esc(x) + '</span>').join('') + '</div>' : '')
    + state + (actions ? '<div class="actions">' + actions + '</div>' : '') + '</div>';
}

function filtered(){
  const q = $('search').value.trim().toLowerCase(), company = $('company').value, sort = $('sort').value;
  const t = TABS.find(x => x.key === tab);
  let list = DATA.filter(o => (!user || t.has(statusOf(o.id)))
    && (!company || o.company === company)
    && (!q || (o.title + ' ' + o.company + ' ' + o.location).toLowerCase().includes(q)));
  const fit = o => (myMatch(o.id) || {score: -1}).score;
  const day = o => sort === 'found' ? o.scrapedAt : (o.postedDate || o.scrapedAt.slice(0, 10));
  if (sort === 'fit') list.sort((a, b) => fit(b) - fit(a) || (day(a) < day(b) ? 1 : -1));
  else if (user && tab !== 'new' && sort === 'posted') list.sort((a, b) => ((apps[b.id] || {}).updatedAt?.seconds || 0) - ((apps[a.id] || {}).updatedAt?.seconds || 0));
  else list.sort((a, b) => day(a) < day(b) ? 1 : day(a) > day(b) ? -1 : 0);
  return list;
}

function renderTabs(){
  if (!user) { $('tabs').hidden = true; return; }
  $('tabs').hidden = false;
  $('tabs').innerHTML = TABS.map(t => '<button class="tab' + (t.key === tab ? ' active' : '') + '" data-tab="' + t.key + '">' + t.label
    + '<span class="n">' + DATA.filter(o => t.has(statusOf(o.id))).length + '</span></button>').join('');
}

function renderStats(){
  if (!user) { $('stats').hidden = true; return; }
  const vals = Object.values(apps).map(a => a.status).filter(s => APPLIED.includes(s));
  const total = vals.length, c = s => vals.filter(v => v === s).length;
  const answered = c('interview') + c('rejected') + c('offer');
  const pct = n => total ? '%' + Math.round(100 * n / total) : '—';
  $('stats').hidden = false;
  $('stats').innerHTML = [
    ['Başvurulan', total], ['Dönüş oranı', pct(answered)], ['Görüşme oranı', pct(c('interview') + c('offer'))], ['Cevap bekleyen', c('applied')],
  ].map(([k, v]) => '<div class="stat"><b>' + v + '</b><span>' + k + '</span></div>').join('');
}

function render(){
  renderTabs(); renderStats();
  const list = filtered();
  $('count').textContent = list.length + ' ilan';
  $('list').innerHTML = list.length ? list.slice(0, shown).map(card).join('') : '<div class="empty">Bu sekmede ilan yok.</div>';
  $('more').hidden = list.length <= shown;
  $('more').textContent = 'Daha fazla göster (' + (list.length - shown) + ' kaldı)';
}

function toast(text, undo){
  $('toastText').textContent = text; undoFn = undo; $('undo').hidden = !undo;
  $('toast').style.display = 'flex'; clearTimeout(toast.t); toast.t = setTimeout(() => $('toast').style.display = 'none', 6000);
}

function ref(id){ return db.collection('trackers').doc(user.email.toLowerCase()).collection('applications').doc(id); }

async function write(id, status){
  const o = BY_ID[id];
  if (!status) return ref(id).delete();
  return ref(id).set({status, updatedAt: firebase.firestore.FieldValue.serverTimestamp(), title: o.title, company: o.company,
    history: firebase.firestore.FieldValue.arrayUnion({status, at: firebase.firestore.Timestamp.now()})}, {merge: true});
}

async function setStatus(id, status){
  const prev = statusOf(id) || null;
  const el = $('c-' + id); if (el) el.classList.add('leaving');
  try {
    await write(id, status);
    toast(status ? STATUS[status] + ' olarak işaretlendi' : "Yeni'ye geri alındı", async () => { await write(id, prev); $('toast').style.display = 'none'; });
  } catch (e) { if (el) el.classList.remove('leaving'); toast('Kaydedilemedi: ' + (e.code || e.message)); }
}

$('list').addEventListener('click', e => { const b = e.target.closest('button[data-act]'); if (!b) return;
  setStatus(b.dataset.id, b.dataset.act === 'reset' ? null : b.dataset.act); });
$('tabs').addEventListener('click', e => { const b = e.target.closest('button[data-tab]'); if (!b) return; tab = b.dataset.tab; shown = 60; render(); });
$('undo').addEventListener('click', () => undoFn && undoFn());
$('more').addEventListener('click', () => { shown += 60; render(); });
['search', 'company', 'sort'].forEach(id => $(id).addEventListener(id === 'search' ? 'input' : 'change', () => { shown = 60; render(); }));
[...new Set(DATA.map(o => o.company).filter(Boolean))].sort().forEach(c => { const el = document.createElement('option'); el.value = c; el.textContent = c; $('company').appendChild(el); });

function banner(html){ $('banner').innerHTML = html; $('banner').hidden = !html; }

async function onUser(u){
  user = u; apps = {}; matches = {}; profile = -1;
  const key = 'lastVisit:' + (u ? u.email : 'anon');
  lastVisit = store.get(key) || ''; store.set(key, new Date().toISOString());
  if (!u) {
    $('user').innerHTML = '<button class="btn primary" id="login">Google ile giriş</button>';
    $('login').onclick = login;
    banner('Başvurularını işaretlemek ve takip etmek için <b>Google ile giriş</b> yap. Giriş yapmadan sadece ilan listesi görünür.');
    $('sortFit').hidden = true; render(); return;
  }
  $('user').innerHTML = esc(u.email) + ' <button class="btn small" id="logout">Çıkış</button>';
  $('logout').onclick = () => firebase.auth().signOut();
  const email = u.email.toLowerCase();
  try {
    const me = await db.collection('allowed').doc(email).get();
    const d = me.exists ? me.data() : {};
    profile = typeof d.profile === 'number' ? d.profile : d.owner ? 0 : -1;
  } catch (e) {
    banner('Bu Google hesabının panoya erişim izni yok (' + esc(u.email) + '). İzinli hesapla giriş yap.');
    user = null; render(); return;
  }
  banner('');
  if (profile >= 0) {
    try {
      (await db.collection('matches').get()).forEach(d => matches[d.id] = d.data());
      $('sortFit').hidden = !Object.keys(matches).some(myMatch);
    } catch (e) {}
  }
  db.collection('trackers').doc(email).collection('applications').onSnapshot(snap => {
    apps = {}; snap.forEach(d => apps[d.id] = d.data()); render();
  }, e => toast('Durumlar okunamadı: ' + (e.code || e.message)));
  render();
}

function login(){
  const provider = new firebase.auth.GoogleAuthProvider();
  firebase.auth().signInWithPopup(provider).catch(e => {
    if (e.code === 'auth/popup-blocked' || e.code === 'auth/operation-not-supported-in-this-environment') firebase.auth().signInWithRedirect(provider);
    else toast('Giriş yapılamadı: ' + (e.code || e.message));
  });
}

render();
fetch('/__/firebase/init.json').then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(cfg => {
  firebase.initializeApp(cfg); db = firebase.firestore();
  firebase.auth().onAuthStateChanged(onUser);
}).catch(() => { banner('Giriş henüz ayarlanmadı; şimdilik sadece ilan listesi görünüyor.'); });
</script>
</body></html>
"""
