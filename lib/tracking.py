"""
Basvuru takibi. Kaan ve kiz arkadasi ayni ilanlari gorur ama durumlari (Basvurdum / Gorusme / Red / Kabul /
Ilgilenmiyorum) kisiye ozeldir: Firestore'da trackers/{email}/applications/{ilan_id} altinda tutulur.

Iki yerden isaretlenebilir:
  - Web paneli (Google ile giris; sadece ALLOWED_EMAILS'taki hesaplar) dogrudan Firestore'a yazar.
  - Telegram: ilan bildirimlerinin altindaki butonlar. Sunucumuz olmadigi icin buton basmalari saatlik bir GitHub
    Actions isiyle (track.py) ve gunluk taramanin basinda toplanir. Telegram bekleyen haberleri 24 saat saklar.
    Her Telegram sohbeti bir kez "/bagla e-posta" ile kendi hesabina baglanir.

Durumlar sadece Firestore'da ve Telegram'da durur; herkese acik site koduna / repoya yazilmaz.

Telegram komutlari:
  /bagla <e-posta>          -> bu sohbeti hesaba bagla (e-posta ALLOWED_EMAILS'ta olmali)
  /ozet                     -> basvuru istatistikleri
  <ilan linki> basvurdum    -> butonu olmayan eski bildirimler icin durum (gorusme / red / kabul / ilgilenmiyorum)
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

ALLOWED_EMAILS = config.ALLOWED_EMAILS  # siteye girebilecek hesaplar; sira CV profilleriyle ayni (ilki Kaan)

# Serbest metinde durum kelimeleri (Turkce karakterli / karaktersiz)
_TEXT_STATUS = [
    (r"ba[sş]vurdum|applied", "applied"),
    (r"g[oö]r[uü][sş]me|m[uü]lakat|interview", "interview"),
    (r"\bred\b|\bret\b|reddedil|rejected", "rejected"),
    (r"kabul|\boffer\b", "offer"),
    (r"ilgilenmiyorum|\bskip\b", "skip"),
]

HELP = ("ℹ️ <b>Başvuru takibi</b>\n"
        "• İlk kez: <code>/bagla senin@gmail.com</code> yaz (siteye girdiğin Google hesabı).\n"
        "• Her ilan bildiriminin altındaki butonlara bas (en geç ~1 saat içinde kaydedilir, buton ✅ olur).\n"
        "• Butonu olmayan eski ilanlar için: ilan linkini yapıştırıp yanına <i>başvurdum / görüşme / red / kabul</i> yaz.\n"
        "• /ozet → başvuru istatistiklerin\n"
        "• Sınıf şartıyla yanlışlıkla elenen bir ilan için: <code>/geri ilan-linki</code>\n"
        "• Aynı durumları web sitesinde de görüp değiştirebilirsin.")


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

def stats(email: str) -> dict:
    apps = [a for a in store.applications(email) if a.get("status") in APPLIED_STATUSES]
    now = datetime.now(timezone.utc)
    counts = {s: 0 for s in APPLIED_STATUSES}
    pending = []
    for a in apps:
        counts[a["status"]] += 1
        if a["status"] == "applied" and a.get("updatedAt"):
            pending.append((a, (now - a["updatedAt"]).days))
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
        for a, days in s["oldest_pending"]:
            lines.append(f"• {html.escape(a.get('title', ''))} — {html.escape(a.get('company', ''))} ({days} gün)")
    return "\n".join(lines)


# ---------- Telegram guncellemelerini isleme ----------

NOT_LINKED = "🔗 Bu sohbet henüz bir hesaba bağlı değil. Önce <code>/bagla senin@gmail.com</code> yaz."


async def _handle_callback(bot: Bot, cq, links: dict) -> bool:
    try:
        _, doc_id, status = cq.data.split(":", 2)
    except (AttributeError, ValueError):
        return False
    email = links.get(str(cq.message.chat.id))
    if not email:
        await bot.send_message(chat_id=cq.message.chat.id, text=NOT_LINKED, parse_mode=ParseMode.HTML)
        return False
    if status not in STATUSES or store.set_application_status(email, doc_id, status) is None:
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


async def _handle_message(bot: Bot, msg, links: dict) -> bool:
    text = (msg.text or "").strip()
    command = text.lower().lstrip("/")
    chat_id = str(msg.chat.id)
    email = links.get(chat_id)
    reply, changed = None, False
    if command.startswith(("bagla", "bağla")):
        given = (text.split(maxsplit=1)[1:] or [""])[0].strip().lower()
        if given in ALLOWED_EMAILS:
            store.link_telegram(chat_id, given)
            links[chat_id] = given
            reply = f"✅ Bu sohbet <b>{html.escape(given)}</b> hesabına bağlandı. Butonlar artık senin listene yazacak."
        else:
            reply = "⚠️ Bu e-posta izinli hesaplar arasında yok. Siteye girdiğin Google hesabını yaz: /bagla adres@gmail.com"
    elif command.startswith("geri"):
        url, _ = _parse_text_status(text)
        offer = store.restore_offer(store.url_hash(url)) if url else None
        if offer is not None:
            doc_id = store.url_hash(url)
            await bot.send_message(
                chat_id=msg.chat.id, parse_mode=ParseMode.HTML, disable_web_page_preview=True,
                text=(f"↩️ Geri alındı: <b>{html.escape(offer.get('title', ''))}</b> — {html.escape(offer.get('company', ''))}\n"
                      "Panoda görünecek; CV ve ön yazısı bir sonraki günlük çalıştırmada gelecek."),
                reply_markup=keyboard(doc_id))
            return True
        reply = "⚠️ Link bulunamadı. Elenenler mesajındaki ilan linkini kopyalayıp <code>/geri link</code> yaz."
    elif command.startswith(("ozet", "özet")):
        reply = format_stats(stats(email)) if email else NOT_LINKED
    elif command.startswith(("yardim", "yardım", "start", "help")):
        reply = HELP
    else:
        url, status = _parse_text_status(text)
        if url and status:
            if not email:
                reply = NOT_LINKED
            else:
                offer = store.set_application_status(email, store.url_hash(url), status)
                if offer is not None:
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
    links = store.telegram_links()
    changed = 0
    async with Bot(token=config.TELEGRAM_BOT_TOKEN) as bot:
        updates = await bot.get_updates(timeout=0, allowed_updates=["callback_query", "message"])
        for u in updates:
            try:
                if u.callback_query and str(u.callback_query.message.chat.id) in allowed:
                    changed += await _handle_callback(bot, u.callback_query, links)
                elif u.message and str(u.message.chat.id) in allowed:
                    changed += await _handle_message(bot, u.message, links)
            except Exception as e:
                print(f"[tracking] guncelleme islenemedi: {type(e).__name__}")
        if updates:  # islenenleri Telegram'a onayla ki bir daha gelmesin
            await bot.get_updates(offset=updates[-1].update_id + 1, timeout=0)
    print(f"[tracking] {len(updates)} guncelleme, {changed} durum degisikligi")
    return changed


async def send_weekly_summaries():
    """Her bagli Telegram sohbetine kendi hesabinin ozetini gonderir."""
    if not config.TELEGRAM_BOT_TOKEN:
        return
    async with Bot(token=config.TELEGRAM_BOT_TOKEN) as bot:
        for chat_id, email in store.telegram_links().items():
            try:
                await bot.send_message(chat_id=chat_id, text="🗓 Haftalık özet\n" + format_stats(stats(email)),
                                       parse_mode=ParseMode.HTML)
            except Exception as e:
                print(f"[tracking] haftalik ozet gonderilemedi: {type(e).__name__}")


def sync_allowed():
    """ALLOWED_EMAILS secret'ini Firestore'daki erisim listesine yazar (site girisi icin)."""
    if ALLOWED_EMAILS:
        store.sync_allowed(ALLOWED_EMAILS)
