"""
Yeni ilan bulunduğunda Telegram üzerinden bildirim gönderir.
Birden fazla chat_id'ye (sen + kız arkadaşın) aynı anda mesaj atar.
"""
import asyncio
import html
from concurrent.futures import ThreadPoolExecutor
from telegram import Bot
from telegram.constants import ParseMode

from lib import config


def _format_message(offer: dict) -> str:
    return (
        f"🎯 <b>Yeni staj ilanı</b>\n\n"
        f"<b>{offer.get('title', 'Başlıksız')}</b>\n"
        f"🏢 {offer.get('company', '-')}\n"
        f"📍 {offer.get('location', '-')}\n"
        f"🔗 <a href=\"{offer['url']}\">İlana git</a>\n"
        f"📡 Kaynak: {offer.get('source', '-')}"
    )


async def _send_all(text: str, reply_markup=None):
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_IDS:
        print("[notify] TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_IDS ayarlanmamış, bildirim atlanıyor.")
        return
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    for chat_id in config.TELEGRAM_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
                reply_markup=reply_markup,
            )
        except Exception as e:
            print(f"[notify] chat_id={chat_id} için mesaj gönderilemedi: {e}")


async def _send_documents(paths: list[str], caption: str):
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_IDS:
        return
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    for chat_id in config.TELEGRAM_CV_CHAT_IDS:
        for path in paths:
            try:
                with open(path, "rb") as f:
                    await bot.send_document(chat_id=chat_id, document=f, caption=caption)
            except Exception as e:
                print(f"[notify] chat_id={chat_id} için dosya gönderilemedi: {e}")


def _run(coro):
    """Coroutine'i ayri bir thread'de calistirir: Playwright sync API acikken ana thread'de bir event loop calisir
    ve orada asyncio.run() hata verir."""
    with ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result()


def notify_new_offer(offer: dict):
    from lib import store, tracking  # basvuru takibi butonlari (Basvurdum / Gorusme / Red / Kabul)
    text = _format_message(offer)
    _run(_send_all(text, reply_markup=tracking.keyboard(store.url_hash(offer["url"]))))


def send_text(text: str):
    _run(_send_all(text))


def send_application_files(offer: dict, paths: list[str], match: dict | None = None):
    caption = f"📎 {offer.get('company', '')} — {offer.get('title', '')}"
    if match:
        caption += f"\n📊 Uygunluk: %{match['score']} ({match['met']}/{match['total']} temel şart CV'nde var)"
        if match["missing"]:
            caption += "\nEksik görünen: " + ", ".join(match["missing"])
    caption = caption[:1000]
    _run(_send_documents(paths, caption))


def send_ineligible_summary(items: list[tuple[dict, str, str]]):
    """Sinif sarti yuzunden elenen ilanlari tek mesajda gonderir; yanlis eleme varsa kullanici gorebilsin."""
    lines = ["🎓 <b>Sınıf şartı yüzünden elenen ilanlar</b> (yanlış eleme varsa bana yaz)\n"]
    for offer, reason, evidence in items:
        line = (f"• <a href=\"{html.escape(offer['url'], quote=True)}\">{html.escape(offer.get('title', ''))}</a>"
                f" — {html.escape(offer.get('company', ''))}\n   <i>“{html.escape(evidence[:160])}”</i>")
        if sum(len(l) for l in lines) + len(line) > 3800:  # Telegram mesaj siniri 4096
            lines.append(f"… ve {len(items) - (len(lines) - 1)} ilan daha")
            break
        lines.append(line)
    _run(_send_all("\n".join(lines)))
