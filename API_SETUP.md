# 🚀 Gemini API Kurulumu

## 1. API Anahtarı Alma

1. **Google AI Studio'ya** gidin: https://aistudio.google.com
2. **"Get API Key"** butonuna tıklayın
3. **"Create API key"** seçin
4. API anahtarınızı kopyalayın

## 2. API Anahtarını Ayarlama

### Windows (PowerShell):
```powershell
$env:GEMINI_API_KEY="your_actual_api_key_here"
```

### Windows (Command Prompt):
```cmd
set GEMINI_API_KEY=your_actual_api_key_here
```

### Linux/Mac:
```bash
export GEMINI_API_KEY="your_actual_api_key_here"
```

## 3. Kalıcı Ayarlama

### Windows:
1. **Sistem Özellikleri** > **Gelişmiş** > **Ortam Değişkenleri**
2. **Yeni** > **GEMINI_API_KEY** = `your_actual_api_key_here`

### Linux/Mac (.bashrc veya .zshrc):
```bash
echo 'export GEMINI_API_KEY="your_actual_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

## 4. Test Etme

Uygulamayı yeniden başlatın ve admin panelinden soru üretmeyi deneyin!

## 🎯 Artık Desteklenen Konular:

- **Python Programlama**
- **JavaScript & React**
- **İngilizce Temel Seviye**
- **Matematik**
- **Tarih**
- **Coğrafya** 
- **Fen Bilgisi**
- **Ve daha fazlası!**

Herhangi bir konu yazın, AI o konuya göre sorular üretecek! 🚀