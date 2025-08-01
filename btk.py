import streamlit as st
import google.generativeai as genai
import requests
import os
from dotenv import load_dotenv
import json

# Environment variables yükle
load_dotenv()

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="BTK Akademi Kurs Önerisi",
    page_icon="🎓",
    layout="wide"
)

# Gemini API konfigürasyonu
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def test_gemini_connection():
    """Gemini API bağlantısını test et"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Merhaba, bu bir test mesajıdır.")
        return response.parts[0].text if response.parts else None
    except Exception as e:
        return f"Hata: {str(e)}"

def search_btk_courses(query):
    """BTK Akademi'de kurs arama"""
    try:
        # Debug bilgisi
        st.info(f"🔍 Arama sorgusu: '{query}'")
        
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": os.getenv("GOOGLE_SEARCH_API_KEY"),
                "cx": os.getenv("GOOGLE_CSE_ID"),
                "q": query,
                "num": 10,  # Maksimum 10 sonuç
                "siteSearch": "btkakademi.gov.tr",  # Site kısıtlaması
                "siteSearchFilter": "i"  # Sadece bu sitede ara
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            # Debug bilgisi
            if items:
                st.success(f"✅ {len(items)} sonuç bulundu")
            else:
                st.warning(f"⚠️ '{query}' sorgusu için sonuç bulunamadı")
                
            return items
        else:
            st.error(f"Arama hatası: {response.status_code}")
            st.error(f"Hata detayı: {response.text}")
            return []
            
    except Exception as e:
        st.error(f"Arama sırasında hata oluştu: {str(e)}")
        return []

def analyze_user_profile(responses):
    """Kullanıcı yanıtlarını analiz ederek profil oluştur"""
    prompt = f"""
    Sen bir eğitim danışmanısın. Aşağıdaki kullanıcı yanıtlarını analiz ederek kapsamlı bir öğrenme profili oluştur:
    
    Kullanıcı Yanıtları:
    1. Öğrenmek istediği beceri/konu: {responses['skill']}
    2. Öğrenme amacı: {responses['goal']}
    3. Mevcut seviye: {responses['level']}
    4. Haftalık zaman: {responses['time']}
    5. Öğrenme tercihi: {responses['learning_style']}
    
    Bu bilgilere dayanarak şunları belirle:
    - Kullanıcının öğrenme hedefi ve motivasyonu
    - Uygun kurs seviyesi (başlangıç/orta/ileri)
    - Önerilen öğrenme yaklaşımı
    - Beklenen öğrenme süresi
    - Özel ihtiyaçlar veya tercihler
    
    ÖNEMLİ: Yanıtını SADECE JSON formatında ver, başka hiçbir şey ekleme. Açıklama, giriş veya sonuç yazma, sadece JSON:
    {{
        "hedef": "açıklama",
        "seviye": "başlangıç/orta/ileri",
        "yaklasim": "açıklama",
        "sure": "tahmini süre",
        "ozel_ihtiyaclar": "varsa özel ihtiyaçlar"
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        text = response.parts[0].text if response.parts else None
        
        if not text:
            st.error("Gemini'den boş yanıt alındı")
            return None
        
        # JSON parsing'i daha güvenli hale getir
        try:
            # Önce temizleme yap
            text = text.strip()
            # JSON bloklarını bul
            if '{' in text and '}' in text:
                start = text.find('{')
                end = text.rfind('}') + 1
                json_text = text[start:end]
                return json.loads(json_text)
            else:
                raise ValueError("JSON formatı bulunamadı")
                
        except json.JSONDecodeError as json_error:
            st.warning(f"JSON parsing hatası: {str(json_error)}")
            st.info("Gemini'den gelen yanıt:")
            st.code(text)
            
            # Fallback: Basit profil oluştur
            st.info("Basit profil oluşturuluyor...")
            return create_simple_profile(responses)
            
    except Exception as e:
        st.error(f"Profil analizi sırasında hata: {str(e)}")
        return None

def create_simple_profile(responses):
    """JSON parsing başarısız olduğunda basit profil oluştur"""
    # Seviye belirleme
    level_mapping = {
        "Hiç bilmiyorum": "başlangıç",
        "Temel bilgim var": "başlangıç",
        "Orta seviye": "orta",
        "İleri seviye": "ileri"
    }
    
    # Öğrenme tarzı belirleme
    style_mapping = {
        "Videolu anlatım": "görsel ve işitsel öğrenme",
        "Uygulamalı görevler": "pratik odaklı öğrenme",
        "Proje odaklı": "proje tabanlı öğrenme",
        "Metin ve dökümanla öğrenme": "okuma ve yazma odaklı öğrenme"
    }
    
    return {
        "hedef": f"{responses['skill']} öğrenerek {responses['goal']}",
        "seviye": level_mapping.get(responses['level'], "başlangıç"),
        "yaklasim": style_mapping.get(responses['learning_style'], "genel öğrenme"),
        "sure": f"{responses['time']} süreyle",
        "ozel_ihtiyaclar": "Yok"
    }

def recommend_courses(profile, courses):
    """Kurs önerileri oluştur"""
    courses_text = ""
    for i, course in enumerate(courses, 1):
        courses_text += f"{i}. {course['title']}\n"
        courses_text += f"   Açıklama: {course.get('snippet', 'Açıklama bulunamadı')}\n"
        courses_text += f"   Link: {course.get('link', 'Link bulunamadı')}\n\n"
    
    prompt = f"""
    Sen BTK Akademi'nin eğitim danışmanısın. Kullanıcının profili şöyle:
    
    Kullanıcı Profili:
    - Hedef: {profile['hedef']}
    - Seviye: {profile['seviye']}
    - Yaklaşım: {profile['yaklasim']}
    - Süre: {profile['sure']}
    - Özel ihtiyaçlar: {profile.get('ozel_ihtiyaclar', 'Yok')}
    
    Mevcut BTK Akademi kursları:
    {courses_text}
    
    Bu kurslar arasından kullanıcıya en uygun 2-3 kursu seç ve her biri için:
    1. Neden bu kursu önerdiğini açıkla
    2. Bu kursun kullanıcının hedefine nasıl katkı sağlayacağını belirt
    3. Kursun seviyesinin kullanıcıya uygunluğunu değerlendir
    4. Öğrenme tarzına uygunluğunu açıkla
    
    Sadece gerçekten uygun olanları seç. Genel veya alakasız olanları önermene gerek yok.
    
    Yanıtını Türkçe olarak, düzenli ve anlaşılır bir şekilde ver.
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        text = response.parts[0].text if response.parts else None
        return text
    except Exception as e:
        st.error(f"Öneri oluşturma sırasında hata: {str(e)}")
        return None

