/**
 * Client-side router for OpenVPN Manager
 * Handles hash-based routing and page management
 */

class Router {
    constructor() {
        this.routes = new Map();
        this.currentRoute = null;
        this.currentPage = null;
        this.middlewares = [];
        
        // Initialize router
        this.setupRoutes();
        this.setupEventListeners();
    }

    /**
     * Setup application routes
     */
    setupRoutes() {
        // Define all routes
        this.addRoute('', 'overview');
        this.addRoute('overview', 'overview');
        this.addRoute('users', 'users');
        this.addRoute('openvpn-settings', 'openvpn-settings');
        this.addRoute('charts', 'charts');
        this.addRoute('general-settings', 'general-settings');
    }

    /**
     * Add a route
     */
    addRoute(path, pageId, middleware = []) {
        this.routes.set(path, {
            pageId,
            middleware: Array.isArray(middleware) ? middleware : [middleware]
        });
    }

    /**
     * Add global middleware
     */
    use(middleware) {
        this.middlewares.push(middleware);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for hash changes
        window.addEventListener('hashchange', () => {
            this.handleRoute();
        });

        // Listen for page load
        window.addEventListener('load', () => {
            this.handleRoute();
        });

        // Listen for navigation clicks
        document.addEventListener('click', (event) => {
            const link = event.target.closest('[data-route]');
            if (link) {
                event.preventDefault();
                const route = link.getAttribute('data-route');
                this.navigate(route);
            }
        });
    }

    /**
     * Navigate to a route
     */
    navigate(path) {
        if (path === this.getCurrentPath()) {
            return;
        }
        
        window.location.hash = path;
    }

    /**
     * Get current path from hash
     */
    getCurrentPath() {
        return window.location.hash.slice(1) || '';
    }

    /**
     * Handle route change
     */
    async handleRoute() {
        const path = this.getCurrentPath();
        const route = this.routes.get(path);

        if (!route) {
            // Handle 404 - redirect to overview
            this.navigate('overview');
            return;
        }

        try {
            // Run global middlewares
            for (const middleware of this.middlewares) {
                const result = await middleware(path, route);
                if (result === false) {
                    return; // Middleware blocked navigation
                }
            }

            // Run route-specific middlewares
            for (const middleware of route.middleware) {
                const result = await middleware(path, route);
                if (result === false) {
                    return; // Middleware blocked navigation
                }
            }

            // Load the page
            await this.loadPage(route.pageId);
            
            // Update current route
            this.currentRoute = path;
            
            // Update navigation state
            this.updateNavigation();
            
            // Update page title
            this.updatePageTitle(route.pageId);
            
            // Emit route change event
            window.dispatchEvent(new CustomEvent('routeChanged', {
                detail: { path, pageId: route.pageId }
            }));
            
        } catch (error) {
            console.error('Route handling failed:', error);
            this.showError('Failed to load page');
        }
    }

    /**
     * Load page content
     */
    async loadPage(pageId) {
        const pageContent = document.getElementById('page-content');
        if (!pageContent) {
            throw new Error('Page content container not found');
        }

        // Show loading state
        pageContent.innerHTML = this.getLoadingHTML();

        try {
            // Generate page content based on pageId
            const content = await this.generatePageContent(pageId);
            
            // Update page content
            pageContent.innerHTML = content;
            
            // Initialize page-specific functionality
            await this.initializePage(pageId);
            
            // Update current page reference
            this.currentPage = pageId;
            
        } catch (error) {
            console.error(`Failed to load page ${pageId}:`, error);
            pageContent.innerHTML = this.getErrorHTML('Failed to load page');
        }
    }

    /**
     * Generate page content HTML
     */
    async generatePageContent(pageId) {
        switch (pageId) {
            case 'overview':
                return this.generateOverviewPage();
            case 'users':
                return this.generateUsersPage();
            case 'openvpn-settings':
                return this.generateOpenVPNSettingsPage();
            case 'charts':
                return this.generateChartsPage();
            case 'general-settings':
                return this.generateGeneralSettingsPage();
            default:
                throw new Error(`Unknown page: ${pageId}`);
        }
    }

