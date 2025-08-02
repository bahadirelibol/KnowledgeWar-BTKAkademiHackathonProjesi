// Create animated stars
function createStars() {
    const starsContainer = document.getElementById('stars');
    for (let i = 0; i < 150; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.animationDelay = Math.random() * 3 + 's';
        starsContainer.appendChild(star);
    }
}
createStars();

// Form switching functionality
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const successMessage = document.getElementById('successMessage');
const showRegisterBtn = document.getElementById('showRegister');
const showLoginBtn = document.getElementById('showLogin');

function switchToRegister() {
    loginForm.classList.add('slide-out-left');
    setTimeout(() => {
        loginForm.classList.add('hidden');
        loginForm.classList.remove('slide-out-left');
        registerForm.classList.remove('hidden');
        registerForm.classList.add('slide-in-right');
    }, 300);
}

function switchToLogin() {
    registerForm.classList.add('slide-out-right');
    setTimeout(() => {
        registerForm.classList.add('hidden');
        registerForm.classList.remove('slide-out-right');
        loginForm.classList.remove('hidden');
        loginForm.classList.add('slide-in-left');
    }, 300);
}

showRegisterBtn.addEventListener('click', switchToRegister);
showLoginBtn.addEventListener('click', switchToLogin);

// Password strength checker
const passwordInput = document.querySelector('#registerPassword');
const strengthBars = document.querySelectorAll('.h-1');
const strengthText = document.querySelector('.text-xs.text-gray-400');

function checkPasswordStrength(password) {
    let strength = 0;
    const checks = [
        password.length >= 8,
        /[a-z]/.test(password),
        /[A-Z]/.test(password),
        /[0-9]/.test(password),
        /[^A-Za-z0-9]/.test(password)
    ];

    strength = checks.filter(check => check).length;

    const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'];
    const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];

    strengthBars.forEach((bar, index) => {
        bar.className = `h-1 w-1/4 rounded ${index < strength ? colors[strength - 1] : 'bg-gray-600'}`;
    });

    if (strengthText) {
        strengthText.textContent = `Password strength: ${strength > 0 ? labels[strength - 1] : 'Too short'}`;
        strengthText.className = `text-xs ${strength > 2 ? 'text-green-400' : strength > 0 ? 'text-yellow-400' : 'text-red-400'}`;
    }
}

// API Functions
const API_BASE_URL = 'http://localhost:5000/api';

async function registerUser(userData) {
    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData)
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Kayıt işlemi başarısız');
        }

        return data;
    } catch (error) {
        throw error;
    }
}

async function loginUser(userData) {
    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData)
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Giriş işlemi başarısız');
        }

        return data;
    } catch (error) {
        throw error;
    }
}

// Show notification
function showNotification(message, type = 'success') {
    // Remove existing notifications
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    const notification = document.createElement('div');
    notification.className = `notification fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 ${
        type === 'success' ? 'bg-green-500' : 'bg-red-500'
    } text-white`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Form validation and submission
const loginFormElement = document.getElementById('loginFormElement');
const registerFormElement = document.getElementById('registerFormElement');

// Login form submission
loginFormElement.addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    // Add loading state
    const submitBtn = loginFormElement.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.innerHTML = `
        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Giriş yapılıyor...
    `;
    submitBtn.disabled = true;

    try {
        const result = await loginUser({ email, password });
        
        // Store token and user data
        localStorage.setItem('authToken', result.token);
        localStorage.setItem('userData', JSON.stringify(result.user));
        
        showNotification('Giriş başarılı!', 'success');
        
        // Redirect to dashboard or main page
        setTimeout(() => {
            window.location.href = '/profile'; // You can change this to your desired page
        }, 1500);
        
    } catch (error) {
        showNotification(error.message, 'error');
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

// Register form submission
registerFormElement.addEventListener('submit', async function (e) {
    e.preventDefault();

    const firstName = document.getElementById('registerFirstName').value;
    const lastName = document.getElementById('registerLastName').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('registerConfirmPassword').value;

    // Password confirmation check
    if (password !== confirmPassword) {
        showNotification('Şifreler eşleşmiyor!', 'error');
        return;
    }

    // Add loading state
    const submitBtn = registerFormElement.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.innerHTML = `
        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Kayıt yapılıyor...
    `;
    submitBtn.disabled = true;

    try {
        const result = await registerUser({ 
            first_name: firstName, 
            last_name: lastName, 
            email, 
            password 
        });
        
        // Store token and user data
        localStorage.setItem('authToken', result.token);
        localStorage.setItem('userData', JSON.stringify(result.user));
        
        showNotification('Kayıt başarılı!', 'success');
        
        // Show success message
        registerForm.classList.add('slide-out-left');
        setTimeout(() => {
            registerForm.classList.add('hidden');
            registerForm.classList.remove('slide-out-left');
            successMessage.classList.remove('hidden');
            successMessage.classList.add('slide-in-right');
        }, 300);
        
    } catch (error) {
        showNotification(error.message, 'error');
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

// Password strength checker for register form
if (passwordInput) {
    passwordInput.addEventListener('input', function() {
        checkPasswordStrength(this.value);
    });
}

// Check if user is already logged in
function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    const userData = localStorage.getItem('userData');
    
    if (token && userData) {
        // User is logged in, redirect to dashboard
        window.location.href = '/dashboard';
    }
}

// Logout function
function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    window.location.href = '/';
}

// Check auth status on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
});

// Create particle effect for button clicks
function createParticle(x, y) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.left = x + 'px';
    particle.style.top = y + 'px';
    document.body.appendChild(particle);

    setTimeout(() => {
        particle.remove();
    }, 1000);
}

// Add particle effect to buttons
document.addEventListener('click', function(e) {
    if (e.target.tagName === 'BUTTON' && e.target.classList.contains('gradient-button')) {
        createParticle(e.clientX, e.clientY);
    }
});