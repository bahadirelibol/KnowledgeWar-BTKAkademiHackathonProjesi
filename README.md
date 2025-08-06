
# KNOWLEDGEWAR - Eğitim Platformu

  

  

## 📖 Proje Hakkında

  

  

KNOWLEDGEWAR, modern teknolojiler kullanarak geliştirilmiş kapsamlı bir eğitim platformudur. Platform, kullanıcıların BTK kurslarını keşfetmesi, öğrenme yolculuklarını planlaması, turnuvalara katılması ve AI destekli asistan ile etkileşim kurmasına olanak sağlar.

  

  

## ✨ Özellikler

  

  

### 🎓 Eğitim Yönetimi

  

  

-  **BTK Kurs Arama**: BTK platformundan kurs arama ve keşfetme

  

-  **Dinamik Roadmap**: Kişiselleştirilmiş öğrenme yolları oluşturma

  

-  **İlerleme Takibi**: Kurs tamamlama durumu ve ilerleme yüzdesi

  

-  **Profil Analizi**: Kullanıcı yeteneklerine göre kurs önerileri

  

  

### 🏆 Turnuva Sistemi

  

  

-  **Turnuva Oluşturma**: Admin paneli ile turnuva yönetimi

  

-  **Katılım Sistemi**: Kullanıcıların turnuvalara kayıt olması

  

-  **Gerçek Zamanlı Sıralama**: Liderlik tablosu ve istatistikler

  

-  **Otomatik Soru Üretimi**: AI destekli soru oluşturma

  

  

### 🤖 AI Asistan

  

  

-  **RAG Sistemi**: PDF tabanlı bilgi tabanı ile sohbet

  

-  **Gemini AI Entegrasyonu**: Google'ın en son AI modeli

  

-  **Akıllı Yanıtlar**: Bağlama duyarlı cevaplar

  

  

### 👤 Kullanıcı Yönetimi

  

  

-  **Kayıt/Giriş Sistemi**: JWT token tabanlı kimlik doğrulama

  

-  **Profil Yönetimi**: Kullanıcı bilgileri ve istatistikler

  

-  **Güvenlik**: Şifre hashleme ve token yönetimi

  

  

## 🛠️ Teknolojiler

  

  

### Backend

  

  

-  **Flask**: Web framework

  

-  **SQLite**: Veritabanı

  

-  **JWT**: Kimlik doğrulama

  

-  **Selenium**: Web scraping

  

-  **BeautifulSoup**: HTML parsing

  

  

### AI & ML

  

  

-  **Google Gemini AI**: Soru üretimi ve sohbet

  

-  **LangChain**: RAG sistemi

  

-  **Chroma DB**: Vector database

  

-  **PyPDF**: PDF işleme

  

  

### Frontend

  

  

-  **HTML5/CSS3**: Modern ve responsive tasarım

  

-  **JavaScript**: Dinamik kullanıcı deneyimi

  

-  **Bootstrap**: UI framework

  

  

## 📁 Proje Yapısı

  

  

```

  

BTK/

  

├── app.py # Ana uygulama

  

├── requirements.txt # Python bağımlılıkları

  

├── database.db # SQLite veritabanı

  

├── mypdf.pdf # RAG sistemi için bilgi kaynağı

  

├── chroma_db/ # Vector database

  

├── templates/ # HTML şablonları

  

│ ├── index.html # Ana sayfa

  

│ ├── login-register.html #giriş kayıt

  

│ ├── profile.html # Kullanıcı profili

  

│ ├── roadmap.html # Öğrenme yolu

  

│ ├── tournament.html # Turnuva sayfası

  

│ ├── tournament-admin.html

  

│ ├── learn.html # Öğrenme sayfası

  

│ ├── battle.html # Turnuva savaşı

  

│ └── test.html # Test sayfası

  

└── static/ # Statik dosyalar

  

├── styles.css # Ana stil dosyası

  

├── profile.css # Profil stilleri

  

├── script.js # Ana JavaScript

  

├── profile.js # Profil JavaScript

  

├── chatbot.js # AI asistan

  

└── chatbot.html # Chatbot arayüzü

  

```

  

  

## 🚀 Kurulum

  

  

### Gereksinimler

  

  

- Python

  

- Chrome tarayıcı (Selenium için)

  

- env dosyası için gerkli anahtarlar

  

  

### Adımlar

  

  

1.  **Projeyi klonlayın**

  

  

```bash

  

git  clone <repository-url>

  

cd  BTK

  

```

  

  

2.  **Ortam oluşturun**

  

  

```bash

  

conda  create  -n  my_env  python=3.10

  

conda  activate  my_env

  

```

  

  

3.  **Bağımlılıkları yükleyin**

  

  

```bash

  

pip  install  -r  requirements.txt

  

```

  

  

4.  **Çevre değişkenlerini ayarlayın**

  

  

```bash

  

# .env dosyasını oluşturun ve aşağıdaki satırları ekleyin

  

GEMINI_API_KEY=

GOOGLE_SEARCH_API_KEY=

GOOGLE_CSE_ID=778db080ec34d45a5

  

#Google ai studio üzerinden gemini(GEMINI_API_KEY) api key alabilirsiniz

#Google Cloud Console üzerinden (GOOGLE_SEARCH_API_KEY) api key alabilirsiniz.

  

```

  

  

5.  **Uygulamayı çalıştırın**

  

  

```bash

  

python  app.py

  

```

  ## **🎬️**Proje Videosu
Proje videosunu izlemek için:

- [[video](https://github.com/bahadirelibol/BTK/blob/main/tanitim_video.mp4)]

  
  


## 🎯 Kullanım Senaryoları

  

  

### Öğrenci Kullanıcısı

  

  

1. Platforma kayıt olun

  

2. Profil analizi yapın

  

3. Önerilen kursları roadmap'e ekleyin

  

4. Kursları takip edin ve tamamlayın

  

5. Test çözün

  

6. Turnuvalara katılın ve yarışın

  

7. AI asistan ile sorularınızı sorun

  

## 🔧 Konfigürasyon

  

  

### RAG Sistemi

  

  

-  `mypdf.pdf` dosyasını güncelleyerek bilgi tabanını değiştirebilirsiniz

  
  
  

### AI Modeli

  

- Gemini API anahtarınızı `.env` dosyasında ayarlayın

  

- Model parametrelerini `app.py` dosyasında düzenleyebilirsiniz

  

  
  

### Debug Modu

  

  

```bash

  

python  app.py  --debug

  

```

  

  

## 📞 İletişim

  

  

Proje hakkında sorularınız için:

  

  

- İletişim: [[k.erden03@gmail.com](mailto:k.erden03@gmail.com)]

  

- GitHub: [https://github.com/Kerden22]

  
  

- İletişim: [[www.suleymanyilmaz.me](http://www.suleymanyilmaz.me/)]

  

- GitHub: [https://github.com/Kerden22]

  

- İletişim: [[bahadirelibol60@gmail.com](mailto:bahadirelibol60@gmail.com)]

  

- GitHub: [https://github.com/bahadirelibol]

  

---