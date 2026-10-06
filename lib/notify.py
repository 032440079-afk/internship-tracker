"""
Yeni ilan bulunduğunda Telegram üzerinden bildirim gönderir.
Birden fazla chat_id'ye (sen + kız arkadaşın) aynı anda mesaj atar.
"""
import asyncio
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


async def _send_all(text: str):
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


def notify_new_offer(offer: dict):
    text = _format_message(offer)
    asyncio.run(_send_all(text))


def send_application_files(offer: dict, paths: list[str]):
    caption = f"📎 {offer.get('company', '')} — {offer.get('title', '')}"[:1000]
    asyncio.run(_send_documents(paths, caption))
