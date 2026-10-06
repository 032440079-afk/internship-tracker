"""
Her yeni ilan icin ana CV'den ilana uyarlanmis bir CV ve on yazi (cover letter) uretir, PDF'e cevirir.

Repo herkese acik oldugu icin:
  - Ana CV repoda sifreli durur (cv/master_cv.docx.enc); workflow CV_KEY secret'i ile /tmp'ye acar.
  - CV icerigi ve uretilen metinler ASLA print edilmez (Actions loglari da herkese acik).

Uydurma korumasi: model sadece ozet, madde (bullet) ve beceri satirlarini degistirebilir. Basliklar, isimler,
tarihler, iletisim bilgileri hic modele birakilmaz. Degistirilen metinde ana CV'de gecmeyen bir ozel isim,
kisaltma veya sayi varsa o degisiklik reddedilir ve orijinal metin kalir. Beceri satirlarinda sadece siralama
degisebilir.
"""
import json
import os
import re
import subprocess
import tempfile
from datetime import date

from docx import Document
from docx.shared import Pt, Inches
from openai import OpenAI

from lib.config import NVIDIA_API_KEY
from scrapers.company_nim_fallback import NIM_BASE_URL, NIM_MODEL, _parse_json

MASTER_CV_PATH = os.environ.get("MASTER_CV_PATH", "/tmp/master_cv.docx")
MAX_LENGTH_GROWTH = 1.3  # tek sayfaya sigsin diye: yeni metin orijinalin en fazla %30 uzun olabilir

SYSTEM_PROMPT = """You tailor a student's CV and write a cover letter for a specific internship posting.
Rules — follow them strictly:
- NEVER invent experience, employers, tools, technologies, certificates, numbers or results that are not in the CV.
- You may only rephrase and reorder what the CV already says, emphasising what matters for this posting and using
  the posting's wording where it truthfully describes the same thing.
- Keep each rewritten text about the same length as the original (one-page CV).
- "skills": reorder the comma-separated items of each line so the most relevant come first. Do not add or remove items.
- Cover letter: English, 3 short paragraphs (why this role/company, relevant evidence from the CV, closing), no
  greeting and no signature (they are added separately), max ~230 words in total.
Reply ONLY with JSON:
{"summary": "...", "bullets": {"<id>": "..."}, "skills": {"<id>": "item, item, ..."}, "cover_letter": ["...", "...", "..."]}
Only include bullet ids you actually changed."""


# ---------- ana CV'yi okuma ----------

def _is_heading(p) -> bool:
    t = p.text.strip()
    return bool(t) and t.isupper() and len(p.runs) == 1 and bool(p.runs[0].bold)


def _is_bullet(p) -> bool:
    ppr = p._p.pPr
    return ppr is not None and ppr.numPr is not None


def _sections(doc: Document):
    """(bolum_basligi, paragraf_indeksi, paragraf) uclusu dondurur."""
    section = ""
    for i, p in enumerate(doc.paragraphs):
        if _is_heading(p):
            section = p.text.strip()
            continue
        yield section, i, p


def _editable_parts(doc: Document) -> dict:
    parts = {"summary": None, "bullets": {}, "skills": {}}
    for section, i, p in _sections(doc):
        if section == "PROFESSIONAL SUMMARY" and p.text.strip() and parts["summary"] is None:
            parts["summary"] = (i, p.text)
        elif _is_bullet(p) and section != "CERTIFICATIONS" and len(p.runs) == 1:
            parts["bullets"][str(i)] = p.text
        elif section == "TECHNICAL SKILLS" and len(p.runs) >= 2 and p.runs[0].text.strip().endswith(":") \
                and not p.runs[0].text.lower().startswith("language"):
            parts["skills"][str(i)] = p.runs[1].text.strip()
    return parts


def available() -> bool:
    return bool(NVIDIA_API_KEY) and os.path.exists(MASTER_CV_PATH)


# ---------- uydurma korumasi ----------

_TOKEN = re.compile(r"[A-Za-z0-9][\w+#&/.-]*")


def _suspicious_tokens(text: str, corpus_lower: str) -> list[str]:
    """Cumle basi disinda buyuk harfle baslayan, kisaltma veya rakam iceren ve corpus'ta gecmeyen kelimeler."""
    bad = []
    for sentence in re.split(r"(?<=[.;:!?])\s+", text):
        for k, tok in enumerate(_TOKEN.findall(sentence)):
            tok = tok.rstrip(".,")
            special = any(c.isdigit() for c in tok) or (k > 0 and tok[:1].isupper()) or \
                (len(tok) > 1 and tok.isupper())
            if special and tok.lower() not in corpus_lower:
                bad.append(tok)
    return bad


def _accept(new: str, old: str, corpus_lower: str) -> bool:
    if not new or len(new) > len(old) * MAX_LENGTH_GROWTH + 20:
        return False
    return not _suspicious_tokens(new, corpus_lower)


# ---------- model ----------

