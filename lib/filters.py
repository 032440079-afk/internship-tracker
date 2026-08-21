"""
Bir ilanın Kaan'ın alanına (Endüstri Mühendisliği / Operations / Supply Chain)
uygun olup olmadığına karar veren basit anahtar kelime filtresi.
"""
from lib.config import RELEVANT_KEYWORDS, EXCLUDE_KEYWORDS


def matched_keywords(title: str, description: str = "") -> list[str]:
    text = f"{title} {description}".lower()
    return [kw for kw in RELEVANT_KEYWORDS if kw in text]


def is_relevant(title: str, description: str = "") -> tuple[bool, list[str]]:
    text = f"{title} {description}".lower()
    for bad in EXCLUDE_KEYWORDS:
        if bad in text:
            return False, []
    matches = matched_keywords(title, description)
    return (len(matches) > 0), matches
