// ===== Login Page JavaScript (isolated) =====

// Language configuration
const LANG_CONFIG = {
  fa: {
    flag: '<svg width="20" height="15" viewBox="0 0 20 15"><rect width="20" height="5" fill="#239f40"/><rect y="5" width="20" height="5" fill="#fff"/><rect y="10" width="20" height="5" fill="#da0000"/><circle cx="10" cy="7.5" r="2" fill="none" stroke="#da0000" stroke-width="0.5"/></svg>',
    name: 'Farsi',
    flagCode: 'IR'
  },
  en: {
    flag: '<svg width="20" height="15" viewBox="0 0 20 15"><rect width="20" height="15" fill="#b22234"/><rect y="1" width="20" height="1" fill="#fff"/><rect y="3" width="20" height="1" fill="#fff"/><rect y="5" width="20" height="1" fill="#fff"/><rect y="7" width="20" height="1" fill="#fff"/><rect y="9" width="20" height="1" fill="#fff"/><rect y="11" width="20" height="1" fill="#fff"/><rect y="13" width="20" height="1" fill="#fff"/><rect width="8" height="7" fill="#3c3b6e"/></svg>', 
    name: 'English',
    flagCode: 'US'
  }
};

// Login page initialization
document.addEventListener('DOMContentLoaded', () => {
  // Check if user is already authenticated
  if (checkAuth()) {
    window.location.href = '/overview';
    return;
  }
  
  initializeLoginPage();
});

// Check if user is authenticated
function checkAuth() {
  const token = localStorage.getItem('token');
  if (!token) {
    return false;
  }
  
  // Basic JWT validation (check if not expired)
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const currentTime = Math.floor(Date.now() / 1000);
    
    if (payload.exp && payload.exp < currentTime) {
      localStorage.removeItem('token');
      return false;
    }
    
    return true;
  } catch (error) {
    localStorage.removeItem('token');
    return false;
  }
}

function initializeLoginPage() {
  // Set current year
  const yearEl = document.querySelector('.year');
  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }

  // Initialize language dropdown
  initializeLanguageDropdown();
  
  // Initialize theme toggle
  initializeThemeToggle();
  
  // Initialize password toggle
  initializePasswordToggle();
  
  // Initialize login form
  initializeLoginForm();
}

function initializeLanguageDropdown() {
  const langDropdown = document.getElementById('langDropdown');
  const langMenu = document.getElementById('langMenu');
  const langItems = document.querySelectorAll('.ui-dropdown-item');

  if (!langDropdown || !langMenu) return;

  // Update current language display
  function updateCurrentLang() {
    const lang = window.currentLang || 'fa';
    const config = LANG_CONFIG[lang];
    if (!config) return;
    const btn = document.getElementById('langDropdown');
    if (!btn) return;
    const flagBox = btn.querySelector('.flag-box');
    const label = btn.querySelector('.lang-label');
    if (flagBox) flagBox.innerHTML = config.flag;
    if (label) label.textContent = config.name;
  }

  // Dropdown toggle
  langDropdown.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = langMenu.classList.contains('open');
    langMenu.classList.toggle('open', !isOpen);
    langDropdown.setAttribute('aria-expanded', !isOpen);
  });

  // Language selection
  langItems.forEach(item => {
    item.addEventListener('click', () => {
      const lang = item.getAttribute('data-lang');
      if (lang && LANG_CONFIG[lang]) {
        setLanguage(lang);
        window.currentLang = lang;
        updateCurrentLang();
        langMenu.classList.remove('open');
        langDropdown.setAttribute('aria-expanded', 'false');
      }
    });
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', () => {
    langMenu.classList.remove('open');
    langDropdown.setAttribute('aria-expanded', 'false');
  });

  // Initialize current language display
  window.currentLang = window.currentLang || localStorage.getItem('lang') || 'fa';
  updateCurrentLang();
}

function initializeThemeToggle() {
  const themeToggle = document.getElementById('themeToggle');
  if (!themeToggle) return;

  function updateThemeIcon() {
    const isDark = document.documentElement.classList.contains('dark');
    themeToggle.textContent = isDark ? '☀️' : '🌙';
  }

  themeToggle.addEventListener('click', () => {
    toggleTheme();
    updateThemeIcon();
  });

  // Set initial icon
  updateThemeIcon();
}

function initializePasswordToggle() {
  const togglePass = document.getElementById('togglePass');
  const passInput = document.getElementById('loginPass');
  
  if (!togglePass || !passInput) return;

  togglePass.addEventListener('click', () => {
    const isHidden = passInput.getAttribute('type') === 'password';
    passInput.setAttribute('type', isHidden ? 'text' : 'password');
    togglePass.setAttribute('data-visible', isHidden ? 'true' : 'false');
  });
}

function initializeLoginForm() {
  const loginForm = document.getElementById('loginForm');
  const submitBtn = document.getElementById('loginSubmit');
  
  if (!loginForm || !submitBtn) return;

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Form validation
    if (!loginForm.checkValidity()) {
      loginForm.reportValidity();
      return;
    }

    const username = document.getElementById('loginUser')?.value.trim();
    const password = document.getElementById('loginPass')?.value.trim();

    if (!username || !password) {
      showToast('لطفاً نام کاربری و رمز عبور را وارد کنید', 'error');
      return;
    }

    try {
      // Show loading state
      submitBtn.classList.add('loading');
      submitBtn.disabled = true;

      // Attempt login
      await apiLogin(username, password);
      
             // Redirect on success
       location.href = '/overview';
      
    } catch (err) {
      // Show error message
      const errorMessage = err && err.message ? err.message : 'خطا در ورود به سیستم';
      showToast(errorMessage, 'error');
      
    } finally {
      // Reset loading state
      submitBtn.classList.remove('loading');
      submitBtn.disabled = false;
    }
  });
}

// Enhanced toast function for login page
function showToast(message, type = 'info') {
  const container = document.querySelector('.toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  
  // Add type-specific styling
  if (type === 'error') {
    toast.style.borderColor = '#ef4444';
    toast.style.color = '#ef4444';
  } else if (type === 'success') {
    toast.style.borderColor = '#10b981';
    toast.style.color = '#10b981';
  }

  container.appendChild(toast);
  
  // Auto remove after 3 seconds
  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
    }
  }, 3000);
}

// Enhanced modal function for login page
function showModal(message, onConfirm) {
  const modal = document.querySelector('.modal');
  const text = modal?.querySelector('.modal-message');
  const yesBtn = modal?.querySelector('.yes');
  const noBtn = modal?.querySelector('.no');
  
  if (!modal || !text || !yesBtn || !noBtn) return;

  text.textContent = message;
  modal.style.display = 'flex';

  const cleanup = () => {
    modal.style.display = 'none';
    yesBtn.onclick = null;
    noBtn.onclick = null;
  };

  yesBtn.onclick = () => {
    cleanup();
    if (onConfirm) onConfirm();
  };

  noBtn.onclick = cleanup;
} 