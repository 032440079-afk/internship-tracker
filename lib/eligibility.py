"""
Ilan metnine bakip Kaan'in sinif / donem sartini karsilayip karsilamadigina karar verir.
Sadece 4. sinif / son sinif / master / mezun sarti olan ilanlar elenir; 3. sinif ve alti, sart yazmayan ve
emin olunamayan ilanlar tutulur. Model cagrisi basarisiz olursa veya ilan metni okunamadiysa ilan tutulur.
Model eleme kararinin dayanagi olan cumleyi ilandan aynen kopyalamak zorunda; bu cumle ilan metninde yoksa
(model uydurduysa) ilan tutulur.
"""
import re

from openai import OpenAI

from lib.config import NVIDIA_API_KEY
from scrapers.company_nim_fallback import NIM_BASE_URL, NIM_MODEL, _parse_json

SYSTEM_PROMPT = """Bir staj ilaninin metnini okuyup ogrencinin sinif/donem sartini karsilayip karsilamadigina karar ver.
Ogrenci: Turkiye'de 4 yillik (8 donemlik) endustri muhendisligi lisans programinda okuyor. Su an 2. sinif; 2027 yazinda
2. sinifi bitirmis, 3. sinifa gecmis olacak. Mezuniyeti 2029 yazinda.
eligible=false SADECE ilan acikca sunlardan birini istiyorsa: sadece master ogrencileri, tamamlanmis lisans derecesi /
mezun, son sinif (final year, letztes Studienjahr), 4. sinif, en az 7. donem (ab dem 7. Semester veya ustu).
eligible=true: 3. sinif, "ab dem 4./5./6. Semester", "fortgeschrittenes Studium", "Hauptstudium", "Bachelor oder
Master" gibi lisans ogrencisine de acik sartlar; sart yazmayan ilanlar; emin olmadigin her durum.
eligible=false dersen "evidence" alanina bu sarti iceren cumleyi ilandan AYNEN kopyala (en fazla 30 kelime).
SADECE su JSON ile cevap ver:
{"eligible": true, "reason": "ilandaki sarti en fazla 8 kelimeyle ozetle", "evidence": "ilandan aynen alinti veya bos"}"""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _evidence_in_text(evidence: str, job_text: str) -> bool:
    """Alintinin ilk 60 karakteri ilan metninde geciyor mu (bosluk ve buyuk/kucuk harf farki yok sayilir)."""
    ev = _norm(evidence).strip(' "\'.…')[:60]
    return len(ev) >= 15 and ev in _norm(job_text)


def check(offer: dict, job_text: str) -> tuple[bool, str, str]:
    """(uygun_mu, kisa_gerekce, ilandan_alinti) dondurur."""
    if not NVIDIA_API_KEY or not job_text.strip():
        return True, "", ""
    try:
        client = OpenAI(base_url=NIM_BASE_URL, api_key=NVIDIA_API_KEY)
        response = client.chat.completions.create(
            model=NIM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"ILAN: {offer.get('title', '')} — {offer.get('company', '')}\n\n{job_text[:6000]}"},
            ],
            temperature=0.0,
            max_tokens=400,
            response_format={"type": "json_object"},
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        answer = _parse_json(response.choices[0].message.content or "")
    except Exception as e:
        print(f"    [uygunluk] kontrol edilemedi, ilan tutuldu: {type(e).__name__}")
        return True, "", ""
    reason = str(answer.get("reason") or "")[:80]
    evidence = str(answer.get("evidence") or "")[:300]
    if answer.get("eligible") is not False:
        return True, reason, ""
    if not _evidence_in_text(evidence, job_text):
        print(f"    [uygunluk] eleme gerekcesi ilanda bulunamadi, ilan tutuldu: {offer.get('title')}")
        return True, reason, ""
    return False, reason, evidence
