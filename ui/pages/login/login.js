// Login Page JavaScript - منطق صفحه لاگین

class LoginPage {
	constructor() {
		this.form = null;
		this.usernameInput = null;
		this.passwordInput = null;
		this.passwordToggle = null;
		this.rememberMeCheckbox = null;
		this.loginBtn = null;
		this.themeToggle = null;
		this.languageSelect = null;
		
		this.init();
	}
	
	init() {
		this.setupElements();
		this.setupEventListeners();
		this.loadSavedSettings();
		this.updatePlaceholders();
		// Wait for translations, then update texts
		document.addEventListener('translationsLoaded', () => {
			this.updatePlaceholders();
		});
	}
	
	setupElements() {
		this.form = document.getElementById('loginForm');
		this.usernameInput = document.getElementById('username');
		this.passwordInput = document.getElementById('password');
		this.passwordToggle = document.getElementById('passwordToggle');
		this.rememberMeCheckbox = document.getElementById('rememberMe');
		this.loginBtn = document.getElementById('loginBtn');
		this.themeToggle = document.getElementById('themeToggle');
		this.languageSelect = document.getElementById('languageSelect');
	}
	
	setupEventListeners() {
		// Form submission
		if (this.form) {
			this.form.addEventListener('submit', (e) => this.handleLogin(e));
		}
		
		// Password toggle
		if (this.passwordToggle) {
			this.passwordToggle.addEventListener('click', () => this.togglePassword());
		}
		
		// Theme toggle
		if (this.themeToggle) {
			this.themeToggle.addEventListener('click', () => this.toggleTheme());
		}
		
		// Language change
		if (this.languageSelect) {
			this.languageSelect.addEventListener('change', (e) => this.changeLanguage(e.target.value));
		}
		
		// Input focus effects
		if (this.usernameInput) {
			this.usernameInput.addEventListener('focus', () => this.handleInputFocus(this.usernameInput));
			this.usernameInput.addEventListener('blur', () => this.handleInputBlur(this.usernameInput));
		}
		
		if (this.passwordInput) {
			this.passwordInput.addEventListener('focus', () => this.handleInputFocus(this.passwordInput));
			this.passwordInput.addEventListener('blur', () => this.handleInputBlur(this.passwordInput));
		}
		
		// Enter key navigation
		if (this.usernameInput) {
			this.usernameInput.addEventListener('keydown', (e) => {
				if (e.key === 'Enter') this.passwordInput.focus();
			});
		}
		if (this.passwordInput) {
			this.passwordInput.addEventListener('keydown', (e) => {
				if (e.key === 'Enter') this.form.dispatchEvent(new Event('submit'));
			});
		}
	}
	
	loadSavedSettings() {
		const savedUsername = localStorage.getItem('vpn_remember_username');
		if (savedUsername && this.usernameInput) {
			this.usernameInput.value = savedUsername;
			this.rememberMeCheckbox.checked = true;
		}
		if (this.languageSelect) {
			this.languageSelect.value = VPNPanel.currentLanguage;
		}
		this.updateThemeIcon();
	}
	
	updatePlaceholders() {
		if (this.usernameInput) this.usernameInput.placeholder = VPNPanel.t('login.username_placeholder');
		if (this.passwordInput) this.passwordInput.placeholder = VPNPanel.t('login.password_placeholder');
	}
	
	handleInputFocus(input) {
		input.parentNode.classList.add('focused');
		input.classList.add('focused');
	}
	
	handleInputBlur(input) {
		input.parentNode.classList.remove('focused');
		input.classList.remove('focused');
		
		// Validate on blur
		this.validateField(input);
	}
	
	validateField(field) {
		const value = field.value.trim();
		if (field.hasAttribute('required') && !value) {
			VPNPanel.showFieldError(field, VPNPanel.t('messages.required_field'));
			return false;
		}
		VPNPanel.clearFieldError(field);
		return true;
	}
	
	validateForm() {
		let isValid = true;
		if (!this.validateField(this.usernameInput)) isValid = false;
		if (!this.validateField(this.passwordInput)) isValid = false;
		return isValid;
	}
	
