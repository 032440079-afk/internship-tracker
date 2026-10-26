"""
Uretilen CV / on yazi PDF'lerini Supabase Storage'daki gizli bir bucket'a yukler ve panoda gosterilecek sureli
indirme linkleri (signed URL) uretir.

- Bucket herkese kapali (public=false). Yukleme ve link uretme sadece GitHub Actions'ta, SUPABASE_SECRET_KEY ile yapilir.
- Linkler Firestore'da trackers/{e-posta}/documents/{ilan_id} altina yazilir; firestore.rules bunlari sadece o
  e-postayla giris yapan kisiye acar. Herkese acik panoya (docs/index.html) link gomulmez.
- SUPABASE_URL / SUPABASE_SECRET_KEY yoksa hicbir sey yapilmaz (Telegram gonderimi etkilenmez).
"""
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
BUCKET = os.environ.get("SUPABASE_BUCKET", "applications").strip()
LINK_DAYS = 180  # indirme linklerinin gecerlilik suresi

_bucket_ready = False


def enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def _headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_SECRET_KEY}
    if SUPABASE_SECRET_KEY.startswith("eyJ"):  # eski tip service_role JWT; yeni sb_secret_ anahtarlari sadece apikey ister
        h["Authorization"] = f"Bearer {SUPABASE_SECRET_KEY}"
    h.update(extra or {})
    return h


def _ensure_bucket():
    """Gizli bucket'i ilk kullanimda olusturur (zaten varsa dokunmaz)."""
    global _bucket_ready
    if _bucket_ready:
        return
    r = requests.post(f"{SUPABASE_URL}/storage/v1/bucket", headers=_headers({"Content-Type": "application/json"}),
                      json={"id": BUCKET, "name": BUCKET, "public": False}, timeout=20)
    if r.status_code not in (200, 201) and "already exists" not in r.text.lower() and r.status_code != 409:
        raise RuntimeError(f"bucket olusturulamadi: HTTP {r.status_code}")
    _bucket_ready = True


def upload(profile: int, doc_id: str, path: str) -> str:
    """PDF'i p{profile}/{ilan_id}/{dosya_adi} olarak yukler, sureli indirme linkini dondurur."""
    _ensure_bucket()
    key = f"p{profile}/{doc_id}/{os.path.basename(path)}"
    obj = quote(f"{BUCKET}/{key}")
    with open(path, "rb") as f:
        r = requests.post(f"{SUPABASE_URL}/storage/v1/object/{obj}", data=f.read(), timeout=60,
                          headers=_headers({"Content-Type": "application/pdf", "x-upsert": "true"}))
    if r.status_code not in (200, 201):
        raise RuntimeError(f"yukleme basarisiz: HTTP {r.status_code}")
    r = requests.post(f"{SUPABASE_URL}/storage/v1/object/sign/{obj}", headers=_headers({"Content-Type": "application/json"}),
                      json={"expiresIn": LINK_DAYS * 86400}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"link olusturulamadi: HTTP {r.status_code}")
    signed = r.json().get("signedURL") or r.json().get("signedUrl")
    if not signed:
        raise RuntimeError("link olusturulamadi: cevapta signedURL yok")
    return f"{SUPABASE_URL}/storage/v1{signed}" if signed.startswith("/") else signed


def upload_application(profile: int, doc_id: str, cv_path: str, letter_path: str | None) -> dict:
    """{"cv": link, "coverLetter": link veya None, "expiresAt": zaman} dondurur."""
    return {
        "cv": upload(profile, doc_id, cv_path),
        "coverLetter": upload(profile, doc_id, letter_path) if letter_path else None,
        "expiresAt": datetime.now(timezone.utc) + timedelta(days=LINK_DAYS),
    }