def main():
    st.title("🎓 BTK Akademi Kişiselleştirilmiş Kurs Önerisi")
    st.markdown("---")
    
    # Sidebar - API durumu
    with st.sidebar:
        st.header("🔧 Sistem Durumu")
        
        # API anahtarlarını kontrol et
        google_api = os.getenv("GOOGLE_SEARCH_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        gemini_api = os.getenv("GEMINI_API_KEY")
        
        if google_api and google_api != "your_google_search_api_key_here":
            st.success("✅ Google Search API")
        else:
            st.error("❌ Google Search API")
            
        if cse_id and cse_id != "your_custom_search_engine_id_here":
            st.success("✅ Google CSE ID")
        else:
            st.error("❌ Google CSE ID")
            
        if gemini_api and gemini_api != "your_gemini_api_key_here":
            st.success("✅ Gemini API")
            
            # Gemini test butonu
            if st.button("🧪 Gemini Bağlantısını Test Et"):
                with st.spinner("Gemini API test ediliyor..."):
                    test_result = test_gemini_connection()
                    if test_result and not test_result.startswith("Hata"):
                        st.success("✅ Gemini API çalışıyor!")
                        st.info(f"Test yanıtı: {test_result[:100]}...")
                    else:
                        st.error(f"❌ Gemini API hatası: {test_result}")
        else:
            st.error("❌ Gemini API")
    
    # Ana form
    with st.form("user_profile_form"):
        st.header("📝 Profil Bilgilerinizi Girin")
        
        # Soru 1: Beceri/Konu
        skill = st.text_input(
            "🎯 Hangi beceriyi veya konuyu öğrenmek istiyorsun?",
            placeholder="Örnek: Python, siber güvenlik, İngilizce, Excel, veri analizi..."
        )
        
        # Soru 2: Amaç
        goal = st.text_input(
            "🎯 Bu beceriyi öğrenme amacın nedir?",
            placeholder="Örnek: iş bulmak, freelance çalışmak, kendi projemi geliştirmek, sadece merak ediyorum..."
        )
        
        # Soru 3: Seviye
        level = st.selectbox(
            "📚 Bu konuda daha önce bir eğitim aldın mı veya bilgin var mı?",
            ["Hiç bilmiyorum", "Temel bilgim var", "Orta seviye", "İleri seviye"]
        )
        
        # Soru 4: Zaman
        time = st.text_input(
            "⏳ Haftalık olarak öğrenmeye ne kadar zaman ayırabilirsin?",
            placeholder="Örnek: günde 1 saat, haftada 10 saat, yalnızca hafta sonları..."
        )
        
        # Soru 5: Öğrenme tarzı
        learning_style = st.selectbox(
            "👨‍💻 Aşağıdaki öğrenme biçimlerinden hangisi sana daha uygun?",
            ["Videolu anlatım", "Uygulamalı görevler", "Proje odaklı", "Metin ve dökümanla öğrenme"]
        )
        
        submitted = st.form_submit_button("🚀 Kurs Önerilerini Al")
    
    # Form gönderildiğinde
    if submitted:
        if not all([skill, goal, time]):
            st.error("❌ Lütfen tüm alanları doldurun!")
            return
        
        # API anahtarlarını kontrol et
        if not all([google_api, cse_id, gemini_api]) or any([
            google_api == "your_google_search_api_key_here",
            cse_id == "your_custom_search_engine_id_here", 
            gemini_api == "your_gemini_api_key_here"
        ]):
            st.error("❌ Lütfen önce API anahtarlarınızı .env dosyasında yapılandırın!")
            st.info("📋 env_example.txt dosyasını .env olarak kopyalayıp API anahtarlarınızı ekleyin.")
            return
        
        # Loading göster
        with st.spinner("🔍 Profiliniz analiz ediliyor..."):
            responses = {
                'skill': skill,
                'goal': goal,
                'level': level,
                'time': time,
                'learning_style': learning_style
            }
            
            # Profil analizi
            profile = analyze_user_profile(responses)
            
            if not profile:
                st.error("❌ Profil analizi başarısız!")
                return
        
        # Profil sonuçlarını göster
        st.success("✅ Profil analizi tamamlandı!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 Profil Özeti")
            st.write(f"**Hedef:** {profile['hedef']}")
            st.write(f"**Seviye:** {profile['seviye']}")
            st.write(f"**Yaklaşım:** {profile['yaklasim']}")
        
        with col2:
            st.write(f"**Süre:** {profile['sure']}")
            if profile.get('ozel_ihtiyaclar'):
                st.write(f"**Özel İhtiyaçlar:** {profile['ozel_ihtiyaclar']}")
        
        # Kurs arama
        with st.spinner("🔍 BTK Akademi'de uygun kurslar aranıyor..."):
            # İlk arama sorgusu
            search_query = f"{skill} {profile['hedef']} {profile['seviye']} seviye kurs"
            courses = search_btk_courses(search_query)
            
            # Eğer sonuç bulunamazsa, daha genel arama yap
            if not courses:
                st.warning("⚠️ İlk aramada sonuç bulunamadı, daha genel arama yapılıyor...")
                search_query = f"{skill} programlama eğitim"
                courses = search_btk_courses(search_query)
            
            # Hala sonuç yoksa, çok genel arama
            if not courses:
                st.warning("⚠️ Genel aramada da sonuç bulunamadı, tüm programlama kursları aranıyor...")
                search_query = "programlama yazılım eğitim"
                courses = search_btk_courses(search_query)
            
            if not courses:
                st.error("❌ BTK Akademi'de uygun kurs bulunamadı!")
                st.info("💡 Öneriler:")
                st.write("- Farklı bir beceri/konu deneyin")
                st.write("- Daha genel terimler kullanın (örn: 'yazılım' yerine 'programlama')")
                st.write("- BTK Akademi'yi manuel olarak kontrol edin")
                return
        
        # Kurs önerileri
        with st.spinner("🤖 Kişiselleştirilmiş öneriler hazırlanıyor..."):
            recommendations = recommend_courses(profile, courses)
            
            if not recommendations:
                st.error("❌ Öneri oluşturma başarısız!")
                return
        
        # Sonuçları göster
        st.success("🎉 Kurs önerileriniz hazır!")
        st.markdown("---")
        
        st.subheader("📋 Önerilen Kurslar")
        st.markdown(recommendations)
        
        # Bulunan kursların listesi
        st.subheader("🔍 Bulunan Kurslar")
        for i, course in enumerate(courses[:10], 1):
            with st.expander(f"{i}. {course['title']}"):
                st.write(f"**Açıklama:** {course.get('snippet', 'Açıklama bulunamadı')}")
                if course.get('link'):
                    st.write(f"**Link:** [{course['link']}]({course['link']})")

if __name__ == "__main__":
    main() 