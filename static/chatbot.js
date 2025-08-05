document.addEventListener("DOMContentLoaded", function () {
  fetch("/static/chatbot.html")
    .then(response => response.text())
    .then(html => {
      document.body.insertAdjacentHTML("beforeend", html);

      const toggle = document.getElementById("chatbot-toggle");
      const box = document.getElementById("chatbot-box");

      toggle.addEventListener("click", () => {
        box.classList.toggle("hidden");
      });
    })
    .catch(err => console.error("Chatbot yüklenemedi:", err));
});
window.closeChat = function () {
  const chatBox = document.getElementById('chatbot-box');
  chatBox.classList.add('hidden');
};