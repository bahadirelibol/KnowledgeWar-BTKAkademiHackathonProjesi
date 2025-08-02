import streamlit as st
import json
import os
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Gemini API anahtarını al
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Gemini API'yi yapılandır
genai.configure(api_key=GEMINI_API_KEY)

def generate_questions_with_gemini(topic):
    """Gemini API kullanarak sorular üretir"""
    try:
        # Gemini Flash modelini kullan
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""{topic} konusu hakkında 10 adet çoktan seçmeli test sorusu hazırla.

Yanıtını sadece JSON formatında ver:
[
  {{
    "question": "Soru metni",
    "options": ["A seçeneği", "B seçeneği", "C seçeneği", "D seçeneği"],
    "correct_option": "A"
  }}
]

Sadece JSON ver, başka hiçbir şey yazma."""
        
        response = model.generate_content(prompt)
        
        # API yanıtını kontrol et
        response_text = response.text.strip()
        
        # Debug için yanıtı göster
        st.info(f"API Yanıtı: {response_text}")
        st.info(f"Yanıt uzunluğu: {len(response_text)} karakter")
        
        # JSON yanıtını parse et
        try:
            # Önce yanıtı temizle
            cleaned_response = response_text.strip()
            
            # JSON başlangıcını bul
            start_idx = cleaned_response.find('[')
            end_idx = cleaned_response.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_part = cleaned_response[start_idx:end_idx]
                questions_data = json.loads(json_part)
                return questions_data
            else:
                # Direkt parse etmeyi dene
                questions_data = json.loads(cleaned_response)
                return questions_data
                
        except json.JSONDecodeError as json_error:
            # Daha agresif temizleme dene
            try:
                # Markdown kod bloklarını temizle
                if '```json' in cleaned_response:
                    start = cleaned_response.find('```json') + 7
                    end = cleaned_response.find('```', start)
                    if end != -1:
                        json_part = cleaned_response[start:end].strip()
                        questions_data = json.loads(json_part)
                        return questions_data
                
                # Sadece JSON kısmını bul
                import re
                json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
                if json_match:
                    json_part = json_match.group()
                    questions_data = json.loads(json_part)
                    return questions_data
                    
            except:
                pass
            
            st.error(f"JSON parse hatası: {str(json_error)}")
            st.error("API'den gelen yanıt JSON formatında değil. Lütfen tekrar deneyin.")
            return None
        
    except Exception as e:
        st.error(f"Soru üretilirken hata oluştu: {str(e)}")
        return None

def save_tournament_data(tournament_data):
    """Turnuva verilerini JSON dosyasına kaydeder"""
    try:
        with open('tournament.json', 'w', encoding='utf-8') as f:
            json.dump(tournament_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Dosya kaydedilirken hata oluştu: {str(e)}")
        return False

# Streamlit uygulaması
def main():
    st.set_page_config(page_title="Turnuva Admin Paneli", layout="wide")
    
    st.title("🏆 Turnuva Admin Paneli")
    st.markdown("---")
    
    # Sidebar'da API key kontrolü
    with st.sidebar:
        st.header("🔧 Ayarlar")
        if not GEMINI_API_KEY:
            st.error("❌ GEMINI_API_KEY bulunamadı!")
            st.info("Lütfen .env dosyasında GEMINI_API_KEY'i tanımlayın.")
            return
        else:
            st.success("✅ Gemini API Key mevcut")
    
    # Ana form
    with st.form("tournament_form"):
        st.header("📋 Turnuva Bilgileri")
        
        # Turnuva başlığı (sadece bilgi amaçlı)
        tournament_title = st.text_input(
            "Turnuva Başlığı",
            placeholder="Örn: Python Programlama Turnuvası"
        )
        
        # Turnuva içeriği (soru üretimi için)
        tournament_content = st.text_area(
            "Turnuva İçeriği",
            placeholder="Örn: Python programlama dili, değişkenler, döngüler, fonksiyonlar, listeler, sözlükler, dosya işlemleri, hata yönetimi, nesne yönelimli programlama, modüller ve paketler hakkında sorular hazırla",
            height=100,
            help="Bu alana yazdığınız konulara göre sorular üretilecektir. Başlık sadece turnuva adı için kullanılır."
        )
        
        # Tarih ve saat seçimi
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Başlangıç Tarihi", value=datetime.now().date())
            start_hour = st.selectbox("Başlangıç Saati", range(0, 24), index=datetime.now().hour)
            start_minute = st.selectbox("Başlangıç Dakikası", range(0, 60, 5), index=0)
            start_time = datetime.combine(start_date, datetime.min.time().replace(hour=start_hour, minute=start_minute))
        
        with col2:
            end_date = st.date_input("Bitiş Tarihi", value=datetime.now().date())
            end_hour = st.selectbox("Bitiş Saati", range(0, 24), index=datetime.now().hour + 2)
            end_minute = st.selectbox("Bitiş Dakikası", range(0, 60, 5), index=0)
            end_time = datetime.combine(end_date, datetime.min.time().replace(hour=end_hour, minute=end_minute))
        
        # LLM'den soru üret butonu
        generate_questions = st.form_submit_button(
            "🤖 LLM'den Soru Üret",
            type="primary",
            use_container_width=True
        )
    
    # Soru üretme işlemi
    if generate_questions and tournament_content:
        with st.spinner("Sorular üretiliyor..."):
            questions = generate_questions_with_gemini(tournament_content)
            
            if questions:
                st.session_state.questions = questions
                st.success(f"✅ {len(questions)} soru başarıyla üretildi!")
            else:
                st.error("❌ Sorular üretilemedi!")
    elif generate_questions and not tournament_content:
        st.error("❌ Lütfen Turnuva İçeriği alanını doldurun!")
    
    # Soruları düzenleme bölümü
    if 'questions' in st.session_state and st.session_state.questions:
        st.header("📝 Soruları Düzenle")
        
        # Her soru için düzenleme formu
        edited_questions = []
        
        for i, question in enumerate(st.session_state.questions):
            st.subheader(f"Soru {i+1}")
            
            with st.expander(f"Soru {i+1} - {question.get('question', '')[:50]}..."):
                # Soru metni
                question_text = st.text_area(
                    "Soru Metni",
                    value=question.get('question', ''),
                    key=f"question_{i}"
                )
                
                # Şıklar
                options = question.get('options', ['A', 'B', 'C', 'D'])
                edited_options = []
                
                col1, col2 = st.columns(2)
                with col1:
                    option_a = st.text_input("A Şıkkı", value=options[0] if len(options) > 0 else '', key=f"option_a_{i}")
                    option_b = st.text_input("B Şıkkı", value=options[1] if len(options) > 1 else '', key=f"option_b_{i}")
                
                with col2:
                    option_c = st.text_input("C Şıkkı", value=options[2] if len(options) > 2 else '', key=f"option_c_{i}")
                    option_d = st.text_input("D Şıkkı", value=options[3] if len(options) > 3 else '', key=f"option_d_{i}")
                
                edited_options = [option_a, option_b, option_c, option_d]
                
                # Doğru şık seçimi
                correct_option = st.selectbox(
                    "Doğru Şık",
                    options=['A', 'B', 'C', 'D'],
                    index=['A', 'B', 'C', 'D'].index(question.get('correct_option', 'A')),
                    key=f"correct_{i}"
                )
                
                # Düzenlenmiş soruyu listeye ekle
                edited_questions.append({
                    'question': question_text,
                    'options': edited_options,
                    'correct_option': correct_option
                })
        
        # Turnuvayı kaydet butonu
        if st.button("💾 Turnuvayı Kaydet", type="primary", use_container_width=True):
            if tournament_title and tournament_content and start_time and end_time:
                # Turnuva verilerini hazırla
                tournament_data = {
                    'title': tournament_title,
                    'content': tournament_content,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'created_at': datetime.now().isoformat(),
                    'questions': edited_questions
                }
                
                # Dosyaya kaydet
                if save_tournament_data(tournament_data):
                    st.success("✅ Turnuva başarıyla kaydedildi!")
                    
                    # JSON verilerini göster
                    st.subheader("📄 Kaydedilen Veriler")
                    st.json(tournament_data)
                    
                    # Dosya indirme linki
                    st.download_button(
                        label="📥 tournament.json Dosyasını İndir",
                        data=json.dumps(tournament_data, ensure_ascii=False, indent=2),
                        file_name="tournament.json",
                        mime="application/json"
                    )
            else:
                st.error("❌ Lütfen Turnuva Başlığı, Turnuva İçeriği ve tarih bilgilerini doldurun!")

if __name__ == "__main__":
    main() 