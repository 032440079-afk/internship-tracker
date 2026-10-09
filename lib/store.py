"""
Firestore katmanı: yeni ilanları kaydeder, daha önce görülenleri (URL hash'ine göre)
atlar. offers/{urlHash} şemasını kullanır (README'de tarif edilen şema).
"""
import hashlib
import json
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore

from lib import config

_app = None
_db = None


def _init():
    global _app, _db
    if _app is not None:
        return
    if not config.FIREBASE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON ortam değişkeni boş. "
            "Firebase servis hesabı JSON'unu env variable olarak eklemen lazım."
        )
    cred_dict = json.loads(config.FIREBASE_SERVICE_ACCOUNT_JSON)
    cred = credentials.Certificate(cred_dict)
    _app = firebase_admin.initialize_app(cred)
    _db = firestore.client()


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:24]


def is_new_offer(url: str) -> bool:
    """Bu ilan daha önce kaydedilmiş mi diye bakar. Yoksa True döner."""
    _init()
    doc_id = url_hash(url)
    doc = _db.collection("offers").document(doc_id).get()
    return not doc.exists


def save_offer(offer: dict):
    """
    offer sözlüğü şu alanları içermeli:
    title, company, location, country, source, url
    """
    _init()
    doc_id = url_hash(offer["url"])
    now = datetime.now(timezone.utc)
    data = {
        "title": offer.get("title", ""),
        "company": offer.get("company", ""),
        "location": offer.get("location", ""),
        "country": offer.get("country", ""),
        "source": offer.get("source", ""),
        "url": offer["url"],
        "postedDate": offer.get("postedDate"),        # "YYYY-MM-DD" (kaynak veriyorsa)
        "postedApprox": offer.get("postedApprox", False),  # True: "30+ gun once" gibi yaklasik
        "scrapedAt": now,
        "keywords": offer.get("matched_keywords", []),
        "eligible": offer.get("eligible", True),  # sinif / donem sarti (lib/eligibility.py)
        "status": "new",
        "notes": "",
        "addedBy": "system",
    }
    _db.collection("offers").document(doc_id).set(data)
    return doc_id


# ---------- basvuru takibi (lib/tracking.py, web paneli) ----------
# Her kisinin durumlari ayri: trackers/{email}/applications/{ilan_id}
# Erisim listesi: allowed/{email} (ALLOWED_EMAILS secret'indan; ilk e-posta Kaan = owner, profile = listedeki sira)
# Telegram sohbeti -> e-posta eslemesi: telegram_links/{chat_id} (/bagla komutuyla)
# Uygunluk skorlari: matches/{ilan_id}; Kaan'inki dogrudan alanlarda, 2. kisininki "p1" alaninda
# Firestore kurallari (firestore.rules) bu koleksiyonlari sadece izinli hesaplara acar.

def sync_allowed(emails: list[str]):
    """ALLOWED_EMAILS listesini allowed koleksiyonuna yazar; listede olmayanlari siler."""
    _init()
    wanted = [e.strip().lower() for e in emails if e.strip()]
    col = _db.collection("allowed")
    for i, email in enumerate(wanted):
        col.document(email).set({"owner": i == 0, "profile": i})
    for doc in col.stream():
        if doc.id not in wanted:
            doc.reference.delete()


def allowed_emails() -> list[str]:
    _init()
    return [d.id for d in _db.collection("allowed").stream()]


def link_telegram(chat_id: str, email: str):
    _init()
    _db.collection("telegram_links").document(str(chat_id)).set({"email": email.lower()})


def telegram_links() -> dict[str, str]:
    """{chat_id: email}"""
    _init()
    return {d.id: d.to_dict().get("email", "") for d in _db.collection("telegram_links").stream()}


def set_application_status(email: str, doc_id: str, status: str) -> dict | None:
    """Kisinin ilan durumunu yazar; ilan yoksa None, varsa ilan bilgisini dondurur."""
    _init()
    offer = _db.collection("offers").document(doc_id).get()
    if not offer.exists:
        return None
    data = offer.to_dict()
    now = datetime.now(timezone.utc)
    _db.collection("trackers").document(email).collection("applications").document(doc_id).set({
        "status": status,
        "updatedAt": now,
        "title": data.get("title", ""),
        "company": data.get("company", ""),
        "history": firestore.ArrayUnion([{"status": status, "at": now}]),
    }, merge=True)
    return data


def applications(email: str) -> list[dict]:
    _init()
    return [d.to_dict() for d in _db.collection("trackers").document(email).collection("applications").stream()]


def save_match(doc_id: str, match: dict, profile: int = 0):
    _init()
    _db.collection("matches").document(doc_id).set(match if profile == 0 else {f"p{profile}": match}, merge=True)


def restore_offer(doc_id: str) -> dict | None:
    """Yanlislikla sinif sartiyla elenmis ilani geri alir: panoda gorunur ve bir sonraki calismada CV'si uretilir."""
    _init()
    ref = _db.collection("offers").document(doc_id)
    doc = ref.get()
    if not doc.exists:
        return None
    ref.update({"eligible": True, "cvPending": True})
    return doc.to_dict()


def offers_cv_pending() -> list[tuple[str, dict]]:
    _init()
    return [(d.id, d.to_dict()) for d in _db.collection("offers").where("cvPending", "==", True).stream()]


def clear_cv_pending(doc_id: str):
    _init()
    _db.collection("offers").document(doc_id).update({"cvPending": False})
