"""
Bir ilanın Kaan'ın alanına (Endüstri Mühendisliği / Operations / Supply Chain)
uygun olup olmadığına karar veren basit anahtar kelime filtresi.
"""
import re

from lib.config import RELEVANT_KEYWORDS, EXCLUDE_KEYWORDS, INTERNSHIP_KEYWORDS, NON_EUROPE_KEYWORDS

# Werkstudent / working student ve duales Studium, Almanya'daki bir universiteye kayitli ogrenciler icin yari zamanli
# isler / ders programlaridir; Erasmus ile tam zamanli staj arayan Kaan'a uymaz. Baslikta staj secenegi de varsa
# ("Praktikant / Werkstudent") ilan tutulur.
_STUDENT_JOB_TERMS = ("werkstudent", "working student", "studentische hilfskraft", "student assistant", "duales studium")
_INTERNSHIP_IN_TITLE = re.compile(r"praktik|\bintern(ship)?s?\b|\bstage\b|stagiair|stajyer")


def matched_keywords(title: str, description: str = "") -> list[str]:
    text = f"{title} {description}".lower()
    return [kw for kw in RELEVANT_KEYWORDS if kw in text]
def is_internship_type(title: str, description: str = "") -> bool:
    text = f"{title} {description}".lower()
    return any(kw in text for kw in INTERNSHIP_KEYWORDS)

def is_europe_location(location: str) -> bool:
    loc = (location or "").lower()
    return not any(kw in loc for kw in NON_EUROPE_KEYWORDS)

def is_student_job_only(title: str) -> bool:
    """Basligi sadece Werkstudent / duales Studium olan (staj secenegi sunmayan) ilanlar."""
    t = (title or "").lower()
    return any(term in t for term in _STUDENT_JOB_TERMS) and not _INTERNSHIP_IN_TITLE.search(t)


def is_relevant(title: str, description: str = "", location: str = "") -> tuple[bool, list[str]]:
    text = f"{title} {description}".lower()
    if not is_europe_location(location):
        return False, []
    if is_student_job_only(title):
        return False, []
    for bad in EXCLUDE_KEYWORDS:
        if bad in text:
            return False, []
    if not is_internship_type(title, description):
        return False, []
    matches = matched_keywords(title, description)
    return (len(matches) > 0), matches
