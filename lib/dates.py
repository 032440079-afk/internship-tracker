"""
Ilan kaynaklarinin farkli bicimlerdeki yayin tarihlerini "YYYY-MM-DD" bicimine cevirir.
Taninmayan bicimlerde None dondurur (ilan yine kaydedilir, sitede sadece "bulundu" tarihi gorunur).
"""
import re
from datetime import date, datetime, timedelta, timezone

_MONTHS = {
    # Ingilizce / Almanca / Fransizca / Hollandaca kisaltmalar (ilk 3 harf yeterli)
    "jan": 1, "feb": 2, "fev": 2, "fév": 2, "mar": 3, "mär": 3, "mrz": 3, "apr": 4, "avr": 4, "may": 5, "mai": 5,
    "mei": 5, "jun": 6, "jui": 6, "jul": 7, "aug": 8, "aoû": 8, "aou": 8, "sep": 9, "oct": 10, "okt": 10,
    "nov": 11, "dec": 12, "dez": 12, "déc": 12,
}


def _iso(d: date) -> str | None:
    # Saçma tarihleri ele (gelecekte ya da cok eski)
    today = datetime.now(timezone.utc).date()
    if d > today + timedelta(days=2) or d < today - timedelta(days=730):
        return None
    return d.isoformat()


def parse_date(value) -> str | None:
    """Unix zaman damgasi, ISO metni, "October 5, 2026", "Oct 5, 2026", "05.10.2026", "5. Okt. 2026" vb."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            ts = value / 1000 if value > 1e11 else value  # milisaniye ise saniyeye cevir
            return _iso(datetime.fromtimestamp(ts, tz=timezone.utc).date())
        text = str(value).strip()
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)  # ISO: 2026-10-05 / 2026-10-05T12:00:00Z
        if m:
            return _iso(date(int(m[1]), int(m[2]), int(m[3])))
        m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", text)  # 05.10.2026 / 5/10/2026 (gun once)
        if m:
            return _iso(date(int(m[3]), int(m[2]), int(m[1])))
        m = re.search(r"([A-Za-zÀ-ÿ]{3})[A-Za-zÀ-ÿ]*\.?\s+(\d{1,2}),?\s+(\d{4})", text)  # October 5, 2026
        if m and m[1].lower() in _MONTHS:
            return _iso(date(int(m[3]), _MONTHS[m[1].lower()], int(m[2])))
        m = re.search(r"(\d{1,2})\.?\s+([A-Za-zÀ-ÿ]{3})[A-Za-zÀ-ÿ]*\.?\s+(\d{4})", text)  # 5. Okt. 2026 / 5 oct 2026
        if m and m[2].lower() in _MONTHS:
            return _iso(date(int(m[3]), _MONTHS[m[2].lower()], int(m[1])))
    except (ValueError, OverflowError, OSError):
        return None
    return None


def parse_relative(text: str) -> tuple[str | None, bool]:
    """Workday "Posted Today" / "Posted Yesterday" / "Posted 3 Days Ago" / "Posted 30+ Days Ago".
    (tarih, yaklasik_mi) dondurur; 30+ gun icin tarih bugunden 30 gun oncesi ve yaklasik=True."""
    t = (text or "").lower()
    today = datetime.now(timezone.utc).date()
    if "today" in t or "heute" in t:
        return today.isoformat(), False
    if "yesterday" in t or "gestern" in t:
        return (today - timedelta(days=1)).isoformat(), False
    m = re.search(r"(\d+)\s*(\+)?\s*(days?|tage?n?)", t)
    if m:
        return (today - timedelta(days=int(m[1]))).isoformat(), bool(m[2])
    return None, False
