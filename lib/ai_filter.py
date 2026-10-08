"""
Anahtar kelime filtresinden gecen yeni ilanlari ikinci kez, yapay zeka ile eler.
Ayni ucretsiz NVIDIA NIM modelini kullanir; ilanlar toplu (BATCH_SIZE'lik gruplar halinde) gonderilir.

Model her ilan icin numarasini, basligini ve kararini geri yazar. Geri yazilan baslik o numaradaki ilanin
basligiyla uyusmazsa (model numaralari kaydirmissa) karar yok sayilir ve ilan tutulur.
Model cagrisi basarisiz olursa o gruptaki ilanlarin hepsi tutulur — hata yuzunden ilan kaybetmeyiz.
NVIDIA_API_KEY yoksa filtre devre disidir (her ilan tutulur).
"""
import re

from openai import OpenAI

from lib.config import NVIDIA_API_KEY
from scrapers.company_nim_fallback import NIM_BASE_URL, NIM_MODEL, _parse_json

BATCH_SIZE = 10

SYSTEM_PROMPT = """Turkiye'de okuyan bir endustri muhendisligi universite ogrencisi Erasmus+ ile Avrupa'da tam zamanli staj ariyor. Sana ilanlar verilecek; her satir
"[N] baslik | sirket | konum" bicimindedir. Her ilan icin ogrenciye uygun olup olmadigina karar ver.
UYGUN (relevant=true): universite ogrencisine yonelik staj, Praktikum veya Pflichtpraktikum pozisyonlari; alanlari satin alma (Einkauf, purchasing, procurement, sourcing),
kalite (Qualitaet, quality management/assurance/engineering, supplier quality), operasyon, tedarik zinciri (supply
chain), lojistik, uretim planlama/yonetimi, lean, surec optimizasyonu, proje yonetimi, endustri muhendisligi veya yakin
muhendislik/analitik isler.
UYGUN DEGIL (relevant=false): sadece Werkstudent / working student / duales Studium olan pozisyonlar (Almanya'da kayitli
ogrenci gerektiren yari zamanli isler), trainee / graduate programlari (mezunlar icin is), bitirme tezi
(Abschlussarbeit / Master's thesis) ilanlari — baslikta Praktikum / internship secenegi de varsa UYGUN —, okul ogrencisi stajlari, mesleki
egitim (Ausbildung), vasifsiz/depo/uretim isciligi, tatil
veya ek is, gonullu hizmet, deneyimli/kidemli/yonetici pozisyonlari, eczacilik/kimya/biyoloji/mikrobiyoloji laboratuvar
isleri (ornek: GMP kalite kontrol laboratuvari, Pharmaziepraktikum), Avrupa disindaki konumlar ve alan disi isler (IK,
pazarlama, finans, hukuk, IT destek, medya, saglik vb.).
Supheliysen relevant=true yaz.
SADECE su JSON ile cevap ver, her ilan icin bir satir, basligi aynen kopyala:
{"results": [{"id": N, "title": "ilan basligi", "relevant": true}]}"""


def _norm(s: str) -> str:
    return re.sub(r"\W+", "", (s or "").lower())[:30]


def _ask(client: OpenAI, batch: list[dict]) -> set[int]:
    """Elenecek ilanlarin (0 tabanli) sira numaralarini dondurur. Basligi uyusmayan kararlar yok sayilir."""
    lines = "\n".join(
        f"[{i + 1}] {o.get('title', '')} | {o.get('company', '')} | {o.get('location', '')}" for i, o in enumerate(batch)
    )
    response = client.chat.completions.create(
        model=NIM_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": lines}],
        temperature=0.0,
        max_tokens=2048,
        response_format={"type": "json_object"},
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    results = _parse_json(response.choices[0].message.content or "").get("results", [])
    drop, mismatched = set(), 0
    for r in results:
        if not isinstance(r, dict) or r.get("relevant") is not False or not str(r.get("id", "")).isdigit():
            continue
        i = int(r["id"]) - 1
        if 0 <= i < len(batch) and _norm(r.get("title")) == _norm(batch[i].get("title")):
            drop.add(i)
        else:
            mismatched += 1
    if mismatched:
        print(f"[ai_filter] {mismatched} karar baslikla uyusmadi, o ilanlar tutuldu")
    return drop


def filter_offers(offers: list[dict]) -> list[dict]:
    if not NVIDIA_API_KEY or not offers:
        return offers

    client = OpenAI(base_url=NIM_BASE_URL, api_key=NVIDIA_API_KEY)
    kept = []
    for start in range(0, len(offers), BATCH_SIZE):
        batch = offers[start:start + BATCH_SIZE]
        try:
            drop_ids = _ask(client, batch)
        except Exception as e:
            print(f"[ai_filter] grup filtrelenemedi, hepsi tutuluyor: {e}")
            kept.extend(batch)
            continue
        for i, offer in enumerate(batch):
            if i not in drop_ids:
                kept.append(offer)
            else:
                print(f"  [AI-ELENDI] {offer.get('title')} — {offer.get('company')} — {offer.get('location')}")
    return kept
