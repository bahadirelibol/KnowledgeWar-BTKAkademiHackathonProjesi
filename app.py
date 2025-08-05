from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import hashlib
import jwt
import datetime
import os
import requests
import json
import re
import urllib3
from werkzeug.security import generate_password_hash, check_password_hash
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import google.generativeai as genai

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Gemini API konfigürasyonu
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")
if GEMINI_API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'btk-auth-secret-key-2024'
CORS(app)

# Veritabanı oluşturma
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Users tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Turnuvalar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            question_count INTEGER DEFAULT 15,
            duration_minutes INTEGER DEFAULT 45,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Sorular tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
        )
    ''')
    
    # Turnuva katılımcıları tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournament_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tournament_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            total_score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
        )
    ''')
    
    # Kullanıcı cevapları tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tournament_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_option TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            answer_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')
    
    # Kullanıcı profilleri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill TEXT NOT NULL,
            goal TEXT NOT NULL,
            level TEXT NOT NULL,
            time_commitment TEXT NOT NULL,
            learning_style TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Seçilen kurslar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_title TEXT NOT NULL,
            course_link TEXT NOT NULL,
            course_description TEXT,
            roadmap_sections TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def update_database_schema():
    """Mevcut veritabanı şemasını güncelle"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Mevcut sütunları kontrol et
        cursor.execute("PRAGMA table_info(tournaments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Eksik sütunları ekle
        if 'question_count' not in columns:
            cursor.execute('ALTER TABLE tournaments ADD COLUMN question_count INTEGER DEFAULT 15')
            print("question_count sütunu eklendi")
            
        if 'duration_minutes' not in columns:
            cursor.execute('ALTER TABLE tournaments ADD COLUMN duration_minutes INTEGER DEFAULT 45')
            print("duration_minutes sütunu eklendi")
        
        conn.commit()
        conn.close()
        print("Veritabanı şeması güncellendi")
        
    except Exception as e:
        print(f"Veritabanı güncelleme hatası: {e}")

# Veritabanını başlat
init_db()
update_database_schema()

# BTK Akademi entegrasyonu için fonksiyonlar
def search_btk_courses(query):
    """BTK Akademi'de kurs arama"""
    try:
        # Environment variables'dan API anahtarlarını al
        google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        
        # API anahtarları yoksa demo veri döndür
        if not google_api_key or not cse_id or google_api_key == "your_google_search_api_key_here":
            print("API keys not configured, returning demo data")
            return get_demo_courses(query)
        
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": google_api_key,
                "cx": cse_id,
                "q": query,
                "num": 10,
                "siteSearch": "btkakademi.gov.tr",
                "siteSearchFilter": "i"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("items", [])
        else:
            print(f"API response error: {response.status_code}")
            return get_demo_courses(query)
            
    except Exception as e:
        print(f"BTK arama hatası: {str(e)}")
        return get_demo_courses(query)

def get_demo_courses(query):
    """Demo kurs verileri döndür"""
    demo_courses = [
        {
            "title": "Python Programlama Temelleri",
            "link": "https://btkakademi.gov.tr/course/python-temelleri",
            "snippet": "Python programlama dilinin temel kavramları, değişkenler, döngüler, fonksiyonlar ve nesne yönelimli programlama konularını içeren kapsamlı bir kurs."
        },
        {
            "title": "Python ile Veri Analizi",
            "link": "https://btkakademi.gov.tr/course/python-veri-analizi",
            "snippet": "Pandas, NumPy ve Matplotlib kütüphaneleri kullanarak veri analizi ve görselleştirme tekniklerini öğrenin."
        },
        {
            "title": "Python Web Geliştirme",
            "link": "https://btkakademi.gov.tr/course/python-web",
            "snippet": "Django ve Flask framework'leri ile web uygulamaları geliştirme ve API tasarımı konularını kapsar."
        },
        {
            "title": "Python Makine Öğrenmesi",
            "link": "https://btkakademi.gov.tr/course/python-ml",
            "snippet": "Scikit-learn, TensorFlow ve PyTorch kullanarak makine öğrenmesi algoritmaları ve yapay zeka uygulamaları."
        },
        {
            "title": "Python Siber Güvenlik",
            "link": "https://btkakademi.gov.tr/course/python-security",
            "snippet": "Python ile güvenlik testleri, penetrasyon testleri ve güvenlik araçları geliştirme konuları."
        }
    ]
    
    # Query'ye göre filtrele
    filtered_courses = []
    query_lower = query.lower()
    
    for course in demo_courses:
        if any(keyword in course['title'].lower() or keyword in course['snippet'].lower() 
               for keyword in query_lower.split()):
            filtered_courses.append(course)
    
    # Eğer hiç sonuç bulunamazsa, ilk 2 kursu döndür
    if not filtered_courses:
        return demo_courses[:2]
    
    return filtered_courses

def analyze_user_profile(responses):
    """Kullanıcı yanıtlarını analiz ederek profil oluştur"""
    try:
        # Basit profil oluştur (Gemini API olmadan)
        level_mapping = {
            "Hiç bilmiyorum": "başlangıç",
            "Temel bilgim var": "başlangıç",
            "Orta seviye": "orta",
            "İleri seviye": "ileri"
        }
        
        style_mapping = {
            "Videolu anlatım": "görsel ve işitsel öğrenme",
            "Uygulamalı görevler": "pratik odaklı öğrenme",
            "Proje odaklı": "proje tabanlı öğrenme",
            "Metin ve dökümanla öğrenme": "okuma ve yazma odaklı öğrenme"
        }
        
        return {
            "hedef": f"{responses['skill']} öğrenerek {responses['goal']}",
            "seviye": level_mapping.get(responses['level'], "başlangıç"),
            "yaklasim": "genel öğrenme",
            "sure": f"{responses['time']} süreyle",
            "ozel_ihtiyaclar": "Yok"
        }
        
    except Exception as e:
        print(f"Profil analizi hatası: {str(e)}")
        return None

def recommend_best_course(profile, courses, skill):
    """En uygun kursu seç"""
    if not courses:
        return None
    
    # İlk kursu en uygun olarak seç
    best_course = courses[0]
    
    return {
        "title": best_course.get('title', 'Kurs başlığı bulunamadı'),
        "link": best_course.get('link', '#'),
        "description": best_course.get('snippet', 'Açıklama bulunamadı'),
        "reason": f"Bu kurs {profile['seviye']} seviyesinde {skill} öğrenmek için en uygun seçenektir."
    }

