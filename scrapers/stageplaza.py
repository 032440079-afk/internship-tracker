"""
Kaynak: https://stageplaza.nl/stage/engineering/
Hollanda staj ilanları. Site statik/server-rendered HTML kullanıyor
(SPA değil), bu yüzden requests + BeautifulSoup ile büyük ihtimalle
doğrudan çalışır. Yine de CSS selector'ları canlı denemeyle doğrulanmalı.
"""
import requests
from bs4 import BeautifulSoup

from lib.config import REQUEST_HEADERS

BASE_URL = "https://stageplaza.nl/stage/engineering/"


def scrape() -> list[dict]:
    resp = requests.get(BASE_URL, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    offers = []

    # TAHMİNİ selector — sayfadaki ilan kartı linklerini yakalamaya çalışıyor.
    # Gerçek class isimleri Inspect ile doğrulanınca netleştirilecek.
    cards = soup.select("a[href*='/stage/']")

    seen_urls = set()
    for card in cards:
        href = card.get("href", "")
        if not href or href.rstrip("/") in (
            "/stage", "/stage/engineering", "/stage/rotterdam"
        ):
            continue
        url = href if href.startswith("http") else f"https://stageplaza.nl{href}"
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = card.get_text(strip=True)
        if not title:
            continue

        offers.append({
            "title": title,
            "company": "",
            "location": "",
            "country": "Netherlands",
            "url": url,
            "description": "",
        })

    return offers


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["url"])
