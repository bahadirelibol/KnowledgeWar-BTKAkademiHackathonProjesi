from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import hashlib
import jwt
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

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
    
    conn.commit()
    conn.close()

# Veritabanını başlat
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def loginIndex():
    return render_template('login-register.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

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

if __name__ == '__main__':
    app.run(debug=True, port=5000) 