def scrape_btk_course_sections(course_url):
    """BTK Akademi kurs sayfasından bölümleri çek - Hibrit versiyon"""
    try:
        print(f"Kurs sayfasına gidiliyor: {course_url}")
        
        # Önce Requests ile dene (hızlı)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(course_url, headers=headers, timeout=2, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            print("Requests ile HTML alındı, bölümler aranıyor...")
            
            # Bölümleri bul
            sections = []
            span_elements = soup.find_all('span', class_='font-medium text-base')
            print(f"font-medium text-base ile {len(span_elements)} span bulundu")
            
            for span in span_elements:
                text = span.get_text().strip()
                if re.match(r'^\d+\.', text):
                    sections.append(text)
                    print(f"Bölüm bulundu: {text}")
            
            if sections:
                print(f"Requests başarılı! Toplam {len(sections)} bölüm bulundu")
                return sections
                
        except Exception as e:
            print(f"Requests başarısız: {e}")
        
        # Requests başarısızsa Selenium kullan (yavaş ama güvenilir)
        print("Selenium ile deneniyor...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get(course_url)
        time.sleep(3)  # Daha kısa bekleme
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        print("Selenium ile HTML alındı, bölümler aranıyor...")
        
        sections = []
        span_elements = soup.find_all('span', class_='font-medium text-base')
        print(f"font-medium text-base ile {len(span_elements)} span bulundu")
        
        for span in span_elements:
            text = span.get_text().strip()
            if re.match(r'^\d+\.', text):
                sections.append(text)
                print(f"Bölüm bulundu: {text}")
        
        driver.quit()
        
        if sections:
            print(f"Selenium başarılı! Toplam {len(sections)} bölüm bulundu")
            return sections
        else:
            print("Hiç bölüm bulunamadı, demo veriler döndürülüyor")
            if 'git' in course_url.lower():
                return ["1. Git Temelleri", "2. Repository Yönetimi", "3. Branch ve Merge", "4. GitHub Kullanımı", "5. İleri Git Teknikleri"]
            elif 'python' in course_url.lower():
                return ["1. Python Giriş", "2. Temel Syntax", "3. Veri Yapıları", "4. Fonksiyonlar", "5. OOP"]
            else:
                return ["1. Tanıtım", "2. Temel Kavramlar", "3. Uygulama", "4. Test", "5. Proje"]
            
    except Exception as e:
        print(f"Scraping hatası: {e}")
        if 'git' in course_url.lower():
            return ["1. Git Temelleri", "2. Repository Yönetimi", "3. Branch ve Merge", "4. GitHub Kullanımı", "5. İleri Git Teknikleri"]
        else:
            return ["1. Tanıtım", "2. Temel Kavramlar", "3. Uygulama", "4. Test", "5. Proje"]

def create_dynamic_roadmap(course_title, course_link, sections):
    """Dinamik yol haritası oluştur"""
    roadmap_steps = []
    
    for i, section in enumerate(sections, 1):
        step = {
            'id': i,
            'title': section,
            'description': f"{course_title} - {section}",
            'link': course_link,
            'status': 'current' if i == 1 else 'locked',
            'icon': '📚'
        }
        roadmap_steps.append(step)
    
    return roadmap_steps

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def loginIndex():
    return render_template('login-register.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/roadmap')
def roadmap():
    return render_template('roadmap.html')

@app.route('/tournament')
def tournament():
    return render_template('tournament.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/tournament-admin')
def tournament_admin():
    return render_template('tournament-admin.html')

@app.route('/battle')
def battle():
    return render_template('battle.html')



@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Veri doğrulama
        required_fields = ['first_name', 'last_name', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} alanı gereklidir'}), 400
        
        # Email formatı kontrolü
        if '@' not in data['email']:
            return jsonify({'error': 'Geçerli bir email adresi giriniz'}), 400
        
        # Şifre uzunluğu kontrolü
        if len(data['password']) < 6:
            return jsonify({'error': 'Şifre en az 6 karakter olmalıdır'}), 400
        
        # Veritabanına kaydet
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Email kontrolü
        cursor.execute('SELECT id FROM users WHERE email = ?', (data['email'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Bu email adresi zaten kayıtlı'}), 400
        
        # Şifreyi hashle
        password_hash = generate_password_hash(data['password'])
        
        # Kullanıcıyı kaydet
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, password_hash)
            VALUES (?, ?, ?, ?)
        ''', (data['first_name'], data['last_name'], data['email'], password_hash))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        # JWT token oluştur
        token = jwt.encode({
            'user_id': user_id,
            'email': data['email'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'success': True,
            'message': 'Kayıt başarılı!',
            'token': token,
            'user': {
                'id': user_id,
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email']
            }
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Veri doğrulama
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email ve şifre gereklidir'}), 400
        
        # Kullanıcıyı bul
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, first_name, last_name, email, password_hash 
            FROM users WHERE email = ?
        ''', (data['email'],))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'Email veya şifre hatalı'}), 401
        
        # Şifre kontrolü
        if not check_password_hash(user[4], data['password']):
            conn.close()
            return jsonify({'error': 'Email veya şifre hatalı'}), 401
        
        # Son giriş zamanını güncelle
        cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (user[0],))
        
        conn.commit()
        conn.close()
        
        # JWT token oluştur
        token = jwt.encode({
            'user_id': user[0],
            'email': user[3],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'success': True,
            'message': 'Giriş başarılı!',
            'token': token,
            'user': {
                'id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'email': user[3]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/profile', methods=['GET'])
def get_profile():
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        # Kullanıcı bilgilerini getir
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, first_name, last_name, email, created_at, last_login
            FROM users WHERE id = ?
        ''', (payload['user_id'],))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
        
        return jsonify({
            'user': {
                'id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'email': user[3],
                'created_at': user[4],
                'last_login': user[5]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Tüm kullanıcıları listele (admin için)"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, first_name, last_name, email, created_at, last_login
            FROM users ORDER BY created_at DESC
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        user_list = []
        for user in users:
            user_list.append({
                'id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'email': user[3],
                'created_at': user[4],
                'last_login': user[5]
            })
        
        return jsonify({'users': user_list}), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/analyze-profile', methods=['POST'])
def analyze_profile():
    """Kullanıcı profilini analiz et ve kurs önerisi yap"""
    try:
        print("=== ANALYZE PROFILE API CALLED ===")
        
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            print("ERROR: Token missing or invalid format")
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            print(f"Token decoded successfully for user_id: {payload['user_id']}")
        except jwt.ExpiredSignatureError:
            print("ERROR: Token expired")
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            print("ERROR: Invalid token")
            return jsonify({'error': 'Geçersiz token'}), 401
        
        data = request.get_json()
        print(f"Received data: {data}")
        
        # Veri doğrulama
        required_fields = ['skill', 'goal', 'level', 'time']
        for field in required_fields:
            if not data.get(field):
                print(f"ERROR: Missing field: {field}")
                return jsonify({'error': f'{field} alanı gereklidir'}), 400
        
        print("Data validation passed")
        
        # Profil analizi
        print("Starting profile analysis...")
        profile = analyze_user_profile(data)
        if not profile:
            print("ERROR: Profile analysis failed")
            return jsonify({'error': 'Profil analizi başarısız'}), 500
        
        print(f"Profile created: {profile}")
        
        # BTK kurs arama
        search_query = f"{data['skill']} {profile['seviye']} seviye kurs"
        print(f"Searching for: {search_query}")
        courses = search_btk_courses(search_query)
        print(f"Found {len(courses)} courses")
        
        # Eğer sonuç bulunamazsa, daha genel arama yap
        if not courses:
            print("No courses found, trying general search...")
            search_query = f"{data['skill']} programlama eğitim"
            courses = search_btk_courses(search_query)
            print(f"General search found {len(courses)} courses")
        
        # En uygun kursu seç
        best_course = recommend_best_course(profile, courses, data['skill'])
        print(f"Best course: {best_course}")
        
        # Profili veritabanına kaydet
        print("Saving profile to database...")
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_profiles (user_id, skill, goal, level, time_commitment, learning_style)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (payload['user_id'], data['skill'], data['goal'], data['level'], data['time'], 'Genel öğrenme'))
        
        conn.commit()
        conn.close()
        print("Profile saved to database")
        
        response_data = {
            'success': True,
            'profile': profile,
            'recommended_course': best_course,
            'total_courses_found': len(courses)
        }
        
        print(f"Sending response: {response_data}")
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"ERROR in analyze_profile: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/add-course-to-roadmap', methods=['POST'])
def add_course_to_roadmap():
    """Kursu kullanıcının yol haritasına ekle"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        data = request.get_json()
        
        # Veri doğrulama
        required_fields = ['course_title', 'course_link', 'course_description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} alanı gereklidir'}), 400
        
        # BTK Akademi'den kurs bölümlerini çek
        print(f"BTK Akademi'den bölümler çekiliyor: {data['course_link']}")
        sections = scrape_btk_course_sections(data['course_link'])
        
        # Dinamik yol haritası oluştur
        roadmap_steps = create_dynamic_roadmap(data['course_title'], data['course_link'], sections)
        
        # Kursu veritabanına kaydet
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_courses (user_id, course_title, course_link, course_description, roadmap_sections)
            VALUES (?, ?, ?, ?, ?)
        ''', (payload['user_id'], data['course_title'], data['course_link'], data['course_description'], json.dumps(roadmap_steps)))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Kurs yol haritasına eklendi'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/get-user-roadmap', methods=['GET'])
