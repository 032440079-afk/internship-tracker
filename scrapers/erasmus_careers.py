"""
Kaynak: https://www.erasmuscareers.org/traineeships

Site Cloudflare tarzı bot koruması kullanıyor, düz `requests` ile 403
alınıyor. Bu yüzden Playwright (gerçek Chromium motoru) ile açıyoruz —
JS challenge'ı normal bir tarayıcı gibi geçiyor.

HTML yapısı (2026-08-21 itibarıyla doğrulandı):
  Kart:      div.card.eg-card
  Başlık:    .card-title
  Link:      a.card-link[href]        (örn. /traineeship-offers/xyz)
  Şirket:    .group--company [aria-label]
  Konum:     .card-labels .location   (örn. "Rome, Italy")
  Süre:      .card-labels .duration   (örn. "6 months")
  Ücret:     .card-labels .paid-traineeship
  Tip:       .card-labels .type

Sayfalama: /traineeships?page=0, ?page=1, ... (0-indexed)
Alt bilgi: "Displaying 1 - 10 of 126" gibi toplam sayıyı veriyor.
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://www.erasmuscareers.org/traineeships"
MAX_PAGES = 15  # güvenlik limiti (126 ilan / 10 per page ~= 13 sayfa)


def _parse_page_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    offers = []

    for card in soup.select("div.card.eg-card"):
        title_el = card.select_one(".card-title")
        link_el = card.select_one("a.card-link")
        if not title_el or not link_el or not link_el.get("href"):
            continue

        title = title_el.get_text(strip=True)
        href = link_el["href"]
        url = href if href.startswith("http") else f"https://www.erasmuscareers.org{href}"

        company_el = card.select_one(".group--company [aria-label]")
        company = company_el["aria-label"] if company_el else ""

        location_el = card.select_one(".card-labels .location")
        location = location_el.get_text(" ", strip=True) if location_el else ""

        duration_el = card.select_one(".card-labels .duration")
        duration = duration_el.get_text(strip=True) if duration_el else ""

        country = location.split(",")[-1].strip() if "," in location else location

        offers.append({
            "title": title,
            "company": company,
            "location": location,
            "country": country,
            "url": url,
            "description": f"{duration}",  # süre bilgisini description'a koyuyoruz, filtreye etkisi yok
        })

    return offers


def _has_next_page(html: str) -> bool:
    return "pager__item--next" in html


def scrape() -> list[dict]:
    all_offers = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )

        for page_num in range(MAX_PAGES):
            url = BASE_URL if page_num == 0 else f"{BASE_URL}?page={page_num}"
            page.goto(url, wait_until="domcontentloaded", timeout=45000)

            # Cookie banner çıkarsa kapatmayı dene (ilk sayfada olabilir)
            try:
                page.get_by_text("Accept", exact=False).first.click(timeout=3000)
            except Exception:
                pass

            html = page.content()
            page_offers = _parse_page_html(html)

            if not page_offers:
                break  # boş sayfa geldiyse bitmiştir

            all_offers.extend(page_offers)

            if not _has_next_page(html):
                break

        browser.close()

    return all_offers


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["company"], "|", r["location"], "|", r["url"])
