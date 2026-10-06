"""
BMW, Mercedes-Benz, Porsche ve benzeri JS-agirlikli, CSS-selector ile
taranamayan kariyer sitelerini render edip bir LLM (NVIDIA NIM) ile
yapisal ilan listesi cikartir. Diger scraper'lar gibi scrape() -> list[dict]
dondurur, run.py tarafindan aynen cagrilir.

Gereken ortam degiskeni: NVIDIA_API_KEY (build.nvidia.com hesabindan alinir)
Tanimli degilse bu scraper sessizce atlanir, pipeline'in geri kalani calisir.
"""
import json
import os
import re
from urllib.parse import quote
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from openai import OpenAI
from lib.config import NVIDIA_API_KEY

TARGETS = [
    {"name": "BMW Group", "url": "https://bmw.jobs/VbDLOr81"},
    {"name": "Mercedes-Benz", "url": "https://jobs.mercedes-benz.com/?TargetGroup.Code=2&CareerLevel.Code=19"},
    {"name": "Porsche", "url": "https://jobs.porsche.com/index.php?ac=search_result&search_criterion_keyword%5B%5D=internship"},
    # Otomotiv
    {"name": "Daimler Truck", "url": "https://www.daimlertruck.com/en/career/job-search"},
    {"name": "Michelin", "url": "https://jobs.michelinman.com/job-offer-result-list"},
    # Havacilik & sanayi
    {"name": "Siemens", "url": "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/intern"},
    {"name": "Siemens Energy", "url": "https://jobs.siemens-energy.com/en_US/jobs"},
    {"name": "ABB", "url": "https://careers.abb/global/en/search-results?keywords=intern"},
    {"name": "Alstom", "url": "https://jobsearch.alstom.com/search/?q=intern"},
    {"name": "Hilti", "url": "https://careers.hilti.group/en/jobs/"},
    {"name": "Atlas Copco", "url": "https://www.atlascopcogroup.com/en/careers/jobs/job-overview"},
    {"name": "Thales", "url": "https://careers.thalesgroup.com/global/en/search-results?keywords=intern"},
    {"name": "Orsted", "url": "https://orsted.com/en/careers/vacancies-list"},
    {"name": "Signify", "url": "https://www.careers.signify.com/global/en/search-results?keywords=intern"},
    # Kimya & tuketim
    {"name": "BASF", "url": "https://basf.jobs/search/?q=intern"},
    {"name": "L'Oreal", "url": "https://careers.loreal.com/en_US/jobs/SearchJobs/intern"},
    {"name": "Ferrero", "url": "https://www.ferrerocareers.com/int/en/jobs"},
    {"name": "Bayer", "url": "https://talent.bayer.com/careers?query=intern"},
    {"name": "Henkel", "url": "https://www.henkel.com/careers/find-your-job-apply"},
    {"name": "P&G", "url": "https://www.pgcareers.com/eu/en/internships"},
    # Lojistik
    {"name": "DHL Group", "url": "https://careers.dhl.com/global/en/internships"},
    {"name": "DSV (DB Schenker)", "url": "https://www.dsv.com/en-gb/careers/job-search"},
    {"name": "Kuehne+Nagel", "url": "https://jobs.kuehne-nagel.com/global/en/search-results?keywords=intern"},
]

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
# Llama 3.3 70B ve Nemotron Super 49B 2026-08-26'da kaldirildi (HTTP 410). Model ileride
# yine kalkarsa kod degistirmeden NIM_MODEL ortam degiskeniyle degistirilebilir.
NIM_MODEL = os.environ.get("NIM_MODEL") or "nvidia/nemotron-3.5-lightning-30b-a3b"