def get_user_roadmap():
    """Kullanıcının yol haritasını getir"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        # Kullanıcının profili ve kurslarını getir
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Profil bilgileri
        cursor.execute('''
            SELECT skill, goal, level, time_commitment, learning_style, created_at
            FROM user_profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
        ''', (payload['user_id'],))
        
        profile = cursor.fetchone()
        
        # Kurslar
        cursor.execute('''
            SELECT course_title, course_link, course_description, roadmap_sections, added_at
            FROM user_courses WHERE user_id = ? ORDER BY added_at DESC
        ''', (payload['user_id'],))
        
        courses = cursor.fetchall()
        conn.close()
        
        roadmap_data = {
            'profile': None,
            'courses': []
        }
        
        if profile:
            roadmap_data['profile'] = {
                'skill': profile[0],
                'goal': profile[1],
                'level': profile[2],
                'time_commitment': profile[3],
                'learning_style': profile[4],
                'created_at': profile[5]
            }
        
        for course in courses:
            roadmap_steps = []
            if course[3]:  # roadmap_sections varsa
                try:
                    roadmap_steps = json.loads(course[3])
                except:
                    roadmap_steps = []
            
            roadmap_data['courses'].append({
                'title': course[0],
                'link': course[1],
                'description': course[2],
                'roadmap_steps': roadmap_steps,
                'added_at': course[4]
            })
        
        return jsonify(roadmap_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

def clean_and_fix_json(json_text):
    """JSON metnini temizler ve eksik kapanan tırnak işaretlerini düzeltir"""
    try:
        # Önce normal JSON parse dene
        json.loads(json_text)
        return json_text
    except json.JSONDecodeError as e:
        print(f"JSON temizleme gerekli: {e}")
        
        # Eksik kapanan tırnak işaretlerini düzelt
        lines = json_text.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Satırda açık tırnak işareti varsa ve kapanmamışsa
            if '"' in line:
                quote_count = line.count('"')
                if quote_count % 2 != 0:  # Tek sayıda tırnak işareti varsa
                    # Satırın sonuna tırnak işareti ekle
                    if not line.strip().endswith('"'):
                        line = line.rstrip() + '"'
                    # Eğer satır virgülle bitmiyorsa ve sonraki satır yoksa virgül ekle
                    if not line.strip().endswith(',') and not line.strip().endswith(']') and not line.strip().endswith('}'):
                        line = line.rstrip() + ','
            
            fixed_lines.append(line)
        
        # Eksik kapanan parantezleri düzelt
        fixed_text = '\n'.join(fixed_lines)
        
        # Eğer JSON hala tamamlanmamışsa, basit bir yapı oluştur
        if not fixed_text.strip().endswith('}'):
            # Son soruyu tamamla
            if not fixed_text.strip().endswith(']'):
                fixed_text = fixed_text.rstrip().rstrip(',') + ']'
            if not fixed_text.strip().endswith('}'):
                fixed_text = fixed_text.rstrip().rstrip(',') + '}'
        
        return fixed_text
        
    except Exception as e:
        print(f"JSON temizleme hatası: {e}")
        return json_text

def extract_questions_from_text(text, topic, max_questions=15):
    """AI yanıtından soruları manuel olarak çıkarır"""
    try:
        questions = []
        lines = text.split('\n')
        
        current_question = None
        current_options = []
        option_count = 0
        
        for line in lines:
            line = line.strip()
            
            # Soru satırını bul
            if '"question"' in line or 'question' in line.lower():
                # Önceki soruyu kaydet
                if current_question and len(current_options) == 4:
                    questions.append({
                        "question": current_question,
                        "options": current_options,
                        "correct_option": "A"  # Varsayılan
                    })
                
                # Yeni soru başlat
                current_question = extract_quoted_text(line)
                current_options = []
                option_count = 0
                
            # Seçenek satırını bul
            elif '"options"' in line or 'options' in line.lower():
                continue
            elif line.startswith('"') and ('"' in line[1:]) and option_count < 4:
                option_text = extract_quoted_text(line)
                if option_text:
                    current_options.append(option_text)
                    option_count += 1
        
        # Son soruyu ekle
        if current_question and len(current_options) == 4:
            questions.append({
                "question": current_question,
                "options": current_options,
                "correct_option": "A"  # Varsayılan
            })
        
        # Soru sayısını sınırla
        if len(questions) > max_questions:
            questions = questions[:max_questions]
        
        return questions
        
    except Exception as e:
        print(f"Soru çıkarma hatası: {e}")
        return []

def extract_quoted_text(line):
    """Satırdan tırnak işaretleri arasındaki metni çıkarır"""
    try:
        # İlk tırnak işaretini bul
        start = line.find('"')
        if start == -1:
            return None
        
        # İkinci tırnak işaretini bul
        end = line.find('"', start + 1)
        if end == -1:
            return None
        
        return line[start + 1:end]
    except:
        return None

# Turnuva API'leri
def generate_questions_with_gemini(topic, question_count=15):
    """Gemini API ile soru üret"""
    try:
        # Gemini API anahtarını kontrol et
        if GEMINI_API_KEY == "your_gemini_api_key_here":
            print("UYARI: Gemini API anahtarı ayarlanmamış. Lütfen GEMINI_API_KEY environment variable'ını ayarlayın.")
            # Demo yerine basit hata mesajı döndür
            return [{
                "question": f"Gemini API anahtarı ayarlanmamış. {topic} için sorular üretilemedi.",
                "options": ["API anahtarı gerekli", "Lütfen ayarlayın", "Environment variable", "GEMINI_API_KEY"],
                "correct_option": "A"
            }]
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
{topic} konusu için {question_count} adet çoktan seçmeli soru üret. 
Her soru için 4 şık olmalı (A, B, C, D) ve sadece bir doğru cevap olmalı.

ÖNEMLİ: Yanıtı SADECE JSON formatında ver, başka hiçbir metin ekleme:

{{
    "questions": [
        {{
            "question": "Soru metni",
            "options": ["A şıkkı", "B şıkkı", "C şıkkı", "D şıkkı"],
            "correct_option": "A"
        }}
    ]
}}

KURALLAR:
- Sorular Türkçe olmalı ve tamamen "{topic}" konusu ile ilgili olmalı
- Soruların zorluk seviyesi orta düzeyde olsun
- Her soru net, anlaşılır ve tek doğru cevabı olsun
- Yanıt sadece JSON olmalı, markdown kod bloğu kullanma
- Başka açıklama ekleme, sadece JSON döndür
- Tüm tırnak işaretlerinin doğru kapatıldığından emin ol
- JSON formatının tam ve geçerli olduğundan emin ol
- Her soru için 4 seçenek olduğundan emin ol
- correct_option değeri A, B, C veya D olmalı
"""
        
        response = model.generate_content(prompt)
        
        # JSON parse et
        import json
        import re
        
        try:
            response_text = response.text.strip()
            
            # Markdown kod bloğu varsa temizle
            if response_text.startswith('```json'):
                # ```json ile başlayıp ``` ile bitenleri bul
                json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1).strip()
                else:
                    # ```json varsa ama ``` yoksa, ```json'dan sonrasını al
                    response_text = response_text[7:].strip()  # ```json kısmını çıkar
            elif response_text.startswith('```'):
                # Sadece ``` ile başlıyorsa
                json_match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1).strip()
                else:
                    response_text = response_text[3:].strip()  # ``` kısmını çıkar
            
            # JSON'u temizle ve tamamla
            response_text = clean_and_fix_json(response_text)
            
            # JSON parse et
            result = json.loads(response_text)
            questions = result.get("questions", [])
            
            # Soru sayısını kontrol et ve gerekirse kırp veya tamamla
            if len(questions) > question_count:
                questions = questions[:question_count]
            elif len(questions) < question_count:
                print(f"Uyarı: İstenen {question_count} soru yerine {len(questions)} soru üretildi")
            
            return questions
            
        except json.JSONDecodeError as e:
            print(f"JSON parse hatası: {e}")
            print(f"Temizlenmiş AI yanıtı: {response_text[:500]}...")
            print(f"Orijinal AI yanıtı: {response.text[:500]}...")
            
            # Son bir deneme: Manuel JSON oluştur
            try:
                # AI yanıtından soruları çıkarmaya çalış
                questions = extract_questions_from_text(response.text, topic, question_count)
                if questions:
                    print(f"Manuel çıkarma başarılı: {len(questions)} soru bulundu")
                    return questions
            except Exception as extract_error:
                print(f"Manuel çıkarma hatası: {extract_error}")
            
            # JSON parse edilemezse basit bir soru döndür
            return [{
                "question": f"{topic} konusunda JSON parse hatası oluştu. Lütfen tekrar deneyin.",
                "options": ["API yanıtı hatalı", "JSON formatı bozuk", "Tekrar deneyin", "Sistem hatası"],
                "correct_option": "C"
            }]
            
    except Exception as e:
        print(f"Gemini API hatası: {e}")
        return [{
            "question": f"{topic} için soru üretilirken hata oluştu: {str(e)}",
            "options": ["API hatası", "Bağlantı sorunu", "Tekrar deneyin", "Sistem hatası"],
            "correct_option": "C"
        }]



