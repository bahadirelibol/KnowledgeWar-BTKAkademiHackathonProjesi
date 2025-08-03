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

# Veritabanını başlat
init_db()

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
            "yaklasim": style_mapping.get(responses['learning_style'], "genel öğrenme"),
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
        required_fields = ['skill', 'goal', 'level', 'time', 'learning_style']
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
        ''', (payload['user_id'], data['skill'], data['goal'], data['level'], data['time'], data['learning_style']))
        
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

# Turnuva API'leri
def generate_questions_with_gemini(topic):
    """Gemini API ile soru üret"""
    try:
        if GEMINI_API_KEY == "your_gemini_api_key_here":
            # Demo sorular döndür
            return get_demo_questions(topic)
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
        {topic} konusu için 10 adet çoktan seçmeli soru üret. 
        Her soru için 4 şık olmalı (A, B, C, D) ve sadece bir doğru cevap olmalı.
        
        Yanıtı şu JSON formatında ver:
        {{
            "questions": [
                {{
                    "question": "Soru metni",
                    "options": ["A şıkkı", "B şıkkı", "C şıkkı", "D şıkkı"],
                    "correct_option": "A"
                }}
            ]
        }}
        
        Sorular Türkçe olmalı ve Python programlama ile ilgili olmalı.
        """
        
        response = model.generate_content(prompt)
        
        # JSON parse et
        import json
        try:
            result = json.loads(response.text)
            return result.get("questions", [])
        except:
            # JSON parse edilemezse demo sorular döndür
            return get_demo_questions(topic)
            
    except Exception as e:
        print(f"Gemini API hatası: {e}")
        return get_demo_questions(topic)

def get_demo_questions(topic):
    """Demo sorular döndür"""
    if "data" in topic.lower() or "veri" in topic.lower():
        return [
            {
                "question": "Python'da bir liste oluşturmak için hangi syntax kullanılır?",
                "options": ["list()", "array()", "vector()", "sequence()"],
                "correct_option": "A"
            },
            {
                "question": "Hangi veri yapısı key-value çiftleri saklar?",
                "options": ["List", "Tuple", "Dictionary", "Set"],
                "correct_option": "C"
            },
            {
                "question": "Set veri yapısının özelliği nedir?",
                "options": ["Sıralı elemanlar", "Tekrarlanan elemanlar", "Benzersiz elemanlar", "Değiştirilemez elemanlar"],
                "correct_option": "C"
            },
            {
                "question": "List comprehension syntax'ı nedir?",
                "options": ["[x for x in range(10)]", "(x for x in range(10))", "{x for x in range(10)}", "<x for x in range(10)>"],
                "correct_option": "A"
            },
            {
                "question": "Hangi metod liste elemanlarını tersine çevirir?",
                "options": ["reverse()", "sort()", "flip()", "invert()"],
                "correct_option": "A"
            }
        ]
    else:
        return [
            {
                "question": "Python'da fonksiyon tanımlamak için hangi keyword kullanılır?",
                "options": ["function", "def", "func", "define"],
                "correct_option": "B"
            },
            {
                "question": "Hangi veri tipi ondalık sayıları temsil eder?",
                "options": ["int", "float", "decimal", "real"],
                "correct_option": "B"
            },
            {
                "question": "String'leri birleştirmek için hangi operatör kullanılır?",
                "options": ["+", "&", "|", "||"],
                "correct_option": "A"
            },
            {
                "question": "Hangi döngü türü en az bir kez çalışır?",
                "options": ["for", "while", "do-while", "repeat"],
                "correct_option": "C"
            },
            {
                "question": "Exception handling için hangi blok kullanılır?",
                "options": ["try-except", "catch-throw", "error-handle", "exception-catch"],
                "correct_option": "A"
            }
        ]

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
        questions = generate_questions_with_gemini(data['content'])
        
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
            INSERT INTO tournaments (title, content, start_time, end_time, status)
            VALUES (?, ?, ?, ?, 'active')
        ''', (data['title'], data['content'], data['start_time'], data['end_time']))
        
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
            SELECT id, title, content, start_time, end_time, status, created_at
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
                'start_time': tournament[3],
                'end_time': tournament[4],
                'status': tournament[5],
                'created_at': tournament[6]
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
            INSERT INTO tournament_participants (user_id, tournament_id)
            VALUES (?, ?)
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
                'can_join': current_time <= end_time,  # Sadece bitiş zamanını kontrol et
                'can_participate': participant is not None and current_time <= end_time,
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
            SELECT id, title, content, start_time, end_time, status
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
                'start_time': tournament[3],
                'end_time': tournament[4],
                'status': tournament[5],
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

if __name__ == '__main__':
    app.run(debug=True, port=5000) 