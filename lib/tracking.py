"""
Basvuru takibi: Kaan her ilan bildiriminin altindaki butonlarla (Basvurdum / Gorusme / Red / Kabul / Ilgilenmiyorum)
ilanin durumunu isaretler; durumlar Firestore'daki ilan kaydina yazilir.

Telegram butona basildiginda haberi bot'a birakir; sunucumuz olmadigi icin bu haberler saatlik bir GitHub Actions
isiyle (track.py) ve gunluk taramanin basinda toplanir. Telegram bekleyen haberleri 24 saat saklar.

Durumlar sadece Firestore'da ve Telegram'da durur; herkese acik dashboard'a / repoya yazilmaz.

Telegram'dan yazilabilecek komutlar:
  /ozet                     -> basvuru istatistikleri
  <ilan linki> basvurdum    -> butonu olmayan eski bildirimler icin durum isaretleme (gorusme / red / kabul da olur)
  /yardim                   -> kullanim
"""
import html
import re
from datetime import datetime, timezone

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from lib import config, store

STATUSES = {
    "applied": "📨 Başvurdum",
    "interview": "🗣 Görüşme",
    "rejected": "❌ Red",
    "offer": "🎉 Kabul",
    "skip": "🙈 İlgilenmiyorum",
}
APPLIED_STATUSES = ("applied", "interview", "rejected", "offer")  # hepsi "basvuru yapildi" sayilir

# Serbest metinde durum kelimeleri (Turkce karakterli / karaktersiz)
_TEXT_STATUS = [
    (r"ba[sş]vurdum|applied", "applied"),
    (r"g[oö]r[uü][sş]me|m[uü]lakat|interview", "interview"),
    (r"\bred\b|\bret\b|reddedil|rejected", "rejected"),
    (r"kabul|\boffer\b", "offer"),
    (r"ilgilenmiyorum|\bskip\b", "skip"),
]

HELP = ("ℹ️ <b>Başvuru takibi</b>\n"
        "• Her ilan bildiriminin altındaki butonlara bas (en geç ~1 saat içinde kaydedilir, buton ✅ olur).\n"
        "• Butonu olmayan eski ilanlar için: ilan linkini yapıştırıp yanına <i>başvurdum / görüşme / red / kabul</i> yaz.\n"
        "• /ozet → başvuru istatistiklerin")


def keyboard(doc_id: str, current: str | None = None) -> InlineKeyboardMarkup:
    def btn(status):
        label = STATUSES[status]
        return InlineKeyboardButton(("✅ " if status == current else "") + label, callback_data=f"st:{doc_id}:{status}")
    return InlineKeyboardMarkup([
        [btn("applied"), btn("skip")],
        [btn("interview"), btn("rejected"), btn("offer")],
    ])


def _allowed_chats() -> set[str]:
    return {str(c) for c in list(config.TELEGRAM_CHAT_IDS) + list(config.TELEGRAM_CV_CHAT_IDS)}


def _parse_text_status(text: str) -> tuple[str | None, str | None]:
    """'<link> basvurdum' -> (url, status)"""
    url = re.search(r"https?://\S+", text or "")
    lowered = (text or "").lower()
    status = next((s for pattern, s in _TEXT_STATUS if re.search(pattern, lowered)), None)
    return (url.group(0).rstrip(").,>") if url else None), status


# ---------- istatistik ----------

def stats() -> dict:
    offers = store.offers_with_status(list(APPLIED_STATUSES))
    now = datetime.now(timezone.utc)
    counts = {s: 0 for s in APPLIED_STATUSES}
    pending = []
    for o in offers:
        counts[o["status"]] += 1
        if o["status"] == "applied" and o.get("statusUpdatedAt"):
            pending.append((o, (now - o["statusUpdatedAt"]).days))
    total = sum(counts.values())
    answered = counts["interview"] + counts["rejected"] + counts["offer"]
    return {
        "total": total, **counts,
        "response_rate": round(100 * answered / total) if total else None,
        "interview_rate": round(100 * (counts["interview"] + counts["offer"]) / total) if total else None,
        "oldest_pending": sorted(pending, key=lambda p: -p[1])[:5],
    }


