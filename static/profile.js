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
const editModal = document.getElementById('editModal');
const closeModal = document.getElementById('closeModal');
const cancelEdit = document.getElementById('cancelEdit');

// Modal aç - daha güvenli yöntem
document.addEventListener('click', (e) => {
    if (e.target && e.target.textContent && e.target.textContent.includes('Edit Profile')) {
        if (editModal) {
            editModal.classList.remove('hidden');
        }
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

// Turnuva kazanımlarını yükle
async function loadTournamentWins() {
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/user-tournament-wins', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            console.log('API Response:', data);
            const container = document.getElementById('tournamentWinsContainer');
            const noWinsMessage = document.getElementById('noWinsMessage');

            if (data.tournament_wins && data.tournament_wins.length > 0) {
                // Kazanım mesajını gizle
                noWinsMessage.style.display = 'none';
                
                // Turnuva kazanımlarını göster
                container.innerHTML = '<div class="grid grid-cols-1 md:grid-cols-2 gap-3"></div>';
                const gridContainer = container.querySelector('.grid');
                
                data.tournament_wins.forEach((win, index) => {
                    const winCard = document.createElement('div');
                    winCard.className = 'bg-gradient-to-r from-yellow-500/10 to-orange-500/10 rounded-xl border border-yellow-500/20 p-4';
                    
                    winCard.innerHTML = `
                        <div class="flex items-center space-x-3">
                            <div class="text-2xl">🏆</div>
                            <div class="flex-1 min-w-0">
                                <h4 class="text-sm font-semibold text-white truncate">${win.tournament_title}</h4>
                                <div class="flex items-center space-x-3 text-xs text-gray-300 mt-1">
                                    <span class="text-green-400">${win.correct_answers}/${win.total_questions}</span>
                                    <span class="text-blue-400">${win.total_score}%</span>
                                    <span class="text-purple-400">${win.total_participants} kişi</span>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    gridContainer.appendChild(winCard);
                });
            } else {
                // Kazanım yoksa mesajı göster
                noWinsMessage.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Turnuva kazanımları yüklenirken hata:', error);
    }
}

// Debug için turnuva verilerini kontrol et
async function debugTournamentData() {
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/debug-tournament-data', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            console.log('DEBUG - Turnuva Verileri:', data);
        }
    } catch (error) {
        console.error('Debug verisi yüklenirken hata:', error);
    }
}