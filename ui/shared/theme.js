// ===== Global Theme Manager ===== //

class ThemeManager {
  constructor() {
    this.theme = this.getStoredTheme();
    this.init();
  }
  
  getStoredTheme() {
    try {
      return localStorage.getItem('theme') || 'light';
    } catch {
      return 'light';
    }
  }
  
  setTheme(theme) {
    this.theme = theme;
    try {
      localStorage.setItem('theme', theme);
    } catch {}
    
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    
    this.updateThemeButtons();
  }
  
  toggleTheme() {
    const newTheme = this.theme === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
  }
  
  updateThemeButtons() {
    const buttons = document.querySelectorAll('.theme-toggle, .ui-theme-btn, #themeToggle');
    buttons.forEach(btn => {
      if (btn) {
        btn.textContent = this.theme === 'light' ? '🌙' : '☀️';
      }
    });
  }
  
  init() {
    this.setTheme(this.theme);
    
    // Auto-detect theme buttons and add event listeners
    document.addEventListener('click', (e) => {
      if (e.target.matches('.theme-toggle, .ui-theme-btn, #themeToggle')) {
        e.preventDefault();
        this.toggleTheme();
      }
    });
  }
}

// Initialize theme manager globally
window.themeManager = new ThemeManager();