def format_stats(s: dict) -> str:
    if not s["total"]:
        return "📊 Henüz başvuru işaretlenmemiş. İlan bildirimlerinin altındaki <b>📨 Başvurdum</b> butonunu kullan."
    lines = [
        "📊 <b>Başvuru takibi</b>",
        f"Başvurulan: <b>{s['total']}</b> (cevap bekleyen: {s['applied']})",
        f"🗣 Görüşme: {s['interview']} · 🎉 Kabul: {s['offer']} · ❌ Red: {s['rejected']}",
        f"Dönüş oranı: <b>%{s['response_rate']}</b> (cevap gelen / başvurulan)",
        f"Görüşmeye çağrılma oranı: <b>%{s['interview_rate']}</b>",
    ]
    if s["total"] < 10:
        lines.append("<i>Henüz az veri var; oranlar ~10+ başvurudan sonra anlamlı olur.</i>")
    if s["oldest_pending"]:
        lines.append("\n⏳ En uzun süredir cevap beklenenler:")
        for o, days in s["oldest_pending"]:
            lines.append(f"• {html.escape(o.get('title', ''))} — {html.escape(o.get('company', ''))} ({days} gün)")
    return "\n".join(lines)


# ---------- Telegram guncellemelerini isleme ----------

async def _handle_callback(bot: Bot, cq) -> bool:
    try:
        _, doc_id, status = cq.data.split(":", 2)
    except (AttributeError, ValueError):
        return False
    if status not in STATUSES or not store.update_status(doc_id, status):
        return False
    try:
        await bot.answer_callback_query(cq.id, text=f"Kaydedildi: {STATUSES[status]}")
    except Exception:
        pass  # saatlik is gec isledigi icin sorgu zaman asimina ugramis olabilir; onemli degil
    try:
        await bot.edit_message_reply_markup(chat_id=cq.message.chat.id, message_id=cq.message.message_id,
                                            reply_markup=keyboard(doc_id, status))
    except Exception:
        pass
    return True


async def _handle_message(bot: Bot, msg) -> bool:
    text = (msg.text or "").strip()
    reply = None
    changed = False
    if text.lower().lstrip("/").startswith(("ozet", "özet")):
        reply = format_stats(stats())
    elif text.lower().lstrip("/").startswith(("yardim", "yardım", "start", "help")):
        reply = HELP
    else:
        url, status = _parse_text_status(text)
        if url and status:
            doc_id = store.url_hash(url)
            if store.update_status(doc_id, status):
                offer = store.get_offer(doc_id) or {}
                reply = (f"✅ Kaydedildi: {STATUSES[status]} — {html.escape(offer.get('title', ''))}"
                         f" ({html.escape(offer.get('company', ''))})")
                changed = True
            else:
                reply = "⚠️ Bu link kayıtlı ilanlar arasında yok. Bildirimdeki 'İlana git' linkini aynen yapıştır."
    if reply:
        await bot.send_message(chat_id=msg.chat.id, text=reply, parse_mode=ParseMode.HTML,
                               disable_web_page_preview=True)
    return changed


async def process_updates() -> int:
    """Bekleyen buton basmalarini ve komutlari isler; degisen ilan sayisini dondurur."""
    if not config.TELEGRAM_BOT_TOKEN:
        return 0
    allowed = _allowed_chats()
    changed = 0
    async with Bot(token=config.TELEGRAM_BOT_TOKEN) as bot:
        updates = await bot.get_updates(timeout=0, allowed_updates=["callback_query", "message"])
        for u in updates:
            try:
                if u.callback_query and str(u.callback_query.message.chat.id) in allowed:
                    changed += await _handle_callback(bot, u.callback_query)
                elif u.message and str(u.message.chat.id) in allowed:
                    changed += await _handle_message(bot, u.message)
            except Exception as e:
                print(f"[tracking] guncelleme islenemedi: {type(e).__name__}")
        if updates:  # islenenleri Telegram'a onayla ki bir daha gelmesin
            await bot.get_updates(offset=updates[-1].update_id + 1, timeout=0)
    print(f"[tracking] {len(updates)} guncelleme, {changed} durum degisikligi")
    return changed
