import fa from './locales/fa.js';
import en from './locales/en.js';

class I18n {
    constructor() {
        this.currentLang = localStorage.getItem('selectedLanguage') || 'fa';
        this.dictionaries = { fa, en };
        this.fallbackLang = 'en';
        this.init();
    }

    init() {
        this.updateHTMLAttributes();
        document.addEventListener('DOMContentLoaded', () => {
            this.translatePage();
        });
    }

    setLanguage(lang) {
        if (!this.dictionaries[lang]) {
            console.warn(`Language ${lang} not supported`);
            return;
        }
        
        this.currentLang = lang;
        localStorage.setItem('selectedLanguage', lang);
        this.updateHTMLAttributes();
        this.translatePage();
    }

    updateHTMLAttributes() {
        const html = document.documentElement;
        html.lang = this.currentLang;
        html.dir = this.currentLang === 'fa' ? 'rtl' : 'ltr';
        html.classList.remove('rtl', 'ltr');
        html.classList.add(this.currentLang === 'fa' ? 'rtl' : 'ltr');
    }

    t(key, fallback = null) {
        const dict = this.dictionaries[this.currentLang];
        const fallbackDict = this.dictionaries[this.fallbackLang];
        
        const getValue = (obj, path) => {
            return path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : undefined), obj);
        };

        let value = getValue(dict, key);
        
        if (value !== undefined) {
            return value;
        }

        value = getValue(fallbackDict, key);
        if (value !== undefined) {
            console.warn(`[i18n] Using fallback for key: ${key}`);
            return value;
        }

        console.warn(`[i18n] Missing translation for key: ${key}`);
        return fallback || key;
    }

    translatePage() {
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);
            
            if (el.tagName === 'INPUT' && (el.type === 'text' || el.type === 'password' || el.type === 'search')) {
                el.placeholder = translation;
            } else {
                el.textContent = translation;
            }
        });

        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            el.title = this.t(key);
        });

        document.querySelectorAll('[data-i18n-value]').forEach(el => {
            const key = el.getAttribute('data-i18n-value');
            el.value = this.t(key);
        });
    }

    getCurrentLang() {
        return this.currentLang;
    }

    isRTL() {
        return this.currentLang === 'fa';
    }

    formatNumber(number) {
        if (this.currentLang === 'fa') {
            return new Intl.NumberFormat('fa-IR').format(number);
        }
        return new Intl.NumberFormat('en-US').format(number);
    }

    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        const value = parseFloat((bytes / Math.pow(k, i)).toFixed(dm));
        
        return `${this.formatNumber(value)} ${sizes[i]}`;
    }

    formatUptime(uptimeParts) {
        if (!uptimeParts) return '--';
        
        const { days, hours, minutes } = uptimeParts;
        const format = this.t('time.uptimeFormat');
        
        return format
            .replace('{days}', this.formatNumber(days))
            .replace('{hours}', this.formatNumber(hours))
            .replace('{minutes}', this.formatNumber(minutes));
    }
}

window.i18n = new I18n();

export default window.i18n;