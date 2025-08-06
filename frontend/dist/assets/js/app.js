/**
 * Main application controller for OpenVPN Manager
 * Handles authentication, theme management, and UI interactions
 */

class App {
    constructor() {
        this.isAuthenticated = false;
        this.currentTheme = 'light';
        this.sidebarCollapsed = false;
        this.refreshInterval = null;
        
        // Initialize application
        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            // Setup event listeners
            this.setupEventListeners();
            
            // Load theme preference
            this.loadThemePreference();
            
            // Check authentication status
            await this.checkAuthentication();
            
            // Hide loading screen
            this.hideLoadingScreen();
            
        } catch (error) {
            console.error('Failed to initialize application:', error);
            this.showError('Failed to initialize application');
        }
    }

    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Authentication events
        window.addEventListener('authenticationFailed', () => {
            this.handleLogout();
        });

        // Language change events
        window.addEventListener('languageChanged', (event) => {
            this.handleLanguageChange(event.detail.language);
        });

        // Theme events
        this.setupThemeEventListeners();
        
        // Login form
        this.setupLoginForm();
        
        // Sidebar events
        this.setupSidebarEventListeners();
        
        // WebSocket events
        this.setupWebSocketEventListeners();
        
        // Keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // Window events
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    /**
     * Setup theme event listeners
     */
    setupThemeEventListeners() {
        // Theme toggle buttons
        document.addEventListener('click', (event) => {
            if (event.target.matches('#theme-toggle, #nav-theme-toggle')) {
                this.toggleTheme();
            }
        });

        // Listen for system theme changes
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                if (this.currentTheme === 'auto') {
                    this.applyTheme('auto');
                }
            });
        }
    }

    /**
     * Setup login form
     */
    setupLoginForm() {
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', async (event) => {
                event.preventDefault();
                await this.handleLogin(event);
            });
        }

        // Language selector in login page
        document.addEventListener('click', (event) => {
            if (event.target.matches('#language-toggle, #nav-language-toggle')) {
                this.toggleLanguageDropdown(event.target);
            }
            
            if (event.target.matches('.language-option, .nav-language-option')) {
                const lang = event.target.getAttribute('data-lang');
                if (lang && window.i18n) {
                    window.i18n.setLanguage(lang);
                }
                this.hideLanguageDropdowns();
            }
        });

        // Close language dropdown when clicking outside
        document.addEventListener('click', (event) => {
            if (!event.target.closest('.language-selector, .nav-language')) {
                this.hideLanguageDropdowns();
            }
        });
    }

    /**
     * Setup sidebar event listeners
     */
    setupSidebarEventListeners() {
        // Sidebar toggle
        document.addEventListener('click', (event) => {
            if (event.target.matches('#sidebar-toggle, #mobile-sidebar-toggle')) {
                this.toggleSidebar();
            }
        });

        // Logout button
        document.addEventListener('click', (event) => {
            if (event.target.matches('#logout-btn')) {
                this.handleLogout();
            }
        });

        // Close sidebar on mobile when clicking outside
        document.addEventListener('click', (event) => {
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('sidebar');
                if (sidebar && !sidebar.contains(event.target) && !event.target.matches('#mobile-sidebar-toggle')) {
                    sidebar.classList.remove('open');
                }
            }
        });
    }

    /**
     * Setup WebSocket event listeners
     */
    setupWebSocketEventListeners() {
        window.addEventListener('wsMessage', (event) => {
            this.handleWebSocketMessage(event.detail);
        });
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + K for search
            if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
                event.preventDefault();
                this.focusSearch();
            }
            
            // Escape to close modals
            if (event.key === 'Escape') {
                this.closeModals();
            }
            
            // Alt + T for theme toggle
            if (event.altKey && event.key === 't') {
                event.preventDefault();
                this.toggleTheme();
            }
        });
    }

    /**
     * Check authentication status
     */
    async checkAuthentication() {
        const token = window.api.getStoredToken();
        
        if (!token) {
            this.showLoginPage();
            return;
        }

        try {
            const isValid = await window.api.validateToken();
            if (isValid) {
                this.isAuthenticated = true;
                await this.showMainApp();
            } else {
                this.showLoginPage();
            }
        } catch (error) {
            console.error('Token validation failed:', error);
            this.showLoginPage();
        }
    }

    /**
     * Handle login form submission
     */
    async handleLogin(event) {
        const formData = new FormData(event.target);
        const apiKey = formData.get('apiKey');
        
        if (!apiKey) {
            this.showLoginError('API key is required');
            return;
        }

        // Show loading state
        this.setLoginLoading(true);

        try {
            await window.api.login(apiKey);
            this.isAuthenticated = true;
            await this.showMainApp();
        } catch (error) {
            console.error('Login failed:', error);
            
            if (error.status === 401) {
                this.showLoginError(window.i18n?.t('login.invalidCredentials') || 'Invalid API key');
            } else if (error.isNetworkError()) {
                this.showLoginError(window.i18n?.t('login.connectionError') || 'Connection error');
            } else {
                this.showLoginError('Login failed. Please try again.');
            }
        } finally {
            this.setLoginLoading(false);
        }
    }

    /**
     * Handle logout
     */
    async handleLogout() {
        try {
            await window.api.logout();
        } catch (error) {
            console.warn('Logout request failed:', error);
        }
        
        this.isAuthenticated = false;
        this.cleanup();
        this.showLoginPage();
    }

    /**
     * Show login page
     */
    showLoginPage() {
        const loginPage = document.getElementById('login-page');
        const mainApp = document.getElementById('main-app');
        
        if (loginPage) loginPage.classList.remove('hidden');
        if (mainApp) mainApp.classList.add('hidden');
        
        // Focus on API key input
        setTimeout(() => {
            const apiKeyInput = document.getElementById('api-key');
            if (apiKeyInput) apiKeyInput.focus();
        }, 100);
    }

    /**
     * Show main application
     */
    async showMainApp() {
        const loginPage = document.getElementById('login-page');
        const mainApp = document.getElementById('main-app');
        
        if (loginPage) loginPage.classList.add('hidden');
        if (mainApp) mainApp.classList.remove('hidden');
        
        // Initialize router
        if (window.router) {
            await window.router.handleRoute();
        }
        
        // Setup WebSocket connection
        if (window.api) {
            window.api.setupWebSocket();
        }
        
        // Start real-time updates
        this.startRealTimeUpdates();
    }

    /**
     * Set login loading state
     */
    setLoginLoading(loading) {
        const loginBtn = document.getElementById('login-btn');
        const spinner = loginBtn?.querySelector('.btn-spinner');
        const text = loginBtn?.querySelector('span');
        
        if (loading) {
            if (spinner) spinner.classList.remove('hidden');
            if (text && window.i18n) text.textContent = window.i18n.t('login.signingIn');
            if (loginBtn) loginBtn.disabled = true;
        } else {
            if (spinner) spinner.classList.add('hidden');
            if (text && window.i18n) text.textContent = window.i18n.t('login.signIn');
            if (loginBtn) loginBtn.disabled = false;
        }
    }

    /**
     * Show login error
     */
    showLoginError(message) {
        const errorElement = document.getElementById('api-key-error');
        if (errorElement) {
            errorElement.textContent = message;
        }
        
        // Clear error after 5 seconds
        setTimeout(() => {
            if (errorElement) {
                errorElement.textContent = '';
            }
        }, 5000);
    }

    /**
     * Load theme preference
     */
    loadThemePreference() {
        const savedTheme = localStorage.getItem('openvpn-theme');
        this.currentTheme = savedTheme || 'light';
        this.applyTheme(this.currentTheme);
    }

    /**
     * Toggle theme
     */
    toggleTheme() {
        const themes = ['light', 'dark', 'auto'];
        const currentIndex = themes.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % themes.length;
        
        this.setTheme(themes[nextIndex]);
    }

    /**
     * Set theme
     */
    setTheme(theme) {
        this.currentTheme = theme;
        localStorage.setItem('openvpn-theme', theme);
        this.applyTheme(theme);
        
        // Emit theme change event
        window.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme }
        }));
    }

    /**
     * Apply theme to document
     */
    applyTheme(theme) {
        const body = document.body;
        const themeIcons = document.querySelectorAll('#theme-icon, #nav-theme-icon');
        
        // Remove existing theme classes
        body.classList.remove('theme-light', 'theme-dark', 'theme-auto');
        
        // Apply new theme
        body.classList.add(`theme-${theme}`);
        body.setAttribute('data-theme', theme);
        
        // Update theme icons
        let iconName = 'sun';
        if (theme === 'dark') {
            iconName = 'moon';
        } else if (theme === 'auto') {
            iconName = 'monitor';
        }
        
        themeIcons.forEach(icon => {
            icon.setAttribute('href', `assets/icons/sprite.svg#${iconName}`);
        });
    }

    /**
     * Toggle language dropdown
     */
    toggleLanguageDropdown(trigger) {
        const dropdown = trigger.nextElementSibling;
        if (dropdown) {
            dropdown.classList.toggle('hidden');
        }
    }

    /**
     * Hide language dropdowns
     */
    hideLanguageDropdowns() {
        const dropdowns = document.querySelectorAll('.language-dropdown, .nav-language-dropdown');
        dropdowns.forEach(dropdown => {
            dropdown.classList.add('hidden');
        });
    }

    /**
     * Handle language change
     */
    handleLanguageChange(language) {
        // Update document direction for RTL languages
        const html = document.documentElement;
        html.dir = window.i18n.isRTL() ? 'rtl' : 'ltr';
        
        // Update page title if on a specific page
        if (window.router && window.router.currentPage) {
            window.router.updatePageTitle(window.router.currentPage);
        }
        
        // Hide language dropdowns
        this.hideLanguageDropdowns();
    }

    /**
     * Toggle sidebar
     */
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (window.innerWidth <= 768) {
            // Mobile: slide sidebar in/out
            if (sidebar) {
                sidebar.classList.toggle('open');
            }
        } else {
            // Desktop: collapse/expand sidebar
            this.sidebarCollapsed = !this.sidebarCollapsed;
            
            if (sidebar) {
                sidebar.classList.toggle('collapsed', this.sidebarCollapsed);
            }
            
            if (mainContent) {
                mainContent.classList.toggle('sidebar-collapsed', this.sidebarCollapsed);
            }
            
            // Save preference
            localStorage.setItem('openvpn-sidebar-collapsed', this.sidebarCollapsed);
        }
    }

    /**
     * Handle WebSocket messages
     */
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'system_stats':
                this.updateSystemStats(data.payload);
                break;
            case 'user_update':
                this.updateUserData(data.payload);
                break;
            case 'service_status':
                this.updateServiceStatus(data.payload);
                break;
            case 'notification':
                this.showNotification(data.payload);
                break;
            default:
                console.log('Unknown WebSocket message:', data);
        }
    }

    /**
     * Update system statistics
     */
    updateSystemStats(stats) {
        // Update CPU usage
        const cpuElement = document.getElementById('cpu-percentage');
        const cpuProgress = document.getElementById('cpu-progress');
        if (cpuElement && stats.cpu !== undefined) {
            cpuElement.textContent = Math.round(stats.cpu);
            if (cpuProgress) {
                cpuProgress.style.width = `${stats.cpu}%`;
            }
        }
        
        // Update RAM usage
        const ramElement = document.getElementById('ram-percentage');
        const ramProgress = document.getElementById('ram-progress');
        if (ramElement && stats.memory !== undefined) {
            ramElement.textContent = Math.round(stats.memory);
            if (ramProgress) {
                ramProgress.style.width = `${stats.memory}%`;
            }
        }
        
        // Update storage usage
        const storageElement = document.getElementById('storage-percentage');
        const storageProgress = document.getElementById('storage-progress');
        if (storageElement && stats.storage !== undefined) {
            storageElement.textContent = Math.round(stats.storage);
            if (storageProgress) {
                storageProgress.style.width = `${stats.storage}%`;
            }
        }
        
        // Update user counts
        if (stats.users) {
            const onlineElement = document.getElementById('online-users-count');
            const activeElement = document.getElementById('active-users-count');
            const totalElement = document.getElementById('total-users-count');
            
            if (onlineElement) onlineElement.textContent = stats.users.online || 0;
            if (activeElement) activeElement.textContent = stats.users.active || 0;
            if (totalElement) totalElement.textContent = stats.users.total || 0;
        }
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        // Update every 30 seconds
        this.refreshInterval = setInterval(async () => {
            try {
                const stats = await window.api.getSystemStats();
                this.updateSystemStats(stats);
            } catch (error) {
                console.error('Failed to fetch system stats:', error);
            }
        }, 30000);
    }

    /**
     * Show notification
     */
    showNotification(notification) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${notification.type || 'info'}`;
        toast.innerHTML = `
            <div class="toast-content">
                <svg class="toast-icon" width="20" height="20">
                    <use href="assets/icons/sprite.svg#${this.getNotificationIcon(notification.type)}"></use>
                </svg>
                <div class="toast-message">
                    <div class="toast-title">${notification.title || ''}</div>
                    <div class="toast-text">${notification.message || ''}</div>
                </div>
                <button class="toast-close" onclick="this.parentElement.remove()">
                    <svg width="16" height="16">
                        <use href="assets/icons/sprite.svg#x"></use>
                    </svg>
                </button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Auto-remove after delay
        const delay = notification.duration || 5000;
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, delay);
    }

    /**
     * Get notification icon based on type
     */
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'information-circle'
        };
        return icons[type] || 'information-circle';
    }

    /**
     * Focus search input
     */
    focusSearch() {
        const searchInput = document.querySelector('input[type="search"], input[placeholder*="search"], input[placeholder*="Search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    /**
     * Close all modals
     */
    closeModals() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.add('hidden');
        });
    }

    /**
     * Hide loading screen
     */
    hideLoadingScreen() {
        const loadingScreen = document.getElementById('loading-screen');
        if (loadingScreen) {
            loadingScreen.style.opacity = '0';
            setTimeout(() => {
                loadingScreen.style.display = 'none';
            }, 300);
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showNotification({
            type: 'error',
            title: 'Error',
            message: message,
            duration: 10000
        });
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Clear intervals
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        
        // Close WebSocket
        if (window.api) {
            window.api.closeWebSocket();
        }
        
        // Cleanup router
        if (window.router) {
            window.router.cleanup();
        }
        
        // Destroy charts
        if (window.charts) {
            window.charts.destroyCharts();
        }
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});