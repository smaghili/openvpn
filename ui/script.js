function toggleTheme() {
  document.documentElement.classList.toggle('dark');
}

function toggleLanguage() {
  if (window.i18n) {
    const currentLang = window.i18n.getCurrentLang();
    const newLang = currentLang === 'fa' ? 'en' : 'fa';
    window.i18n.setLanguage(newLang);
  }
}

// Legacy compatibility functions
function setLanguage(lang) {
  if (window.i18n) {
    window.i18n.setLanguage(lang);
  }
}

function getCurrentLanguage() {
  if (window.i18n) {
    return window.i18n.getCurrentLang();
  }
  return localStorage.getItem('selectedLanguage') || 'fa';
}

function showToast(message, type='info') {
  const container = document.querySelector('.toast-container');
  if (!container) return;
  
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  
  setTimeout(() => toast.classList.add('show'), 100);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => container.removeChild(toast), 300);
  }, 3000);
}

function showModal(message, onConfirm) {
  const modal = document.querySelector('.modal');
  if (!modal) return;
  
  const text = modal.querySelector('.modal-message');
  if (text) text.textContent = message;
  
  modal.style.display = 'flex';
  
  const yes = modal.querySelector('.yes');
  const no = modal.querySelector('.no');
  
  if (yes) yes.onclick = () => { modal.style.display='none'; if(onConfirm) onConfirm(); };
  if (no) no.onclick = () => { modal.style.display='none'; };
}

function openDrawer(id) {
  const drawer = document.getElementById(id);
  if (drawer) drawer.classList.add('open');
}

function closeDrawer(id) {
  const drawer = document.getElementById(id);
  if (drawer) drawer.classList.remove('open');
}

// Initialize language system on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  // Apply RTL/LTR based on saved language
  const savedLang = localStorage.getItem('selectedLanguage') || 'fa';
  document.documentElement.lang = savedLang;
  document.documentElement.dir = savedLang === 'fa' ? 'rtl' : 'ltr';
  
  // Apply theme
  const isDark = localStorage.getItem('theme') === 'dark';
  if (isDark) {
    document.documentElement.classList.add('dark');
  }
});