def _ask_model(parts: dict, offer: dict, job_text: str) -> dict:
    client = OpenAI(base_url=NIM_BASE_URL, api_key=NVIDIA_API_KEY)
    payload = {
        "summary": parts["summary"][1] if parts["summary"] else "",
        "bullets": parts["bullets"],
        "skills": parts["skills"],
    }
    user = (f"POSTING: {offer.get('title')} at {offer.get('company')} ({offer.get('location')})\n"
            f"POSTING TEXT:\n{job_text[:6000]}\n\nEDITABLE CV PARTS (JSON):\n{json.dumps(payload, ensure_ascii=False)}")
    for attempt in range(2):
        response = client.chat.completions.create(
            model=NIM_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=3000,
            response_format={"type": "json_object"},
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        try:
            return _parse_json(response.choices[0].message.content or "")
        except ValueError:
            if attempt == 1:
                raise


# ---------- belge uretimi ----------

def _set_text(p, text: str, run_index: int = 0):
    p.runs[run_index].text = text


def _build_cv(doc: Document, parts: dict, answer: dict, corpus_lower: str) -> int:
    changed = 0
    if parts["summary"] and isinstance(answer.get("summary"), str):
        i, old = parts["summary"]
        if _accept(answer["summary"].strip(), old, corpus_lower):
            _set_text(doc.paragraphs[i], answer["summary"].strip())
            changed += 1
    for pid, new in (answer.get("bullets") or {}).items():
        old = parts["bullets"].get(str(pid))
        if old and isinstance(new, str) and _accept(new.strip(), old, corpus_lower):
            _set_text(doc.paragraphs[int(pid)], new.strip())
            changed += 1
    for pid, new in (answer.get("skills") or {}).items():
        old = parts["skills"].get(str(pid))
        if not old or not isinstance(new, str):
            continue
        old_items = [s.strip() for s in old.split(",")]
        new_items = [s.strip() for s in new.split(",")]
        if sorted(old_items) == sorted(new_items):  # sadece siralama degisebilir
            run = doc.paragraphs[int(pid)].runs[1]
            leading = run.text[:len(run.text) - len(run.text.lstrip())]
            run.text = leading + ", ".join(new_items)
            changed += 1
    return changed


def _build_cover_letter(master: Document, paragraphs: list[str], offer: dict, path: str):
    name = master.paragraphs[0].text.strip().title()
    contact = master.paragraphs[2].text.strip()
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(1)
        s.top_margin = s.bottom_margin = Inches(0.9)
    style = doc.styles["Normal"]
    style.font.size = Pt(11)

    head = doc.add_paragraph()
    r = head.add_run(name)
    r.bold = True
    r.font.size = Pt(14)
    doc.add_paragraph(contact)
    doc.add_paragraph(date.today().strftime("%d %B %Y"))
    doc.add_paragraph(f"Re: {offer.get('title', 'Internship')} — {offer.get('company', '')}")
    doc.add_paragraph(f"Dear Hiring Team at {offer.get('company') or 'your company'},")
    for text in paragraphs:
        doc.add_paragraph(text.strip())
    doc.add_paragraph("Kind regards,")
    doc.add_paragraph(name)
    doc.save(path)


def _to_pdf(docx_path: str, outdir: str) -> str:
    env = dict(os.environ, HOME=tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--norestore", "--convert-to", "pdf", "--outdir", outdir, docx_path],
                   check=True, capture_output=True, timeout=180, env=env)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    if not os.path.exists(pdf):
        raise RuntimeError("PDF olusturulamadi")
    return pdf


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s or "").strip("_")[:40] or "Company"


def build_application(offer: dict, job_text: str) -> dict:
    """{"cv": pdf_yolu, "cover_letter": pdf_yolu (yoksa None), "changes": int} dondurur."""
    master = Document(MASTER_CV_PATH)
    parts = _editable_parts(master)
    cv_text = "\n".join(p.text for p in master.paragraphs)
    answer = _ask_model(parts, offer, job_text)

    outdir = tempfile.mkdtemp(prefix="application_")
    company = _slug(offer.get("company"))

    doc = Document(MASTER_CV_PATH)
    changes = _build_cv(doc, parts, answer, cv_text.lower())
    cv_docx = os.path.join(outdir, f"Kaan_Dogru_CV_{company}.docx")
    doc.save(cv_docx)
    result = {"cv": _to_pdf(cv_docx, outdir), "cover_letter": None, "changes": changes}

    letter = [p for p in (answer.get("cover_letter") or []) if isinstance(p, str) and p.strip()]
    letter_corpus = f"{cv_text}\n{offer.get('title', '')}\n{offer.get('company', '')}\n{job_text}".lower()
    if letter and not any(_suspicious_tokens(p, letter_corpus) for p in letter):
        cl_docx = os.path.join(outdir, f"Kaan_Dogru_Cover_Letter_{company}.docx")
        _build_cover_letter(master, letter, offer, cl_docx)
        result["cover_letter"] = _to_pdf(cl_docx, outdir)
    return result
