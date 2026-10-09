"""
Saatlik calisir (.github/workflows/telegram-updates.yml): Telegram'daki basvuru durumu butonlarini ve /ozet gibi
komutlari isler. Ayrintilar lib/tracking.py'de.
"""
import asyncio

from lib import tracking

if __name__ == "__main__":
    asyncio.run(tracking.process_updates())
