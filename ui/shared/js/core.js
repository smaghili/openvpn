// Core JavaScript - توابع اصلی مشترک

// Global app state
window.VPNPanel = {
	currentLanguage: 'fa',
	currentTheme: 'light',
	isAuthenticated: false,
	translations: {},
	
	// Initialize the application
	init() {
		this.loadSettings();
		this.setupEventListeners();
		this.applyTheme();
		this.applyLanguage();
		// Load translations then notify
		this.loadTranslations().then(() => {
			this.updateAllTexts();
			document.dispatchEvent(new CustomEvent('translationsLoaded'));
		});
	},
	
	// Load saved settings from localStorage
	loadSettings() {
		const savedLanguage = localStorage.getItem('vpn_panel_language');
		const savedTheme = localStorage.getItem('vpn_panel_theme');
		
		if (savedLanguage) this.currentLanguage = savedLanguage;
		if (savedTheme) this.currentTheme = savedTheme;
	},
	
	// Load translation files
	async loadTranslations() {
                try {
                        const basePath = window.location.pathname.split('/ui/')[0];
                        const url = `${basePath}/ui/shared/locales/${this.currentLanguage}.json`;
                        const response = await fetch(url, { cache: 'no-store' });
                        this.translations = await response.json();
                        return true;
                } catch (error) {
                        console.warn('Failed to load translations:', error);
                        if (this.currentLanguage !== 'en') {
                                try {
                                        const basePath = window.location.pathname.split('/ui/')[0];
                                        const response = await fetch(`${basePath}/ui/shared/locales/en.json`, { cache: 'no-store' });
                                        this.translations = await response.json();
                                        return true;
                                } catch (fallbackError) {
                                        console.error('Failed to load fallback translations:', fallbackError);
                                }
                        }
                        return false;
                }
        },
	
	// Setup global event listeners
	setupEventListeners() {
		// Listen for theme changes
                document.addEventListener('themeChanged', (event) => {
                        this.currentTheme = event.detail.theme;
                        this.saveSettings();
                        this.applyTheme();
                });
		
		// Listen for language changes
		document.addEventListener('languageChanged', (event) => {
			this.currentLanguage = event.detail.language;
			this.saveSettings();
			this.loadTranslations().then(() => {
				this.applyLanguage();
				this.updateAllTexts();
				document.dispatchEvent(new CustomEvent('translationsLoaded'));
			});
		});
	},
	
	// Save settings to localStorage
	saveSettings() {
		localStorage.setItem('vpn_panel_language', this.currentLanguage);
		localStorage.setItem('vpn_panel_theme', this.currentTheme);
	},
	
	// Apply current theme
	applyTheme() {
		document.documentElement.setAttribute('data-theme', this.currentTheme);
		document.body.classList.toggle('dark-theme', this.currentTheme === 'dark');
	},
	
	// Apply current language
	applyLanguage() {
		document.documentElement.setAttribute('lang', this.currentLanguage);
		document.documentElement.setAttribute('dir', this.currentLanguage === 'fa' ? 'rtl' : 'ltr');
	},
	
	// Get translation text
	t(key) {
		const keys = key.split('.');
		let value = this.translations;
		
		for (const k of keys) {
			if (value && typeof value === 'object' && k in value) {
				value = value[k];
			} else {
				return key; // Return key if translation not found
			}
		}
		
		return value || key;
	},
	
	// Update all text elements with translations
	updateAllTexts() {
		const elements = document.querySelectorAll('[data-i18n]');
		elements.forEach(element => {
			const key = element.getAttribute('data-i18n');
			const translation = this.t(key);
			if (translation && translation !== key) {
				element.textContent = translation;
			}
		});
		// Update placeholders
		const placeholderEls = document.querySelectorAll('[data-i18n-placeholder]');
		placeholderEls.forEach(el => {
			const key = el.getAttribute('data-i18n-placeholder');
			const translation = this.t(key);
			if (translation && translation !== key) {
				el.setAttribute('placeholder', translation);
			}
		});
	},
	
	// Show notification/toast (uses fixed container if available)
	showNotification(message, type = 'info', duration = 2500) {
		const container = document.getElementById('notificationContainer');
		const target = container || document.body;
		const notification = document.createElement('div');
		notification.className = `alert alert-${type} notification`;
		notification.textContent = message;
		
		target.appendChild(notification);
		
		// Animate in
		requestAnimationFrame(() => {
			notification.style.opacity = '1';
			notification.style.transform = 'translateY(0)';
		});
		
		// Auto remove
		setTimeout(() => {
			notification.style.opacity = '0';
			notification.style.transform = 'translateY(-100%)';
			setTimeout(() => {
				if (notification.parentNode) notification.parentNode.removeChild(notification);
			}, 250);
		}, duration);
	},
	
	// Show loading state
	showLoading(element, text = '') {
		if (element) {
			element.classList.add('loading');
			element.disabled = true;
			
			if (text) {
				const originalText = element.textContent;
				element.setAttribute('data-original-text', originalText);
				element.textContent = text;
			}
		}
	},
	
	// Hide loading state
	hideLoading(element) {
		if (element) {
			element.classList.remove('loading');
			element.disabled = false;
			
			const originalText = element.getAttribute('data-original-text');
			if (originalText) {
				element.textContent = originalText;
				element.removeAttribute('data-original-text');
			}
		}
	},
	
	// Validate form fields
	validateForm(form) {
		const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
		let isValid = true;
		
		inputs.forEach(input => {
			if (!input.value.trim()) {
				this.showFieldError(input, this.t('messages.required_field'));
				isValid = false;
			} else {
				this.clearFieldError(input);
			}
		});
		
		return isValid;
	},
	
	// Show field error
	showFieldError(field, message) {
		field.classList.add('error');
		
		// Remove existing error message
		const existingError = field.parentNode.querySelector('.form-error');
		if (existingError) {
			existingError.remove();
		}
		
		// Add new error message
		const errorElement = document.createElement('div');
		errorElement.className = 'form-error';
		errorElement.textContent = message;
		field.parentNode.appendChild(errorElement);
	},
	
	// Clear field error
	clearFieldError(field) {
		field.classList.remove('error');
		
		const errorElement = field.parentNode.querySelector('.form-error');
		if (errorElement) {
			errorElement.remove();
		}
	},
	
	// Format date
	formatDate(date, options = {}) {
		const defaultOptions = {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		};
		
		const finalOptions = { ...defaultOptions, ...options };
		return new Intl.DateTimeFormat(this.currentLanguage, finalOptions).format(date);
	},
	
	// Format number
	formatNumber(number, options = {}) {
		const defaultOptions = {
			minimumFractionDigits: 0,
			maximumFractionDigits: 2
		};
		
		const finalOptions = { ...defaultOptions, ...options };
		return new Intl.NumberFormat(this.currentLanguage, finalOptions).format(number);
	},
	
	// Debounce function
	debounce(func, wait) {
		let timeout;
		return function executedFunction(...args) {
			const later = () => {
				clearTimeout(timeout);
				func(...args);
			};
			clearTimeout(timeout);
			timeout = setTimeout(later, wait);
		};
	},
	
	// Throttle function
	throttle(func, limit) {
		let inThrottle;
		return function() {
			const args = arguments;
			const context = this;
			if (!inThrottle) {
				func.apply(context, args);
				inThrottle = true;
				setTimeout(() => inThrottle = false, limit);
			}
		};
	}
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
	VPNPanel.init();
});