@app.route('/api/generate-questions', methods=['POST'])
def generate_questions():
    """AI ile soru üret"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        data = request.get_json()
        
        # Veri doğrulama
        if not data.get('content'):
            return jsonify({'error': 'Turnuva içeriği gereklidir'}), 400
        
        # Soruları üret
        questions = generate_questions_with_gemini(data['content'], data.get('question_count', 15))
        
        return jsonify({
            'success': True,
            'questions': questions
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/save-tournament', methods=['POST'])
def save_tournament():
    """Turnuvayı kaydet"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        data = request.get_json()
        
        # Veri doğrulama
        required_fields = ['title', 'content', 'start_time', 'end_time', 'questions']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} alanı gereklidir'}), 400
        
        # Veritabanına kaydet
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuvayı kaydet
        cursor.execute('''
            INSERT INTO tournaments (title, content, question_count, duration_minutes, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        ''', (data['title'], data['content'], data['question_count'], data['duration_minutes'], data['start_time'], data['end_time']))
        
        tournament_id = cursor.lastrowid
        
        # Soruları kaydet
        for question in data['questions']:
            cursor.execute('''
                INSERT INTO questions (tournament_id, question, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                tournament_id,
                question['question'],
                question['options'][0],
                question['options'][1],
                question['options'][2],
                question['options'][3],
                question['correct_option']
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Turnuva başarıyla kaydedildi',
            'tournament_id': tournament_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/tournaments', methods=['GET'])
def get_tournaments():
    """Aktif turnuvaları listele"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Önce status'u NULL olan turnuvaları 'active' yap
        cursor.execute('''
            UPDATE tournaments 
            SET status = 'active' 
            WHERE status IS NULL OR status = ''
        ''')
        conn.commit()
        
        cursor.execute('''
            SELECT id, title, content, question_count, duration_minutes, start_time, end_time, status, created_at
            FROM tournaments 
            WHERE status = 'active'
            ORDER BY created_at DESC
        ''')
        
        tournaments = cursor.fetchall()
        conn.close()
        
        tournament_list = []
        for tournament in tournaments:
            tournament_list.append({
                'id': tournament[0],
                'title': tournament[1],
                'content': tournament[2],
                'question_count': tournament[3],
                'duration_minutes': tournament[4],
                'start_time': tournament[5],
                'end_time': tournament[6],
                'status': tournament[7],
                'created_at': tournament[8]
            })
        
        return jsonify({
            'success': True,
            'tournaments': tournament_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/join-tournament', methods=['POST'])
def join_tournament():
    """Turnuvaya katıl"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        data = request.get_json()
        
        if not data.get('tournament_id'):
            return jsonify({'error': 'Turnuva ID gereklidir'}), 400
        
        # Veritabanına kaydet
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuva zaman kontrolü
        cursor.execute('''
            SELECT start_time, end_time, status FROM tournaments WHERE id = ?
        ''', (data['tournament_id'],))
        
        tournament = cursor.fetchone()
        if not tournament:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        # Zaman kontrolü (daha esnek)
        try:
            start_time = datetime.datetime.fromisoformat(tournament[0].replace('Z', '+00:00'))
            end_time = datetime.datetime.fromisoformat(tournament[1].replace('Z', '+00:00'))
            current_time = datetime.datetime.now()
            
            # Turnuva bitmişse katılıma izin verme
            if current_time > end_time:
                conn.close()
                return jsonify({'error': 'Turnuva süresi dolmuş'}), 400
        except:
            # Zaman formatı sorunluysa katılıma izin ver
            pass
        
        # Daha önce katılmış mı kontrol et
        cursor.execute('''
            SELECT id FROM tournament_participants 
            WHERE user_id = ? AND tournament_id = ?
        ''', (payload['user_id'], data['tournament_id']))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Bu turnuvaya zaten katıldınız'}), 400
        
        # Katılımı kaydet
        cursor.execute('''
            INSERT INTO tournament_participants (user_id, tournament_id, total_questions, correct_answers)
            VALUES (?, ?, 0, 0)
        ''', (payload['user_id'], data['tournament_id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Turnuvaya başarıyla katıldınız'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/tournament-questions/<int:tournament_id>', methods=['GET'])
def get_tournament_questions(tournament_id):
    """Turnuva sorularını getir"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuva bilgilerini al
        cursor.execute('''
            SELECT title, content, start_time, end_time, status
            FROM tournaments WHERE id = ?
        ''', (tournament_id,))
        
        tournament = cursor.fetchone()
        if not tournament:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        # Soruları al
        cursor.execute('''
            SELECT id, question, option_a, option_b, option_c, option_d
            FROM questions WHERE tournament_id = ?
            ORDER BY id
        ''', (tournament_id,))
        
        questions = cursor.fetchall()
        conn.close()
        
        question_list = []
        for question in questions:
            question_list.append({
                'id': question[0],
                'question': question[1],
                'options': [question[2], question[3], question[4], question[5]]
            })
        
        return jsonify({
            'success': True,
            'tournament': {
                'id': tournament_id,
                'title': tournament[0],
                'content': tournament[1],
                'start_time': tournament[2],
                'end_time': tournament[3],
                'status': tournament[4]
            },
            'questions': question_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/answer-question', methods=['POST'])
def answer_question():
    """Soru cevapla"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        data = request.get_json()
        
        required_fields = ['tournament_id', 'question_id', 'selected_option']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} alanı gereklidir'}), 400
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuva zaman kontrolü
        cursor.execute('''
            SELECT end_time FROM tournaments WHERE id = ?
        ''', (data['tournament_id'],))
        
        tournament = cursor.fetchone()
        if not tournament:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        end_time = datetime.datetime.fromisoformat(tournament[0].replace('Z', '+00:00'))
        current_time = datetime.datetime.now()
        
        # Turnuva bitmişse cevap vermeye izin verme
        if current_time > end_time:
            conn.close()
            return jsonify({'error': 'Turnuva süresi dolmuş'}), 400
        
        # Daha önce bu soruyu cevaplamış mı kontrol et
        cursor.execute('''
            SELECT id FROM user_answers 
            WHERE user_id = ? AND tournament_id = ? AND question_id = ?
        ''', (payload['user_id'], data['tournament_id'], data['question_id']))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Bu soruyu zaten cevapladınız'}), 400
        
        # Doğru cevabı kontrol et
        cursor.execute('''
            SELECT correct_option FROM questions WHERE id = ?
        ''', (data['question_id'],))
        
        question = cursor.fetchone()
        if not question:
            conn.close()
            return jsonify({'error': 'Soru bulunamadı'}), 404
        
        is_correct = data['selected_option'] == question[0]
        
        # Cevabı kaydet
        cursor.execute('''
            INSERT INTO user_answers (user_id, tournament_id, question_id, selected_option, is_correct)
            VALUES (?, ?, ?, ?, ?)
        ''', (payload['user_id'], data['tournament_id'], data['question_id'], data['selected_option'], is_correct))
        
        # Skoru güncelle
        cursor.execute('''
            UPDATE tournament_participants 
            SET total_questions = total_questions + 1,
                correct_answers = correct_answers + ?
            WHERE user_id = ? AND tournament_id = ?
        ''', (1 if is_correct else 0, payload['user_id'], data['tournament_id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'is_correct': is_correct,
            'correct_answer': question[0]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/complete-tournament', methods=['POST'])
def complete_tournament():
    """Turnuvayı tamamla ve final skoru hesapla"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        data = request.get_json()
        
        if not data.get('tournament_id'):
            return jsonify({'error': 'Turnuva ID gereklidir'}), 400
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Katılım bilgilerini al
        cursor.execute('''
            SELECT total_questions, correct_answers, completed_at
            FROM tournament_participants 
            WHERE user_id = ? AND tournament_id = ?
        ''', (payload['user_id'], data['tournament_id']))
        
        participant = cursor.fetchone()
        if not participant:
            conn.close()
            return jsonify({'error': 'Bu turnuvaya katılmadınız'}), 404
        
        if participant[2]:  # completed_at varsa
            conn.close()
            return jsonify({'error': 'Bu turnuvayı zaten tamamladınız'}), 400
        
        # Final skoru hesapla
        total_questions = participant[0]
        correct_answers = participant[1]
        
        if total_questions == 0:
            conn.close()
            return jsonify({'error': 'Hiç soru cevaplanmamış'}), 400
        
        final_score = round((correct_answers / total_questions) * 100)
        
        # Turnuvayı tamamla
        cursor.execute('''
            UPDATE tournament_participants 
            SET completed_at = CURRENT_TIMESTAMP,
                total_score = ?
            WHERE user_id = ? AND tournament_id = ?
        ''', (final_score, payload['user_id'], data['tournament_id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'final_score': final_score,
            'total_questions': total_questions,
            'correct_answers': correct_answers
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/tournament-results/<int:tournament_id>', methods=['GET'])
def get_tournament_results(tournament_id):
    """Turnuva sonuçlarını getir"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuva bilgileri
        cursor.execute('''
            SELECT title, start_time, end_time, status
            FROM tournaments WHERE id = ?
        ''', (tournament_id,))
        
        tournament = cursor.fetchone()
        if not tournament:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        # Katılımcı sonuçları
        cursor.execute('''
            SELECT u.first_name, u.last_name, tp.total_score, tp.total_questions, 
                   tp.correct_answers, tp.completed_at
            FROM tournament_participants tp
            JOIN users u ON tp.user_id = u.id
            WHERE tp.tournament_id = ? AND tp.completed_at IS NOT NULL
            ORDER BY tp.total_score DESC, tp.completed_at ASC
        ''', (tournament_id,))
        
        participants = cursor.fetchall()
        conn.close()
        
        participants_list = []
        for i, participant in enumerate(participants):
            # Tamamlama süresini hesapla
            completion_time = "N/A"
            if participant[5]:  # completed_at varsa
                try:
                    completed_time = datetime.datetime.fromisoformat(participant[5].replace('Z', '+00:00'))
                    # Basit süre hesaplama (gerçek uygulamada daha detaylı olabilir)
                    completion_time = "Tamamlandı"
                except:
                    completion_time = "N/A"
            
            participants_list.append({
                'rank': i + 1,
                'username': f"{participant[0]} {participant[1]}",
                'total_score': participant[2] or 0,
                'total_questions': participant[3] or 0,
                'correct_answers': participant[4] or 0,
                'completion_time': completion_time
            })
        
        return jsonify({
            'success': True,
            'tournament': {
                'id': tournament_id,
                'title': tournament[0],
                'start_time': tournament[1],
                'end_time': tournament[2],
                'status': tournament[3]
            },
            'participants': participants_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/user-tournament-status/<int:tournament_id>', methods=['GET'])
def get_user_tournament_status(tournament_id):
    """Kullanıcının turnuva durumunu getir"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuva bilgileri
        cursor.execute('''
            SELECT title, start_time, end_time, status
            FROM tournaments WHERE id = ?
        ''', (tournament_id,))
        
        tournament = cursor.fetchone()
        if not tournament:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        # Kullanıcı katılım durumu
        cursor.execute('''
            SELECT total_score, total_questions, correct_answers, completed_at, joined_at
            FROM tournament_participants 
            WHERE user_id = ? AND tournament_id = ?
        ''', (payload['user_id'], tournament_id))
        
        participant = cursor.fetchone()
        conn.close()
        
        current_time = datetime.datetime.now()
        
        # Zaman kontrolü (daha esnek)
        try:
            start_time = datetime.datetime.fromisoformat(tournament[1].replace('Z', '+00:00'))
            end_time = datetime.datetime.fromisoformat(tournament[2].replace('Z', '+00:00'))
            
            status = {
                'tournament_id': tournament_id,
                'title': tournament[0],
                'start_time': tournament[1],
                'end_time': tournament[2],
                'status': tournament[3],
                'current_time': current_time.isoformat(),
                'has_joined': participant is not None,
                'can_join': start_time <= current_time <= end_time,  # Hem başlangıç hem bitiş zamanını kontrol et
                'can_participate': participant is not None and start_time <= current_time <= end_time,
                'is_completed': participant and participant[3] is not None
            }
        except:
            # Zaman formatı sorunluysa varsayılan değerler
            status = {
                'tournament_id': tournament_id,
                'title': tournament[0],
                'start_time': tournament[1],
                'end_time': tournament[2],
                'status': tournament[3],
                'current_time': current_time.isoformat(),
                'has_joined': participant is not None,
                'can_join': True,  # Varsayılan olarak katılıma izin ver
                'can_participate': participant is not None,
                'is_completed': participant and participant[3] is not None
            }
        
        if participant:
            status.update({
                'total_score': participant[0],
                'total_questions': participant[1],
                'correct_answers': participant[2],
                'completed_at': participant[3],
                'joined_at': participant[4]
            })
        
        return jsonify({
            'success': True,
            'status': status
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/tournaments/<int:tournament_id>', methods=['GET'])
def get_tournament(tournament_id):
    """Turnuva detaylarını getir"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuva bilgileri
        cursor.execute('''
            SELECT id, title, content, question_count, duration_minutes, start_time, end_time, status
            FROM tournaments WHERE id = ?
        ''', (tournament_id,))
        
        tournament = cursor.fetchone()
        if not tournament:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        # Turnuva soruları
        cursor.execute('''
            SELECT id, question, option_a, option_b, option_c, option_d, correct_option
            FROM questions WHERE tournament_id = ?
            ORDER BY id
        ''', (tournament_id,))
        
        questions = cursor.fetchall()
        conn.close()
        
        questions_list = []
        for question in questions:
            questions_list.append({
                'id': question[0],
                'question': question[1],
                'options': [question[2], question[3], question[4], question[5]],
                'correct_option': question[6]
            })
        
        return jsonify({
            'success': True,
            'tournament': {
                'id': tournament[0],
                'title': tournament[1],
                'content': tournament[2],
                'question_count': tournament[3],
                'duration_minutes': tournament[4],
                'start_time': tournament[5],
                'end_time': tournament[6],
                'status': tournament[7],
                'questions': questions_list
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/update-tournament/<int:tournament_id>', methods=['PUT'])
def update_tournament(tournament_id):
    """Turnuvayı güncelle"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        data = request.get_json()
        
        required_fields = ['title', 'content', 'start_time', 'end_time', 'questions']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} alanı gereklidir'}), 400
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuvayı güncelle
        cursor.execute('''
            UPDATE tournaments 
            SET title = ?, content = ?, start_time = ?, end_time = ?
            WHERE id = ?
        ''', (data['title'], data['content'], data['start_time'], data['end_time'], tournament_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        # Eski soruları sil
        cursor.execute('DELETE FROM questions WHERE tournament_id = ?', (tournament_id,))
        
        # Yeni soruları ekle
        for question in data['questions']:
            cursor.execute('''
                INSERT INTO questions (tournament_id, question, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (tournament_id, question['question'], question['options'][0], question['options'][1], 
                  question['options'][2], question['options'][3], question['correct_option']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Turnuva başarıyla güncellendi'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/tournaments/<int:tournament_id>', methods=['DELETE'])
def delete_tournament(tournament_id):
    """Turnuvayı sil"""
    try:
        # Token kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token gereklidir'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token süresi dolmuş'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Geçersiz token'}), 401
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuvayı sil
        cursor.execute('DELETE FROM tournaments WHERE id = ?', (tournament_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        # İlgili soruları da sil
        cursor.execute('DELETE FROM questions WHERE tournament_id = ?', (tournament_id,))
        
        # İlgili katılımları da sil
        cursor.execute('DELETE FROM tournament_participants WHERE tournament_id = ?', (tournament_id,))
        
        # İlgili cevapları da sil
        cursor.execute('DELETE FROM user_answers WHERE tournament_id = ?', (tournament_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Turnuva başarıyla silindi'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/tournament-participant-count/<int:tournament_id>', methods=['GET'])
def get_tournament_participant_count(tournament_id):
    """Turnuvayı tamamlayan kişi sayısını döndür"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuvayı tamamlayan kişi sayısını al (completed_at NULL değil)
        cursor.execute('''
            SELECT COUNT(*) 
            FROM tournament_participants 
            WHERE tournament_id = ? AND completed_at IS NOT NULL
        ''', (tournament_id,))
        
        participant_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'participant_count': participant_count
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/leaderboard/<int:tournament_id>', methods=['GET'])
def get_leaderboard(tournament_id):
    """Turnuva sıralamasını doğru cevap sayısına göre döndür"""
    try:
        # Token kontrolü (opsiyonel - genel sıralama için)
        auth_header = request.headers.get('Authorization')
        current_user_id = None
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                current_user_id = payload['user_id']
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass  # Token geçersizse sadece genel sıralama göster
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuvayı tamamlayan kullanıcıları doğru cevap sayısına göre sırala
        cursor.execute('''
            SELECT 
                tp.user_id,
                u.first_name,
                u.last_name,
                tp.correct_answers,
                tp.total_questions,
                tp.total_score,
                tp.completed_at
            FROM tournament_participants tp
            JOIN users u ON tp.user_id = u.id
            WHERE tp.tournament_id = ? AND tp.completed_at IS NOT NULL
            ORDER BY tp.correct_answers DESC, tp.completed_at ASC
            LIMIT 10
        ''', (tournament_id,))
        
        participants = cursor.fetchall()
        
        leaderboard = []
        for i, participant in enumerate(participants):
            user_id, first_name, last_name, correct_answers, total_questions, total_score, completed_at = participant
            
            # Kullanıcı adını oluştur
            username = f"{first_name} {last_name}"
            
            # Sıralama pozisyonu
            rank = i + 1
            
            # Mevcut kullanıcı mı kontrol et
            is_current_user = current_user_id == user_id
            
            leaderboard.append({
                'rank': rank,
                'user_id': user_id,
                'username': username,
                'correct_answers': correct_answers,
                'total_questions': total_questions,
                'total_score': total_score,
                'completion_time': completed_at,
                'is_current_user': is_current_user
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'tournament_id': tournament_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/global-leaderboard', methods=['GET'])
def get_global_leaderboard():
    """Genel sıralama - tüm turnuvalardaki toplam performansa göre"""
    try:
        # Token kontrolü (opsiyonel)
        auth_header = request.headers.get('Authorization')
        current_user_id = None
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                current_user_id = payload['user_id']
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Tüm turnuvalardaki toplam performansı hesapla
        cursor.execute('''
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                SUM(tp.correct_answers) as total_correct,
                SUM(tp.total_questions) as total_questions,
                AVG(tp.total_score) as avg_score,
                COUNT(tp.id) as tournaments_completed
            FROM users u
            JOIN tournament_participants tp ON u.id = tp.user_id
            WHERE tp.completed_at IS NOT NULL
            GROUP BY u.id, u.first_name, u.last_name
            HAVING total_correct > 0
            ORDER BY total_correct DESC, avg_score DESC
            LIMIT 10
        ''')
        
        participants = cursor.fetchall()
        
        leaderboard = []
        for i, participant in enumerate(participants):
            user_id, first_name, last_name, total_correct, total_questions, avg_score, tournaments_completed = participant
            
            username = f"{first_name} {last_name}"
            rank = i + 1
            is_current_user = current_user_id == user_id
            
            leaderboard.append({
                'rank': rank,
                'user_id': user_id,
                'username': username,
                'total_correct_answers': total_correct,
                'total_questions': total_questions,
                'average_score': round(avg_score, 1),
                'tournaments_completed': tournaments_completed,
                'is_current_user': is_current_user
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/tournament-stats/<int:tournament_id>', methods=['GET'])
def get_tournament_stats(tournament_id):
    """Turnuva istatistiklerini döndür"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Turnuva bilgilerini al
        cursor.execute('''
            SELECT start_time, end_time, status
            FROM tournaments
            WHERE id = ?
        ''', (tournament_id,))
        
        tournament = cursor.fetchone()
        if not tournament:
            conn.close()
            return jsonify({'error': 'Turnuva bulunamadı'}), 404
        
        start_time, end_time, status = tournament
        
        # Toplam katılımcı sayısı
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id)
            FROM tournament_participants
            WHERE tournament_id = ?
        ''', (tournament_id,))
        
        total_participants = cursor.fetchone()[0]
        
        # Tamamlanan turnuvaların istatistikleri
        cursor.execute('''
            SELECT 
                COUNT(*) as completed_count,
                AVG(total_score) as avg_score,
                MAX(total_score) as max_score,
                AVG(correct_answers) as avg_correct,
                MAX(correct_answers) as max_correct
            FROM tournament_participants
            WHERE tournament_id = ? AND completed_at IS NOT NULL
        ''', (tournament_id,))
        
        stats = cursor.fetchone()
        completed_count, avg_score, max_score, avg_correct, max_correct = stats
        
        # Ortalama skor hesapla
        average_score = round(avg_score, 1) if avg_score else 0
        highest_score = round(max_score, 1) if max_score else 0
        
        # Kalan süre hesapla
        now = datetime.datetime.now()
        end_datetime = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        if end_datetime > now:
            time_left = end_datetime - now
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            seconds = int(time_left.total_seconds() % 60)
            remaining_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            remaining_time = "00:00:00"
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_participants': total_participants,
                'completed_participants': completed_count,
                'average_score': average_score,
                'highest_score': highest_score,
                'average_correct_answers': round(avg_correct, 1) if avg_correct else 0,
                'max_correct_answers': max_correct if max_correct else 0,
                'remaining_time': remaining_time,
                'tournament_status': status
            },
            'tournament_id': tournament_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/weekly-tournament-calendar', methods=['GET'])
def get_weekly_tournament_calendar():
    """Haftalık turnuva takvimini döndür"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Bu haftanın başlangıç ve bitiş tarihlerini hesapla
        now = datetime.datetime.now()
        start_of_week = now - datetime.timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + datetime.timedelta(days=7)
        
        # Haftalık günler
        days_of_week = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
        
        weekly_calendar = []
        
        for i in range(7):
            current_date = start_of_week + datetime.timedelta(days=i)
            day_name = days_of_week[i]
            
            # Bu gün için turnuva var mı kontrol et
            cursor.execute('''
                SELECT id, title, status
                FROM tournaments
                WHERE DATE(start_time) = DATE(?)
                ORDER BY start_time ASC
                LIMIT 1
            ''', (current_date.strftime('%Y-%m-%d'),))
            
            tournament = cursor.fetchone()
            
            if tournament:
                tournament_id, tournament_title, tournament_status = tournament
                
                # Bu turnuvanın kazananını bul
                cursor.execute('''
                    SELECT u.first_name, u.last_name, tp.correct_answers, tp.total_score
                    FROM tournament_participants tp
                    JOIN users u ON tp.user_id = u.id
                    WHERE tp.tournament_id = ? AND tp.completed_at IS NOT NULL
                    ORDER BY tp.correct_answers DESC, tp.completed_at ASC
                    LIMIT 1
                ''', (tournament_id,))
                
                winner = cursor.fetchone()
                
                if winner:
                    winner_name, winner_lastname, correct_answers, total_score = winner
                    winner_display = f"{winner_name} {winner_lastname}"
                    winner_score = ""
                else:
                    winner_display = "Henüz kazanan yok"
                    winner_score = ""
                
                # Gün durumunu belirle
                if current_date.date() == now.date():
                    day_status = "today"
                    day_icon = "🔥"
                elif current_date.date() < now.date():
                    day_status = "completed"
                    day_icon = "✓"
                else:
                    day_status = "upcoming"
                    day_icon = "🔒"
                
                weekly_calendar.append({
                    'day_name': day_name,
                    'day_status': day_status,
                    'day_icon': day_icon,
                    'tournament_title': tournament_title,
                    'tournament_status': tournament_status,
                    'winner_name': winner_display,
                    'winner_score': winner_score,
                    'date': current_date.strftime('%Y-%m-%d')
                })
            else:
                # Bu gün için turnuva yok
                if current_date.date() == now.date():
                    day_status = "today"
                    day_icon = "📅"
                elif current_date.date() < now.date():
                    day_status = "completed"
                    day_icon = "✓"
                else:
                    day_status = "upcoming"
                    day_icon = "🔒"
                
                weekly_calendar.append({
                    'day_name': day_name,
                    'day_status': day_status,
                    'day_icon': day_icon,
                    'tournament_title': "Turnuva yok",
                    'tournament_status': "none",
                    'winner_name': "",
                    'winner_score': "",
                    'date': current_date.strftime('%Y-%m-%d')
                })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'weekly_calendar': weekly_calendar,
            'current_week': {
                'start_date': start_of_week.strftime('%Y-%m-%d'),
                'end_date': end_of_week.strftime('%Y-%m-%d')
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 