const avatarBtn = document.getElementById('avatarButton');
const dropdownMenu = document.getElementById('dropdownMenu');

document.addEventListener('click', function (e) {
    const isClickInside = avatarBtn.contains(e.target) || dropdownMenu.contains(e.target);

    if (avatarBtn.contains(e.target)) {
        dropdownMenu.classList.toggle('opacity-0');
        dropdownMenu.classList.toggle('scale-95');
        dropdownMenu.classList.toggle('pointer-events-none');
    } else if (!isClickInside) {
        dropdownMenu.classList.add('opacity-0', 'scale-95', 'pointer-events-none');
    }
});

// Create animated stars
function createStars() {
    const starsContainer = document.getElementById('stars');
    for (let i = 0; i < 200; i++) {
        const star = document.createElement('div');
        star.classList.add('star');

        // Rastgele konum
        const x = Math.random() * window.innerWidth;
        const y = Math.random() * window.innerHeight;

        // Rastgele boyut
        const size = Math.random() * 2 + 1;
        star.style.width = `${size}px`;
        star.style.height = `${size}px`;

        // Yıldızın konumu
        star.style.top = `${y}px`;
        star.style.left = `${x}px`;

        // Farklı animasyon süreleriyle daha doğal görünüm
        star.style.animationDuration = `${Math.random() * 3 + 2}s`;

        starsContainer.appendChild(star);
    }
}

// Modal işlemleri
const editButton = document.querySelector("button:contains('Edit Profile')");
const editModal = document.getElementById('editModal');
const closeModal = document.getElementById('closeModal');
const cancelEdit = document.getElementById('cancelEdit');

// Modal aç
document.querySelectorAll("button").forEach(btn => {
    if (btn.textContent.includes('Edit Profile')) {
        btn.addEventListener('click', () => {
            editModal.classList.remove('hidden');
        });
    }
});

// Modal kapat
[closeModal, cancelEdit].forEach(el => {
    el.addEventListener('click', () => {
        editModal.classList.add('hidden');
    });
});

// Sayfa yüklendiğinde yıldızları oluştur
window.addEventListener('DOMContentLoaded', () => {
    createStars();
});

function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    window.location.href = '/';
}