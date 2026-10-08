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
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
TELEGRAM_CHAT_IDS = [
    c.strip() for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()
]
# Uyarlanmis CV / on yazi PDF'lerinin gidecegi chat'ler (bos ise TELEGRAM_CHAT_IDS'in hepsi)
TELEGRAM_CV_CHAT_IDS = [
    c.strip() for c in os.environ.get("TELEGRAM_CV_CHAT_IDS", "").split(",") if c.strip()
] or TELEGRAM_CHAT_IDS
# Bir calismada en fazla kac ilan icin CV + on yazi uretilecegi (calisma suresini sinirlamak icin)
MAX_APPLICATIONS_PER_RUN = int(os.environ.get("MAX_APPLICATIONS_PER_RUN", "80"))

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
    # Almanca/diger dillerdeki ilan basliklari icin (orn. "Praktikum Logistik")
    "logisti",          # logistik, logistique, logística, logistica
    "lieferkette",
    "produktion",
    "fertigung",
    "wirtschaftsingenieur",
    "prozessoptimierung",
    "optimierung",
    # Satin alma ve kalite
    "einkauf",
    "beschaffung",
    "procurement",
    "purchasing",
    "qualität",
    "qualitaet",
    "quality",
]

# İşimize yaramayan ama bu kaynaklarda sık çıkan gürültü kelimeleri (opsiyonel ek filtre)
EXCLUDE_KEYWORDS = [
    "graphic design",
    "social media",
    "babysitter",
    "bar & restaurant",
    "teaching internship",
    # Universite stajı olmayan ilanlar (Arbeitsagentur/Arbeitnow'dan geliyordu)
    "schülerprakti", "schüler/", "studentenjob", "ferienjob", "ferienarbeit", "minijob", "aushilfe",
    "ausbildung", "bundesfreiwillig", "bufdi", "freiwilliges soziales", "(fsj)", "bfd ",
    "produktionshelfer", "head of ",
    # "Produktion" kelimesinin medya anlami
    "tv-produktion", "filmproduktion", "videoproduktion", "medienproduktion", "pharmaziepraktikant",
    # "Operations" kelimesinin endustri muhendisligi disi anlamlari
    "hr operations", "people operations", "it operations", "tax operations", "legal operations",
    "treasury operations", "fund operations", "sales operations", "store operations", "cabin operations",
    "finance operations", "financial markets", "platform operations",
    # Basliginda "operations" gecen ama alan disi olan ilanlar (Amazon HR / IT / veri merkezi stajlari)
    "human resources", "it support", "data center", "marketing", "pharmaziepraktikum",
]

# Sadece staj/ogrenci pozisyonlarini kabul etmek icin gerekli anahtar kelimeler
# (tam zamanli/deneyimli pozisyonlar bu listede yoksa elenir)
INTERNSHIP_KEYWORDS = [
    "intern",
    "internship",
    "praktikum",
    "praktikant",       # Praktikant*in / Praktikant (m/w/d)
    "co-op",
    "stagiaire",
    "stajyer",
]

# Avrupa disi ilanlari elemek icin konum anahtar kelimeleri
# (location metni bunlardan birini icerirse ilan elenir)
NON_EUROPE_KEYWORDS = [
    "taiwan", "vietnam", "china", "singapore", "india", "indonesia",
    "malaysia", "thailand", "philippines", "japan", "korea", "hong kong",
    "russia", "usa", "united states", "mexico", "brazil", "argentina",
    "australia", "canada", "south africa", "nigeria", "kenya", "morocco",
    "egypt", "saudi", "uae", "dubai", "qatar", "israel", "pakistan",
    "bangladesh", "sri lanka", "chile", "colombia", "peru",
    "petaling jaya", "kuala lumpur", "mississauga", "toronto", "vancouver",
    "montreal", "ontario", "quebec", "san francisco", "boston", "indianapolis",
    "pleasanton", "santa clara", "shanghai", "beijing", "seoul", "tokyo",
    "osaka", "sydney", "melbourne", "auckland", "manila", "jakarta",
    "bangkok", "ho chi minh", "hanoi", "mumbai", "bangalore", "delhi",
    "sao paulo", "rio de janeiro", "mexico city", "hyderabad", "pune",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
