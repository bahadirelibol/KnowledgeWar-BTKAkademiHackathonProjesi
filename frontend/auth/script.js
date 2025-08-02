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
const passwordInput = document.querySelector('input[type="password"]');
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

// Form validation and submission
const forms = document.querySelectorAll('form');
forms.forEach(form => {
    form.addEventListener('submit', function (e) {
        e.preventDefault();

        // Add loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.innerHTML = `
                    <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                `;
        submitBtn.disabled = true;
        window.location.href = "../profile/index.html";

        // Simulate API call
        setTimeout(() => {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;

            // Show success for register form
            if (form.closest('#registerForm')) {
                registerForm.classList.add('slide-out-left');
                setTimeout(() => {
                    registerForm.classList.add('hidden');
                    successMessage.classList.remove('hidden');
                    successMessage.classList.add('slide-in-right');
                }, 300);
            } else {
                // For login, you could redirect to dashboard
                console.log('Login successful!');
            }
        }, 2000);
    });
});

// Enhanced input interactions
const inputs = document.querySelectorAll('input');
inputs.forEach(input => {
    input.addEventListener('focus', function () {
        this.parentElement.classList.add('focused');
    });

    input.addEventListener('blur', function () {
        this.parentElement.classList.remove('focused');
        if (this.value) {
            this.classList.add('has-value');
        } else {
            this.classList.remove('has-value');
        }
    });

    // Real-time validation
    input.addEventListener('input', function () {
        if (this.type === 'email') {
            const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.value);
            this.classList.toggle('border-red-500', !isValid && this.value);
            this.classList.toggle('border-green-500', isValid);
        }

        if (this.type === 'password' && this.placeholder === '••••••••' && !this.nextElementSibling) {
            checkPasswordStrength(this.value);
        }
    });
});

// Password visibility toggle
const passwordToggles = document.querySelectorAll('button[type="button"]');
passwordToggles.forEach(toggle => {
    toggle.addEventListener('click', function () {
        const input = this.parentElement.querySelector('input');
        const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
        input.setAttribute('type', type);

        // Update icon
        const icon = this.querySelector('svg');
        if (type === 'text') {
            icon.innerHTML = `
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>
                    `;
        } else {
            icon.innerHTML = `
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    `;
        }
    });
});

// Social login handlers
const socialButtons = document.querySelectorAll('.social-button');
socialButtons.forEach(button => {
    button.addEventListener('click', function () {
        const provider = this.querySelector('span').textContent;
        console.log(`Authenticating with ${provider}...`);

        // Add loading state
        this.classList.add('opacity-75');
        setTimeout(() => {
            this.classList.remove('opacity-75');
        }, 1000);
    });
});

// Add some interactive particle effects
function createParticle(x, y) {
    const particle = document.createElement('div');
    particle.className = 'fixed w-1 h-1 bg-blue-400 rounded-full pointer-events-none';
    particle.style.left = x + 'px';
    particle.style.top = y + 'px';
    particle.style.animation = 'particleFloat 2s ease-out forwards';
    document.body.appendChild(particle);

    setTimeout(() => particle.remove(), 2000);
}

// Create particles on button clicks
document.addEventListener('click', function (e) {
    if (e.target.tagName === 'BUTTON') {
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                createParticle(
                    e.clientX + (Math.random() - 0.5) * 50,
                    e.clientY + (Math.random() - 0.5) * 50
                );
            }, i * 100);
        }
    }
});

// Add CSS for particle animation
const style = document.createElement('style');
style.textContent = `
            @keyframes particleFloat {
                0% {
                    transform: translateY(0) scale(1);
                    opacity: 1;
                }
                100% {
                    transform: translateY(-100px) scale(0);
                    opacity: 0;
                }
            }
        `;
document.head.appendChild(style);