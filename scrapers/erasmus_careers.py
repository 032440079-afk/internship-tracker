
"""
Kaynak: https://www.erasmuscareers.org/offers
(Eski erasmusintern.org buraya taşınıyor — bkz. proje notları)

⚠️ ÖNEMLİ NOT: Bu site JavaScript ile render ediliyor (SPA). Basit bir
`requests.get()` çoğu zaman kartların dolu HTML'ini DÖNDÜRMEYEBİLİR —
ilk yükte sunucu sadece bir kaç kart render edip gerisini client-side
JS ile getiriyor olabilir.

Bu dosya "iyimser" bir HTML-parse denemesi yapıyor. Eğer canlıda
çalıştırıldığında offers listesi boş dönerse (ki muhtemel), iki seçenek var:

  1) Tarayıcıda F12 > Network > Fetch/XHR sekmesini açıp `/offers` sayfasını
     yenile, "offers" veya "api" geçen bir istek ara. Onun URL'sini ve
     response JSON yapısını bana gönder, ben scraper'ı ona göre yeniden yazarım
     (muhtemelen bu en temiz ve en hızlı yol).
  2) API bulunamazsa Playwright ile headless browser scraping'e geçilir
     (daha yavaş ama garanti çalışır).

Şimdilik bu iskelet, CSS selector'ları güncellenmeye hazır şekilde duruyor.
"""
import requests
from bs4 import BeautifulSoup

from lib.config import REQUEST_HEADERS

BASE_URL = "https://www.erasmuscareers.org/offers"


BROWSER_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Sec-Fetch-Mode": "navigate",
}


def scrape() -> list[dict]:
    session = requests.Session()
    resp = session.get(BASE_URL, headers=BROWSER_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    offers = []

    # TAHMİNİ selector'lar — gerçek HTML yapısı doğrulanınca güncellenecek.
    # Devtools'ta ilan kartlarının class/tag yapısını bulup burayı güncelleyeceğiz.
    cards = soup.select("a[href*='/offers/']")

    seen_urls = set()
    for card in cards:
        href = card.get("href", "")
        if not href or "/offers/" not in href or href.rstrip("/").endswith("/offers"):
            continue
        url = href if href.startswith("http") else f"https://www.erasmuscareers.org{href}"
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = card.get_text(strip=True) or "Başlıksız ilan"

        offers.append({
            "title": title,
            "company": "",       # detay sayfasından çekilebilir, v1'de boş
            "location": "",      # aynı şekilde
            "country": "",
            "url": url,
            "description": "",
        })

    return offers


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["url"])