	async handleLogin(event) {
		event.preventDefault();
		if (!this.validateForm()) return;
		
		const username = this.usernameInput.value.trim();
		const password = this.passwordInput.value.trim();
		const rememberMe = this.rememberMeCheckbox.checked;
		
		VPNPanel.showLoading(this.loginBtn, VPNPanel.t('common.loading'));
		try {
			const response = await this.performLogin(username, password);
			if (response.success) {
				if (rememberMe) localStorage.setItem('vpn_remember_username', username);
				else localStorage.removeItem('vpn_remember_username');
				
				VPNPanel.showNotification(VPNPanel.t('messages.login_success'), 'success');
				setTimeout(() => this.redirectToOverview(), 800);
			} else {
				throw new Error(response.message || VPNPanel.t('messages.login_failed'));
			}
		} catch (error) {
			VPNPanel.showNotification(error.message, 'error');
			this.passwordInput.value = '';
			this.passwordInput.focus();
		} finally {
			VPNPanel.hideLoading(this.loginBtn);
		}
	}
	
	async performLogin(username, password) {
		try {
			const response = await fetch('/api/auth/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, password })
			});
			const data = await response.json();
			if (response.ok && data.token) {
				localStorage.setItem('vpn_token', data.token);
				VPNPanel.isAuthenticated = true;
				return { success: true };
			}
			return { success: false, message: data.message || VPNPanel.t('messages.invalid_credentials') };
		} catch (_) {
			throw new Error(VPNPanel.t('messages.network_error'));
		}
	}
	
	togglePassword() {
		const type = this.passwordInput.type === 'password' ? 'text' : 'password';
		this.passwordInput.type = type;
		this.passwordToggle.textContent = type === 'password' ? '👁️' : '🙈';
		const label = type === 'password' ? 'نمایش رمز عبور' : 'مخفی کردن رمز عبور';
		this.passwordToggle.setAttribute('aria-label', label);
	}
	
	toggleTheme() {
		const newTheme = VPNPanel.currentTheme === 'light' ? 'dark' : 'light';
		VPNPanel.currentTheme = newTheme;
		document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
		this.updateThemeIcon();
		// No toast scroll; optional silent feedback
	}
	
	updateThemeIcon() {
		if (this.themeToggle) {
			const icon = this.themeToggle.querySelector('.theme-icon');
			if (icon) icon.textContent = VPNPanel.currentTheme === 'light' ? '☀️' : '🌙';
		}
	}
	
	changeLanguage(language) {
		VPNPanel.currentLanguage = language;
		document.dispatchEvent(new CustomEvent('languageChanged', { detail: { language } }));
		this.languageSelect.value = language;
		this.updatePlaceholders();
		// No noisy toast
	}
	
	redirectToOverview() {
		const overviewHTML = `
			<div class="overview-container">
				<div class="welcome-message">
					<h1>${VPNPanel.t('overview.welcome')}</h1>
					<p>${VPNPanel.t('overview.description')}</p>
				</div>
			</div>
		`;
		const loginContainer = document.querySelector('.login-container');
		if (loginContainer) loginContainer.innerHTML = overviewHTML;
		document.title = `${VPNPanel.t('overview.welcome')} - پنل مدیریت VPN`;
		this.addOverviewStyles();
	}
	
	addOverviewStyles() {
		const style = document.createElement('style');
		style.textContent = `
			.overview-container{ text-align:center; max-width:800px; margin:0 auto; padding:var(--spacing-2xl); }
			.welcome-message h1{ font-size:3rem; font-weight:700; color:var(--text-primary); margin-bottom:var(--spacing-lg); background:linear-gradient(135deg,var(--primary-600),var(--primary-700)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
			.welcome-message p{ font-size:1.25rem; color:var(--text-secondary); line-height:1.8; }
			@media (max-width:768px){ .welcome-message h1{ font-size:2.5rem; } }
		`;
		document.head.appendChild(style);
	}
}

// Initialize login page
document.addEventListener('DOMContentLoaded', () => { new LoginPage(); });
