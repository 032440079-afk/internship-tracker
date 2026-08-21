# Kurulum Rehberi

Kodun tamamı hazır. Aşağıdaki adımlar SADECE senin yapman gereken kısımlar
(hesap açma, key alma) — bunları ben senin adına yapamam çünkü kimlik
bilgisi/parola içeriyorlar.

## 1. Firebase Projesi Kur

1. https://console.firebase.google.com → "Add project" → proje adı ver (örn. `internship-tracker`)
2. Sol menüden **Build > Firestore Database** → "Create database" → production mode, bölge olarak `eur3` (Avrupa) seç
3. Sol üstten ⚙️ (Project settings) → **Service accounts** sekmesi → "Generate new private key"
   → bir `.json` dosyası inecek. **Bu dosyayı kimseyle paylaşma, bana da gösterme.**

## 2. Telegram Bot Oluştur

1. Telegram'da **@BotFather**'ı bul, `/newbot` yaz
2. Bot'a isim ver (örn. `Kaan Staj Bot`)
3. BotFather sana bir **token** verecek (`123456:ABC-DEF...` formatında) — bunu not al
4. Botunu Telegram'da bul, `/start` yaz (bot'un sana mesaj atabilmesi için)
5. Kız arkadaşın da aynı bot'a `/start` yazmalı
6. İkinizin de **chat_id**'sini öğrenmek için: tarayıcıda şu adresi aç (TOKEN yerine kendi token'ını yaz):
   `https://api.telegram.org/botTOKEN/getUpdates`
   → JSON içinde `"chat":{"id": 123456789...}` kısmını bul, bu senin chat_id'n

## 3. GitHub Repo Oluştur

1. GitHub'da yeni bir **private** repo aç (örn. `internship-tracker`)
2. Bu klasördeki tüm dosyaları o repo'ya push et:
   ```bash
   cd internship-tracker
   git init
   git add .
   git commit -m "İlk kurulum"
   git remote add origin https://github.com/KULLANICI_ADIN/internship-tracker.git
   git push -u origin main
   ```

## 4. GitHub Secrets Ekle

Repo sayfasında: **Settings > Secrets and variables > Actions > New repository secret**

Üç secret ekle:
| Secret adı | Değer |
|---|---|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Adım 1'de indirdiğin `.json` dosyasının TÜM içeriği (kopyala-yapıştır) |
| `TELEGRAM_BOT_TOKEN` | Adım 2'de aldığın token |
| `TELEGRAM_CHAT_IDS` | Senin ve kız arkadaşının chat_id'leri, virgülle ayrılmış: `111111,222222` |

## 5. Test Et

- Repo'nun **Actions** sekmesine git → "Daily Internship Scrape" workflow'unu seç → **"Run workflow"** butonuyla manuel tetikle
- Loglara bak: kaç ilan bulundu, hata var mı
- **Beklenen sorun:** `scrapers/erasmus_careers.py` ve `scrapers/stageplaza.py` içindeki CSS selector'lar TAHMİNİ yazıldı (ben canlı siteyi bu ortamdan test edemedim, network kısıtlı). İlk çalıştırmada muhtemelen 0 ilan bulacak ya da hata verecek.

## 6. Bana Geri Dön

Actions logundaki hatayı (ya da "0 ilan bulundu" çıktısını) bana yapıştır,
ya da tarayıcıda F12 > Elements ile ilan kartlarının HTML yapısını
screenshot atıp gönder — ben selector'ları gerçek yapıya göre düzeltip
sana güncellenmiş dosyayı vereyim.

## Yerel Test (opsiyonel, GitHub'a hiç dokunmadan)

```bash
cd internship-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Sadece scraper'ı dene, Firestore/Telegram'a dokunmadan:
python scrapers/stageplaza.py
python scrapers/erasmus_careers.py

# Tam pipeline, dry-run (kayıt/bildirim yok, sadece ekrana yazar):
python run.py --dry-run
```
