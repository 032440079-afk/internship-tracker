"""
BMW, Mercedes-Benz ve Porsche gibi JS-agirlikli, CSS-selector ile
taranamayan kariyer sitelerini render edip bir LLM (NVIDIA NIM) ile
yapisal ilan listesi cikartir. Diger scraper'lar gibi scrape() -> list[dict]
dondurur, run.py tarafindan aynen cagrilir.

Gereken ortam degiskeni: NVIDIA_API_KEY (build.nvidia.com hesabindan alinir)
Tanimli degilse bu scraper sessizce atlanir, pipeline'in geri kalani calisir.
"""
import json
from playwright.sync_api import sync_playwright
from openai import OpenAI
from lib.config import NVIDIA_API_KEY

TARGETS = [
    {"name": "BMW Group", "url": "https://bmw.jobs/VbDLOr81"},
    {"name": "Mercedes-Benz", "url": "https://jobs.mercedes-benz.com/?TargetGroup.Code=2&CareerLevel.Code=19"},
    {"name": "Porsche", "url": "https://jobs.porsche.com/index.php?ac=search_result&search_criterion_keyword%5B%5D=internship"},
]

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL = "meta/llama-3.3-70b-instruct"

SYSTEM_PROMPT = """Sen bir bilgi cikarma motorusun. Sana bir sirket kariyer sayfasinin gorunur metni verilecek. Erasmus+ veya J-1 staj basvurusuna uyabilecek her staj/working student/thesis/trainee ilanini cikart. Tam zamanli, kidemli ve yonetici pozisyonlarini yoksay. SADECE bu JSON semasina uyan bir obje ile cevap ver, aciklama veya markdown ekleme:

{"listings": [{"title": "string", "location": "string or null", "url": "string"}]}

Uygun ilan yoksa {"listings": []} don."""

def _fetch_rendered_text(url: str, timeout_ms: int = 20000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ))
        page.goto(url, timeout=timeout_ms, wait_until="networkidle")
        text = page.inner_text("body")
        browser.close()
        return text

def _extract_listings(page_text: str, company: str) -> list[dict]:
    client = OpenAI(base_url=NIM_BASE_URL, api_key=NVIDIA_API_KEY)
    user_prompt = f"Sirket: {company}\n\nSayfa metni:\n\"\"\"\n{page_text[:15000]}\n\"\"\""
    response = client.chat.completions.create(
        model=NIM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("listings", [])

def scrape() -> list[dict]:
    if not NVIDIA_API_KEY:
        print("[nim_fallback] NVIDIA_API_KEY tanimli degil, atlaniyor.")
        return []

    all_offers = []
    for target in TARGETS:
        name = target["name"]
        try:
            text = _fetch_rendered_text(target["url"])
            listings = _extract_listings(text, name)
            for item in listings:
                title = item.get("title", "")
                if not title:
                    continue
                all_offers.append({
                    "title": title,
                    "company": name,
                    "location": item.get("location", "") or "",
                    "country": "",
                    "url": item.get("url") or target["url"],
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
