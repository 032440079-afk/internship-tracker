"""
Merkezi ayarlar. Tüm hassas bilgiler ortam değişkeninden (environment variable)
okunur — hiçbir zaman kod içine yazılmaz, hiçbir zaman git'e commit edilmez.

Gerekli ortam değişkenleri:
  FIREBASE_SERVICE_ACCOUNT_JSON  -> Firebase servis hesabı JSON içeriği (tek satır string)
  TELEGRAM_BOT_TOKEN             -> @BotFather'dan alınan token
  TELEGRAM_CHAT_IDS              -> virgülle ayrılmış chat id listesi, örn: "111111,222222"
"""
import os

FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = [
    c.strip() for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()
]

# Alakalı ilanları filtrelemek için anahtar kelimeler (küçük harfe çevrilip aranır)
RELEVANT_KEYWORDS = [
    "industrial engineering",
    "industrial engineer",
    "supply chain",
    "logistics",
    "operations",
    "process engineer",
    "manufacturing",
    "production engineer",
    "lean",
    "operations research",
    "or-tools",
    "optimization",
    "endüstri mühendis",
]

# İşimize yaramayan ama bu kaynaklarda sık çıkan gürültü kelimeleri (opsiyonel ek filtre)
EXCLUDE_KEYWORDS = [
    "graphic design",
    "social media",
    "babysitter",
    "bar & restaurant",
    "teaching internship",
]

# Sadece staj/ogrenci pozisyonlarini kabul etmek icin gerekli anahtar kelimeler
# (tam zamanli/deneyimli pozisyonlar bu listede yoksa elenir)
INTERNSHIP_KEYWORDS = [
    "intern",
    "internship",
    "praktikum",
    "werkstudent",
    "working student",
    "trainee",
    "co-op",
    "thesis",
    "abschlussarbeit",
    "duales studium",
    "stagiaire",
    "stajyer",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
