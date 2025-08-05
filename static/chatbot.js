document.addEventListener("DOMContentLoaded", function () {
  fetch("/static/chatbot.html")
    .then(response => response.text())
    .then(html => {
      document.body.insertAdjacentHTML("beforeend", html);

      const toggle = document.getElementById("chatbot-toggle");
      const box = document.getElementById("chatbot-box");
      const input = document.querySelector("#chatbot-box input");
      const sendButton = document.querySelector("#chatbot-box button");
      const chatArea = document.querySelector("#chatbot-box .overflow-y-auto .space-y-4");

      // Chat geçmişi
      let chatHistory = [];

      toggle.addEventListener("click", () => {
        box.classList.toggle("hidden");
      });

      // Mesaj gönderme fonksiyonu
      function sendMessage() {
        const message = input.value.trim();
        if (!message) return;

        // Kullanıcı mesajını ekle
        addMessageToChat("user", message);
        input.value = "";

        // Loading mesajı göster
        const loadingId = addLoadingMessage();

        // API'ye gönder
        fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message: message }),
        })
          .then((response) => response.json())
          .then((data) => {
            // Loading mesajını kaldır
            removeLoadingMessage(loadingId);
            
            // Bot yanıtını ekle
            addMessageToChat("bot", data.response);
          })
          .catch((error) => {
            console.error("Chat hatası:", error);
            removeLoadingMessage(loadingId);
            addMessageToChat("bot", "Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.");
          });
      }

      // Mesajı chat alanına ekle
      function addMessageToChat(sender, message) {
        const messageDiv = document.createElement("div");
        messageDiv.className = "flex items-start space-x-3";
        
        const timestamp = new Date().toLocaleTimeString('tr-TR', { 
          hour: '2-digit', 
          minute: '2-digit' 
        });

        if (sender === "user") {
          messageDiv.innerHTML = `
            <div class="flex-1"></div>
            <div class="bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-md max-w-xs">
              <p class="text-sm">${message}</p>
              <span class="text-xs text-blue-100 mt-1 block">${timestamp}</span>
            </div>
            <div class="w-8 h-8 rounded-full bg-gradient-to-r from-blue-400 to-purple-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
              👤
            </div>
          `;
        } else {
          messageDiv.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-gradient-to-r from-blue-400 to-purple-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
              🤖
            </div>
            <div class="bg-white/80 backdrop-blur-sm rounded-2xl rounded-tl-sm px-4 py-3 shadow-md border border-gray-100 max-w-xs">
              <p class="text-sm text-gray-700">${message}</p>
              <span class="text-xs text-gray-400 mt-1 block">${timestamp}</span>
            </div>
          `;
        }

        chatArea.appendChild(messageDiv);
        chatArea.scrollTop = chatArea.scrollHeight;
        
        // Chat geçmişine ekle
        chatHistory.push({ sender, message, timestamp });
      }

      // Loading mesajı ekle
      function addLoadingMessage() {
        const loadingId = "loading-" + Date.now();
        const loadingDiv = document.createElement("div");
        loadingDiv.id = loadingId;
        loadingDiv.className = "flex items-start space-x-3";
        loadingDiv.innerHTML = `
          <div class="w-8 h-8 rounded-full bg-gradient-to-r from-blue-400 to-purple-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
            🤖
          </div>
          <div class="bg-white/80 backdrop-blur-sm rounded-2xl rounded-tl-sm px-4 py-3 shadow-md border border-gray-100">
            <div class="flex space-x-1">
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            </div>
          </div>
        `;
        chatArea.appendChild(loadingDiv);
        chatArea.scrollTop = chatArea.scrollHeight;
        return loadingId;
      }

      // Loading mesajını kaldır
      function removeLoadingMessage(loadingId) {
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
          loadingElement.remove();
        }
      }

      // Enter tuşu ile mesaj gönder
      input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          sendMessage();
        }
      });

      // Gönder butonuna tıklama
      sendButton.addEventListener("click", sendMessage);

      // Hızlı yanıt butonları
      const quickButtons = document.querySelectorAll("#chatbot-box .flex-wrap button");
      quickButtons.forEach(button => {
        button.addEventListener("click", () => {
          const quickMessage = button.textContent.trim();
          input.value = quickMessage;
          sendMessage();
        });
      });
    })
    .catch(err => console.error("Chatbot yüklenemedi:", err));
});

window.closeChat = function () {
  const chatBox = document.getElementById('chatbot-box');
  chatBox.classList.add('hidden');
};