    /**
     * Generate overview page content
     */
    generateOverviewPage() {
        return `
            <div class="overview-page">
                <!-- System Statistics -->
                <div class="stats-section mb-8">
                    <h2 class="text-xl font-semibold mb-4" data-i18n="pages.overview.systemStats">System Statistics</h2>
                    <div class="stats-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <div class="stat-card" id="cpu-card">
                            <div class="stat-header">
                                <h3 data-i18n="pages.overview.cpuUsage">CPU Usage</h3>
                                <svg class="stat-icon" width="24" height="24">
                                    <use href="assets/icons/sprite.svg#cpu"></use>
                                </svg>
                            </div>
                            <div class="stat-value">
                                <span id="cpu-percentage">--</span>%
                            </div>
                            <div class="stat-progress">
                                <div class="progress-bar" id="cpu-progress"></div>
                            </div>
                        </div>
                        
                        <div class="stat-card" id="ram-card">
                            <div class="stat-header">
                                <h3 data-i18n="pages.overview.ramUsage">RAM Usage</h3>
                                <svg class="stat-icon" width="24" height="24">
                                    <use href="assets/icons/sprite.svg#memory"></use>
                                </svg>
                            </div>
                            <div class="stat-value">
                                <span id="ram-percentage">--</span>%
                            </div>
                            <div class="stat-progress">
                                <div class="progress-bar" id="ram-progress"></div>
                            </div>
                        </div>
                        
                        <div class="stat-card" id="storage-card">
                            <div class="stat-header">
                                <h3 data-i18n="pages.overview.storageUsage">Storage Usage</h3>
                                <svg class="stat-icon" width="24" height="24">
                                    <use href="assets/icons/sprite.svg#storage"></use>
                                </svg>
                            </div>
                            <div class="stat-value">
                                <span id="storage-percentage">--</span>%
                            </div>
                            <div class="stat-progress">
                                <div class="progress-bar" id="storage-progress"></div>
                            </div>
                        </div>
                        
                        <div class="stat-card" id="online-users-card">
                            <div class="stat-header">
                                <h3 data-i18n="pages.overview.onlineUsers">Online Users</h3>
                                <svg class="stat-icon text-success-500" width="24" height="24">
                                    <use href="assets/icons/sprite.svg#users"></use>
                                </svg>
                            </div>
                            <div class="stat-value text-success-600">
                                <span id="online-users-count">--</span>
                            </div>
                        </div>
                        
                        <div class="stat-card" id="active-users-card">
                            <div class="stat-header">
                                <h3 data-i18n="pages.overview.activeUsers">Active Users</h3>
                                <svg class="stat-icon text-info-500" width="24" height="24">
                                    <use href="assets/icons/sprite.svg#user-check"></use>
                                </svg>
                            </div>
                            <div class="stat-value text-info-600">
                                <span id="active-users-count">--</span>
                            </div>
                        </div>
                        
                        <div class="stat-card" id="total-users-card">
                            <div class="stat-header">
                                <h3 data-i18n="pages.overview.totalUsers">Total Users</h3>
                                <svg class="stat-icon text-gray-500" width="24" height="24">
                                    <use href="assets/icons/sprite.svg#user-group"></use>
                                </svg>
                            </div>
                            <div class="stat-value text-gray-600">
                                <span id="total-users-count">--</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="quick-actions-section mb-8">
                    <h2 class="text-xl font-semibold mb-4" data-i18n="pages.overview.quickActions">Quick Actions</h2>
                    <div class="flex flex-wrap gap-4">
                        <button class="btn btn-primary" id="backup-btn">
                            <svg width="16" height="16">
                                <use href="assets/icons/sprite.svg#download"></use>
                            </svg>
                            <span data-i18n="pages.overview.backupNow">Backup Now</span>
                        </button>
                        <button class="btn btn-secondary" id="restore-btn">
                            <svg width="16" height="16">
                                <use href="assets/icons/sprite.svg#upload"></use>
                            </svg>
                            <span data-i18n="pages.overview.restoreSystem">Restore System</span>
                        </button>
                        <button class="btn btn-ghost" id="logs-btn">
                            <svg width="16" height="16">
                                <use href="assets/icons/sprite.svg#document-text"></use>
                            </svg>
                            <span data-i18n="pages.overview.viewLogs">View Logs</span>
                        </button>
                    </div>
                </div>

                <!-- Services Status -->
                <div class="services-section">
                    <h2 class="text-xl font-semibold mb-4" data-i18n="pages.overview.services">Services Status</h2>
                    <div class="services-table-container">
                        <table class="services-table" id="services-table">
                            <thead>
                                <tr>
                                    <th>Service</th>
                                    <th>Status</th>
                                    <th>Uptime</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="services-tbody">
                                <!-- Services will be loaded here -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Generate users page content
     */
    generateUsersPage() {
        return `
            <div class="users-page">
                <!-- Users Summary -->
                <div class="users-summary mb-6">
                    <div class="summary-cards grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="summary-card">
                            <div class="summary-header">
                                <h3 data-i18n="pages.users.online">Online</h3>
                                <div class="summary-indicator online"></div>
                            </div>
                            <div class="summary-value" id="summary-online">--</div>
                        </div>
                        <div class="summary-card">
                            <div class="summary-header">
                                <h3 data-i18n="pages.users.active">Active</h3>
                                <div class="summary-indicator active"></div>
                            </div>
                            <div class="summary-value" id="summary-active">--</div>
                        </div>
                        <div class="summary-card">
                            <div class="summary-header">
                                <h3 data-i18n="common.all">Total</h3>
                                <div class="summary-indicator total"></div>
                            </div>
                            <div class="summary-value" id="summary-total">--</div>
                        </div>
                    </div>
                </div>

                <!-- Users Controls -->
                <div class="users-controls mb-6">
                    <div class="flex flex-col md:flex-row gap-4 justify-between">
                        <div class="flex gap-4">
                            <button class="btn btn-primary" id="create-user-btn">
                                <svg width="16" height="16">
                                    <use href="assets/icons/sprite.svg#plus"></use>
                                </svg>
                                <span data-i18n="pages.users.createUser">Create User</span>
                            </button>
                            <button class="btn btn-secondary" id="import-users-btn">
                                <svg width="16" height="16">
                                    <use href="assets/icons/sprite.svg#upload"></use>
                                </svg>
                                <span data-i18n="pages.users.importUsers">Import Users</span>
                            </button>
                            <button class="btn btn-ghost" id="export-users-btn">
                                <svg width="16" height="16">
                                    <use href="assets/icons/sprite.svg#download"></use>
                                </svg>
                                <span data-i18n="pages.users.exportUsers">Export Users</span>
                            </button>
                        </div>
                        
                        <div class="flex gap-4">
                            <div class="search-box">
                                <input type="text" id="users-search" placeholder="Search users..." data-i18n-placeholder="pages.users.searchUsers">
                                <svg class="search-icon" width="16" height="16">
                                    <use href="assets/icons/sprite.svg#search"></use>
                                </svg>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Users Table -->
                <div class="users-table-container">
                    <table class="users-table" id="users-table">
                        <thead>
                            <tr>
                                <th class="checkbox-column">
                                    <input type="checkbox" id="select-all-users">
                                </th>
                                <th data-i18n="pages.users.username">Username</th>
                                <th data-i18n="pages.users.status">Status</th>
                                <th data-i18n="pages.users.protocol">Protocol</th>
                                <th data-i18n="pages.users.dataUsage">Data Usage</th>
                                <th data-i18n="pages.users.quota">Quota</th>
                                <th data-i18n="pages.users.actions">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="users-tbody">
                            <!-- Users will be loaded here -->
                        </tbody>
                    </table>
                </div>

                <!-- Pagination -->
                <div class="pagination-container" id="users-pagination">
                    <!-- Pagination will be loaded here -->
                </div>
            </div>
        `;
    }

    /**
     * Generate OpenVPN settings page content
     */
    generateOpenVPNSettingsPage() {
        return `
            <div class="openvpn-settings-page">
                <div class="settings-container">
                    <div class="settings-header mb-6">
                        <h2 class="text-xl font-semibold" data-i18n="pages.openvpnSettings.currentSettings">Current Settings</h2>
                        <p class="text-gray-600" data-i18n="pages.openvpnSettings.serviceWillRestart">Warning: Applying changes will restart the OpenVPN service.</p>
                    </div>

                    <form id="openvpn-settings-form" class="settings-form">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="server-port" data-i18n="pages.openvpnSettings.serverPort">Server Port</label>
                                <input type="number" id="server-port" name="port" min="1" max="65535" required>
                            </div>

                            <div class="form-group">
                                <label for="protocol" data-i18n="pages.openvpnSettings.protocol">Protocol</label>
                                <select id="protocol" name="protocol" required>
                                    <option value="udp">UDP</option>
                                    <option value="tcp">TCP</option>
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="dns-server" data-i18n="pages.openvpnSettings.dnsSettings">DNS Settings</label>
                                <select id="dns-server" name="dns">
                                    <option value="8.8.8.8,8.8.4.4">Google DNS</option>
                                    <option value="1.1.1.1,1.0.0.1">Cloudflare DNS</option>
                                    <option value="208.67.222.222,208.67.220.220">OpenDNS</option>
                                    <option value="custom">Custom</option>
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="cipher" data-i18n="pages.openvpnSettings.cipherSelection">Cipher Selection</label>
                                <select id="cipher" name="cipher" required>
                                    <option value="AES-256-GCM">AES-256-GCM (Recommended)</option>
                                    <option value="AES-128-GCM">AES-128-GCM</option>
                                    <option value="ChaCha20-Poly1305">ChaCha20-Poly1305</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">
                                <span data-i18n="pages.openvpnSettings.applyChanges">Apply Changes</span>
                            </button>
                            <button type="button" class="btn btn-secondary" id="reset-settings-btn">
                                <span data-i18n="pages.openvpnSettings.resetToDefaults">Reset to Defaults</span>
                            </button>
                            <button type="button" class="btn btn-ghost" id="backup-config-btn">
                                <span data-i18n="pages.openvpnSettings.backupConfig">Backup Configuration</span>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    /**
     * Generate charts page content
     */
    generateChartsPage() {
        return `
            <div class="charts-page">
                <!-- Time Range Selector -->
                <div class="time-range-section mb-6">
                    <div class="flex flex-wrap gap-4 items-center">
                        <h2 class="text-xl font-semibold" data-i18n="pages.charts.timeRange">Time Range</h2>
                        <div class="time-range-buttons">
                            <button class="btn btn-sm btn-ghost active" data-range="daily" data-i18n="pages.charts.daily">Daily</button>
                            <button class="btn btn-sm btn-ghost" data-range="weekly" data-i18n="pages.charts.weekly">Weekly</button>
                            <button class="btn btn-sm btn-ghost" data-range="monthly" data-i18n="pages.charts.monthly">Monthly</button>
                        </div>
                    </div>
                </div>

                <!-- Charts Grid -->
                <div class="charts-grid">
                    <!-- Traffic Analysis -->
                    <div class="chart-section">
                        <h3 class="chart-title" data-i18n="pages.charts.trafficAnalysis">Traffic Analysis</h3>
                        <div class="chart-container">
                            <canvas id="traffic-chart"></canvas>
                        </div>
                    </div>

                    <!-- User Activity -->
                    <div class="chart-section">
                        <h3 class="chart-title" data-i18n="pages.charts.userActivity">User Activity</h3>
                        <div class="chart-container">
                            <canvas id="user-activity-chart"></canvas>
                        </div>
                    </div>

                    <!-- System Performance -->
                    <div class="chart-section">
                        <h3 class="chart-title" data-i18n="pages.charts.systemPerformance">System Performance</h3>
                        <div class="chart-container">
                            <canvas id="system-performance-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Generate general settings page content
     */
    generateGeneralSettingsPage() {
        return `
            <div class="general-settings-page">
                <div class="settings-sections">
                    <!-- Appearance Settings -->
                    <div class="settings-section">
                        <h2 class="section-title" data-i18n="pages.generalSettings.appearance">Appearance</h2>
                        <div class="settings-grid">
                            <div class="setting-item">
                                <label data-i18n="pages.generalSettings.theme">Theme</label>
                                <select id="theme-setting">
                                    <option value="light" data-i18n="pages.generalSettings.light">Light</option>
                                    <option value="dark" data-i18n="pages.generalSettings.dark">Dark</option>
                                    <option value="auto" data-i18n="pages.generalSettings.auto">Auto</option>
                                </select>
                            </div>
                            <div class="setting-item">
                                <label data-i18n="pages.generalSettings.language">Language</label>
                                <select id="language-setting">
                                    <option value="en">English</option>
                                    <option value="fa">فارسی</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Security Settings -->
                    <div class="settings-section">
                        <h2 class="section-title" data-i18n="pages.generalSettings.security">Security</h2>
                        <div class="settings-grid">
                            <div class="setting-item">
                                <label data-i18n="pages.generalSettings.sessionTimeout">Session Timeout (minutes)</label>
                                <input type="number" id="session-timeout" min="5" max="1440" value="60">
                            </div>
                            <div class="setting-item">
                                <label data-i18n="pages.generalSettings.apiKeyManagement">API Key Management</label>
                                <div class="api-key-actions">
                                    <button class="btn btn-sm btn-secondary" id="view-api-key-btn" data-i18n="pages.generalSettings.viewApiKey">View API Key</button>
                                    <button class="btn btn-sm btn-warning" id="generate-api-key-btn" data-i18n="pages.generalSettings.generateNewKey">Generate New Key</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- System Settings -->
                    <div class="settings-section">
                        <h2 class="section-title" data-i18n="pages.generalSettings.system">System</h2>
                        <div class="settings-grid">
                            <div class="setting-item">
                                <label data-i18n="pages.generalSettings.automaticBackup">Automatic Backup</label>
                                <div class="toggle-switch">
                                    <input type="checkbox" id="auto-backup-toggle">
                                    <span class="slider"></span>
                                </div>
                            </div>
                            <div class="setting-item">
                                <label data-i18n="pages.generalSettings.logRetention">Log Retention (days)</label>
                                <input type="number" id="log-retention" min="1" max="365" value="30">
                            </div>
                        </div>
                    </div>
                </div>

                <div class="settings-actions">
                    <button class="btn btn-primary" id="save-settings-btn">
                        <span data-i18n="pages.generalSettings.saveSettings">Save Settings</span>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Initialize page-specific functionality
     */
    async initializePage(pageId) {
        // Update i18n elements
        if (window.i18n) {
            window.i18n.updateElements();
        }

        // Initialize page-specific features
        switch (pageId) {
            case 'overview':
                await this.initializeOverviewPage();
                break;
            case 'users':
                await this.initializeUsersPage();
                break;
            case 'openvpn-settings':
                await this.initializeOpenVPNSettingsPage();
                break;
            case 'charts':
                await this.initializeChartsPage();
                break;
            case 'general-settings':
                await this.initializeGeneralSettingsPage();
                break;
        }
    }

    /**
     * Initialize overview page
     */
    async initializeOverviewPage() {
        try {
            // Load system stats
            const stats = await window.api.getSystemStats();
            this.updateSystemStats(stats);

            // Load services status
            const services = await window.api.getSystemServices();
            this.updateServicesTable(services);

            // Setup auto-refresh
            this.setupAutoRefresh('overview');
        } catch (error) {
            console.error('Failed to initialize overview page:', error);
        }
    }

    /**
     * Initialize users page
     */
    async initializeUsersPage() {
        try {
            // Load users data
            await this.loadUsersData();

            // Setup event listeners
            this.setupUsersEventListeners();
        } catch (error) {
            console.error('Failed to initialize users page:', error);
        }
    }

    /**
     * Initialize OpenVPN settings page
     */
    async initializeOpenVPNSettingsPage() {
        try {
            // Load current settings
            const settings = await window.api.getOpenVPNSettings();
            this.populateOpenVPNSettings(settings);

            // Setup form handler
            this.setupOpenVPNSettingsForm();
        } catch (error) {
            console.error('Failed to initialize OpenVPN settings page:', error);
        }
    }

    /**
     * Initialize charts page
     */
    async initializeChartsPage() {
        try {
            // Initialize charts
            if (window.charts) {
                await window.charts.initializeCharts();
            }
        } catch (error) {
            console.error('Failed to initialize charts page:', error);
        }
    }

    /**
     * Initialize general settings page
     */
    async initializeGeneralSettingsPage() {
        try {
            // Load current settings
            const settings = await window.api.getSettings();
            this.populateGeneralSettings(settings);

            // Setup form handlers
            this.setupGeneralSettingsForm();
        } catch (error) {
            console.error('Failed to initialize general settings page:', error);
        }
    }

    /**
     * Update navigation active state
     */
    updateNavigation() {
        // Remove active class from all nav links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });

        // Add active class to current route
        const activeLink = document.querySelector(`[data-route="${this.currentRoute}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }

    /**
     * Update page title
     */
    updatePageTitle(pageId) {
        const titleElement = document.getElementById('page-title');
        if (titleElement && window.i18n) {
            const titleKey = `pages.${pageId}.title`;
            titleElement.textContent = window.i18n.t(titleKey);
            titleElement.setAttribute('data-i18n', titleKey);
        }
    }

    /**
     * Get loading HTML
     */
    getLoadingHTML() {
        return `
            <div class="loading-container">
                <div class="spinner"></div>
                <p data-i18n="common.loading">Loading...</p>
            </div>
        `;
    }

    /**
     * Get error HTML
     */
    getErrorHTML(message) {
        return `
            <div class="error-container">
                <svg width="48" height="48" class="error-icon">
                    <use href="assets/icons/sprite.svg#exclamation-triangle"></use>
                </svg>
                <h3>Error</h3>
                <p>${message}</p>
                <button class="btn btn-primary" onclick="location.reload()">
                    <span data-i18n="common.refresh">Refresh</span>
                </button>
            </div>
        `;
    }

    /**
     * Show error message
     */
    showError(message) {
        const pageContent = document.getElementById('page-content');
        if (pageContent) {
            pageContent.innerHTML = this.getErrorHTML(message);
        }
    }

    /**
     * Setup auto-refresh for data
     */
    setupAutoRefresh(pageId) {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        // Setup new interval based on page
        const refreshRate = this.getRefreshRate(pageId);
        if (refreshRate > 0) {
            this.refreshInterval = setInterval(() => {
                this.refreshPageData(pageId);
            }, refreshRate);
        }
    }

    /**
     * Get refresh rate for page
     */
    getRefreshRate(pageId) {
        const rates = {
            'overview': 30000, // 30 seconds
            'users': 60000,    // 1 minute
            'charts': 30000    // 30 seconds
        };
        return rates[pageId] || 0;
    }

    /**
     * Refresh page data
     */
    async refreshPageData(pageId) {
        if (this.currentPage !== pageId) {
            return; // Page has changed, don't refresh
        }

        try {
            switch (pageId) {
                case 'overview':
                    const stats = await window.api.getSystemStats();
                    this.updateSystemStats(stats);
                    break;
                case 'users':
                    await this.loadUsersData();
                    break;
                case 'charts':
                    if (window.charts) {
                        await window.charts.refreshCharts();
                    }
                    break;
            }
        } catch (error) {
            console.error('Failed to refresh page data:', error);
        }
    }

    /**
     * Cleanup when page changes
     */
    cleanup() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

// Create global router instance
window.router = new Router();