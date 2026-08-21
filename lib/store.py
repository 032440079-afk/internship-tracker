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
        "postedDate": offer.get("postedDate"),
        "scrapedAt": now,
        "keywords": offer.get("matched_keywords", []),
        "status": "new",
        "notes": "",
        "addedBy": "system",
    }
    _db.collection("offers").document(doc_id).set(data)
    return doc_id
