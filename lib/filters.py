"""
Bir ilanın Kaan'ın alanına (Endüstri Mühendisliği / Operations / Supply Chain)
uygun olup olmadığına karar veren basit anahtar kelime filtresi.
"""
import re

from lib.config import RELEVANT_KEYWORDS, EXCLUDE_KEYWORDS, INTERNSHIP_KEYWORDS, NON_EUROPE_KEYWORDS, NON_EUROPE_ISO3

# Kaan Turkiye'de okuyup Erasmus+ ile tam zamanli staj ariyor. Su ilanlar ona uymaz:
#  - Werkstudent / working student: Almanya'daki bir universiteye kayitli ogrenciler icin yari zamanli is
#  - duales Studium: Almanya'da bir lisans programi
#  - trainee / graduate programlari: mezunlar icin tam zamanli is
#  - bitirme tezi (Abschlussarbeit / thesis): cogunlukla son sinif veya master ogrencisi ister
# Baslikta staj secenegi de varsa ("Praktikant / Werkstudent", "Praktikum oder Abschlussarbeit") ilan tutulur.
_NON_INTERNSHIP_TERMS = (
    "werkstudent", "working student", "studentische hilfskraft", "student assistant", "duales studium",
    "trainee", "graduate program", "thesis", "abschlussarbeit", "masterarbeit", "bachelorarbeit",
)
_INTERNSHIP_IN_TITLE = re.compile(r"praktik|\bintern(ship)?s?\b|\bstage\b|stagiair|stajyer")


def matched_keywords(title: str, description: str = "") -> list[str]:
    text = f"{title} {description}".lower()
    return [kw for kw in RELEVANT_KEYWORDS if kw in text]
def is_internship_type(title: str, description: str = "") -> bool:
    text = f"{title} {description}".lower()
    return any(kw in text for kw in INTERNSHIP_KEYWORDS)

def is_europe_location(location: str) -> bool:
    loc = (location or "").lower()
    if any(kw in loc for kw in NON_EUROPE_KEYWORDS):
        return False
    return not (set(re.findall(r"\b[A-Z]{3}\b", location or "")) & NON_EUROPE_ISO3)


def has_excluded_keyword(title: str) -> bool:
    t = (title or "").lower()
    return any(bad in t for bad in EXCLUDE_KEYWORDS)


def fix_mojibake(text: str) -> str:
    """Kaynakta yanlis kodlanmis metni duzeltir ("stationÃ¤re" -> "stationäre")."""
    if "Ã" not in (text or ""):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

def is_non_internship_role(title: str) -> bool:
    """Basligi Werkstudent / duales Studium / trainee / tez olan ve staj secenegi sunmayan ilanlar."""
    t = (title or "").lower()
    return any(term in t for term in _NON_INTERNSHIP_TERMS) and not _INTERNSHIP_IN_TITLE.search(t)


def is_relevant(title: str, description: str = "", location: str = "") -> tuple[bool, list[str]]:
    text = f"{title} {description}".lower()
    if not is_europe_location(location):
        return False, []
    if is_non_internship_role(title):
        return False, []
    for bad in EXCLUDE_KEYWORDS:
        if bad in text:
            return False, []
    if not is_internship_type(title, description):
        return False, []
    matches = matched_keywords(title, description)
    return (len(matches) > 0), matches
