"""
Anahtar kelime filtresinden gecen yeni ilanlari ikinci kez, yapay zeka ile eler.
Ayni ucretsiz NVIDIA NIM modelini kullanir; ilanlar toplu (BATCH_SIZE'lik gruplar halinde) gonderilir.

Model cagrisi basarisiz olursa o gruptaki ilanlarin hepsi tutulur — hata yuzunden ilan kaybetmeyiz.
NVIDIA_API_KEY yoksa filtre devre disidir (her ilan tutulur).
"""
from openai import OpenAI

from lib.config import NVIDIA_API_KEY
from scrapers.company_nim_fallback import NIM_BASE_URL, NIM_MODEL, _parse_json

BATCH_SIZE = 25

SYSTEM_PROMPT = """Bir endustri muhendisligi universite ogrencisi Avrupa'da staj ariyor. Sana numarali ilan basliklari verilecek.
Su ilanlari TUT: universite ogrencisine yonelik staj, Praktikum, Werkstudent/working student, bitirme tezi (Abschlussarbeit/thesis) veya trainee pozisyonlari; alanlari operasyon, tedarik zinciri, lojistik, uretim planlama/yonetimi, satin alma, kalite, lean, surec optimizasyonu, endustri muhendisligi veya bunlara yakin muhendislik/analitik isler.
Su ilanlari ELE: okul ogrencisi stajlari, mesleki egitim (Ausbildung), vasifsiz/depo/uretim isciligi, tatil veya ek is, gonullu hizmet, deneyimli/kidemli/yonetici pozisyonlari, ve alan disi isler (IK, pazarlama, finans, hukuk, IT destek, medya, saglik vb.).
SADECE su JSON ile cevap ver: {"keep": [tutulacak ilanlarin numaralari]}"""


def _ask(client: OpenAI, batch: list[dict]) -> set[int]:
    lines = "\n".join(
        f"{i}. {o.get('title', '')} | {o.get('company', '')} | {o.get('location', '')}" for i, o in enumerate(batch)
    )
    response = client.chat.completions.create(
        model=NIM_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": lines}],
        temperature=0.0,
        max_tokens=1024,
        response_format={"type": "json_object"},
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    keep = _parse_json(response.choices[0].message.content or "").get("keep", [])
    return {int(i) for i in keep if str(i).isdigit()}


def filter_offers(offers: list[dict]) -> list[dict]:
    if not NVIDIA_API_KEY or not offers:
        return offers

    client = OpenAI(base_url=NIM_BASE_URL, api_key=NVIDIA_API_KEY)
    kept = []
    for start in range(0, len(offers), BATCH_SIZE):
        batch = offers[start:start + BATCH_SIZE]
        try:
            keep_ids = _ask(client, batch)
        except Exception as e:
            print(f"[ai_filter] grup filtrelenemedi, hepsi tutuluyor: {e}")
            kept.extend(batch)
            continue
        for i, offer in enumerate(batch):
            if i in keep_ids:
                kept.append(offer)
            else:
                print(f"  [AI-ELENDI] {offer.get('title')} — {offer.get('company')}")
    return kept