SYSTEM_PROMPT = """Sen bir bilgi cikarma motorusun. Sana bir sirket kariyer sayfasinin gorunur metni verilecek. Erasmus+ veya J-1 staj basvurusuna uyabilecek her staj/working student/thesis/trainee ilanini cikart. Tam zamanli, kidemli ve yonetici pozisyonlarini yoksay. SADECE bu JSON semasina uyan bir obje ile cevap ver, aciklama veya markdown ekleme:

{"listings": [{"title": "string", "location": "string or null", "url": "string"}]}

"url" icin SADECE "Sayfadaki linkler" listesindeki bir adresi kullan; ilana ait link yoksa null yaz, asla adres uydurma.
Uygun ilan yoksa {"listings": []} don."""

MAX_LINKS_IN_PROMPT = 150

def _fetch_rendered_text(url: str, timeout_ms: int = 20000) -> tuple[str, list[tuple[str, str]]]:
    """Sayfanin gorunur metnini ve (link metni, mutlak adres) listesini dondurur."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ))
        try:
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
        except PlaywrightTimeout:
            pass  # bazi siteler hic "networkidle" olmuyor; o ana kadar yuklenen metni kullan
        text = page.inner_text("body")
        links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => [(e.innerText || '').trim(), e.href])"
        )
        browser.close()
        return text, [(t, h) for t, h in links if h.startswith("http")]

def _extract_listings(page_text: str, company: str, links: list[tuple[str, str]]) -> list[dict]:
    client = OpenAI(base_url=NIM_BASE_URL, api_key=NVIDIA_API_KEY)
    link_lines = "\n".join(f"- {t[:120]} -> {h}" for t, h in links if len(t) > 5)[:8000]
    user_prompt = (f"Sirket: {company}\n\nSayfa metni:\n\"\"\"\n{page_text[:15000]}\n\"\"\"\n\n"
                   f"Sayfadaki linkler:\n{link_lines}")
    # Model bazen yarim JSON donduruyor (orn. sadece '{"'); bir kez daha dene.
    for attempt in range(2):
        response = client.chat.completions.create(
            model=NIM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=4096,
            response_format={"type": "json_object"},
            # Akil yurutme modu kapali: token butcesi dusunmeye gitmesin, cevap direkt JSON olsun.
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        try:
            data = _parse_json(response.choices[0].message.content or "")
            return data.get("listings", [])
        except ValueError:
            if attempt == 1:
                raise

def _parse_json(content: str) -> dict:
    # Model bazen <think> blogu veya ```json``` cercevesi ekliyor; ilk {...} blogunu al.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end < start:
        raise ValueError(f"Model JSON dondurmedi: {content[:200]!r}")
    return json.loads(content[start:end + 1])

def scrape() -> list[dict]:
    if not NVIDIA_API_KEY:
        print("[nim_fallback] NVIDIA_API_KEY tanimli degil, atlaniyor.")
        return []

    all_offers = []
    for target in TARGETS:
        name = target["name"]
        try:
            text, links = _fetch_rendered_text(target["url"])
            page_urls = {h.rstrip("/") for _, h in links}
            listings = _extract_listings(text, name, links)
            for item in listings:
                title = item.get("title", "")
                if not title:
                    continue
                url = (item.get("url") or "").rstrip("/")
                if url not in page_urls:
                    # Model sayfada olmayan bir adres verdi (uydurma olabilir) ya da hic vermedi:
                    # kariyer sayfasina yonlendir, ama basliga gore benzersiz yap ki ayni sirketin
                    # ilanlari tek bir URL altinda birlesip "zaten kayitli" sayilmasin.
                    url = f"{target['url']}#{quote(title[:80])}"
                all_offers.append({
                    "title": title,
                    "company": name,
                    "location": item.get("location", "") or "",
                    "country": "",
                    "url": url,
                    "description": "",
                })
        except Exception as e:
            print(f"[HATA] {name} scrape edilemedi (nim_fallback): {e}")

    return all_offers

if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} ilan bulundu")
    for r in results[:10]:
        print(" -", r["title"], "|", r["company"], "|", r["url"])
