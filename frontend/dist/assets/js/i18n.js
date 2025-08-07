/**
 * Internationalization system for OpenVPN Manager
 * Supports English and Persian (Farsi) languages with RTL support
 */

class I18n {
    constructor() {
        this.currentLanguage = 'en';
        this.translations = {};
        this.rtlLanguages = ['fa', 'ar', 'he'];
        this.fallbackLanguage = 'en';
        
        // Load saved language preference
        this.loadLanguagePreference();
        
        // Initialize translations
        this.loadTranslations();
    }

    /**
     * Load language preference from localStorage
     */
    loadLanguagePreference() {
        const saved = localStorage.getItem('openvpn-language');
        if (saved && this.isValidLanguage(saved)) {
            this.currentLanguage = saved;
        } else {
            // Detect browser language
            const browserLang = navigator.language.split('-')[0];
            if (this.isValidLanguage(browserLang)) {
                this.currentLanguage = browserLang;
            }
        }
    }

    /**
     * Check if language code is supported
     */
    isValidLanguage(lang) {
        return ['en', 'fa'].includes(lang);
    }

    /**
     * Load all translations
     */
    async loadTranslations() {
        try {
            // English translations
            this.translations.en = {
                // Login page
                login: {
                    title: 'OpenVPN Manager',
                    subtitle: 'Secure VPN Management Dashboard',
                    apiKey: 'API Key',
                    apiKeyPlaceholder: 'Enter your API key',
                    signIn: 'Sign In',
                    invalidCredentials: 'Invalid API key. Please try again.',
                    connectionError: 'Connection error. Please check your network.',
                    signingIn: 'Signing in...'
                },
                
                // Navigation
                nav: {
                    overview: 'Overview',
                    users: 'Users',
                    openvpnSettings: 'OpenVPN Settings',
                    charts: 'Charts & Usage',
                    generalSettings: 'General Settings'
                },
                
                // Pages
                pages: {
                    overview: {
                        title: 'Overview',
                        systemStats: 'System Statistics',
                        cpuUsage: 'CPU Usage',
                        ramUsage: 'RAM Usage',
                        storageUsage: 'Storage Usage',
                        onlineUsers: 'Online Users',
                        activeUsers: 'Active Users',
                        totalUsers: 'Total Users',
                        alerts: 'System Alerts',
                        services: 'Services Status',
                        quickActions: 'Quick Actions',
                        backupNow: 'Backup Now',
                        restoreSystem: 'Restore System',
                        viewLogs: 'View Logs',
                        trafficOverview: 'Traffic Overview',
                        userActivity: 'User Activity',
                        systemHealth: 'System Health'
                    },
                    users: {
                        title: 'Users Management',
                        summary: 'Users Summary',
                        createUser: 'Create User',
                        editUser: 'Edit User',
                        deleteUser: 'Delete User',
                        changePassword: 'Change Password',
                        setQuota: 'Set Quota',
                        downloadConfig: 'Download Config',
                        username: 'Username',
                        status: 'Status',
                        protocol: 'Protocol',
                        dataUsage: 'Data Usage',
                        quota: 'Quota',
                        actions: 'Actions',
                        online: 'Online',
                        offline: 'Offline',
                        active: 'Active',
                        inactive: 'Inactive',
                        unlimited: 'Unlimited',
                        searchUsers: 'Search users...',
                        exportUsers: 'Export Users',
                        importUsers: 'Import Users',
                        bulkActions: 'Bulk Actions',
                        selectAll: 'Select All',
                        deleteSelected: 'Delete Selected',
                        confirmDelete: 'Are you sure you want to delete this user?',
                        confirmBulkDelete: 'Are you sure you want to delete selected users?',
                        userCreated: 'User created successfully',
                        userUpdated: 'User updated successfully',
                        userDeleted: 'User deleted successfully',
                        usersDeleted: 'Users deleted successfully'
                    },
                    openvpnSettings: {
                        title: 'OpenVPN Settings',
                        currentSettings: 'Current Settings',
                        serverPort: 'Server Port',
                        protocol: 'Protocol',
                        dnsSettings: 'DNS Settings',
                        cipherSelection: 'Cipher Selection',
                        certificateSettings: 'Certificate Settings',
                        applyChanges: 'Apply Changes',
                        resetToDefaults: 'Reset to Defaults',
                        backupConfig: 'Backup Configuration',
                        restoreConfig: 'Restore Configuration',
                        restartService: 'Restart Service',
                        serviceWillRestart: 'Warning: Applying changes will restart the OpenVPN service.',
                        configurationBackup: 'Configuration will be backed up before applying changes.',
                        settingsUpdated: 'Settings updated successfully',
                        servicerestarted: 'OpenVPN service restarted'
                    },
                    charts: {
                        title: 'Charts & Analytics',
                        timeRange: 'Time Range',
                        daily: 'Daily',
                        weekly: 'Weekly',
                        monthly: 'Monthly',
                        custom: 'Custom Range',
                        trafficAnalysis: 'Traffic Analysis',
                        uploadTraffic: 'Upload Traffic',
                        downloadTraffic: 'Download Traffic',
                        totalTraffic: 'Total Traffic',
                        peakUsage: 'Peak Usage',
                        userActivity: 'User Activity',
                        activeSessions: 'Active Sessions',
                        topUsers: 'Top Users by Data Usage',
                        connectionDuration: 'Connection Duration',
                        systemPerformance: 'System Performance',
                        cpuTrend: 'CPU Usage Trend',
                        memoryTrend: 'Memory Usage Trend',
                        storageTrend: 'Storage Growth',
                        serviceAvailability: 'Service Availability',
                        exportChart: 'Export Chart',
                        exportData: 'Export Data',
                        generateReport: 'Generate Report'
                    },
                    generalSettings: {
                        title: 'General Settings',
                        appearance: 'Appearance',
                        theme: 'Theme',
                        language: 'Language',
                        uiDensity: 'UI Density',
                        light: 'Light',
                        dark: 'Dark',
                        auto: 'Auto',
                        compact: 'Compact',
                        comfortable: 'Comfortable',
                        security: 'Security',
                        apiKeyManagement: 'API Key Management',
                        sessionTimeout: 'Session Timeout',
                        ipRestrictions: 'IP Access Restrictions',
                        twoFactorAuth: 'Two-Factor Authentication',
                        system: 'System',
                        automaticBackup: 'Automatic Backup',
                        logRetention: 'Log Retention Period',
                        notifications: 'Notification Preferences',
                        updateCheck: 'Update Check',
                        viewApiKey: 'View API Key',
                        generateNewKey: 'Generate New Key',
                        revokeKey: 'Revoke Key',
                        enable: 'Enable',
                        disable: 'Disable',
                        saveSettings: 'Save Settings',
                        settingsSaved: 'Settings saved successfully'
                    }
                },
                
                // Common elements
                common: {
                    save: 'Save',
                    cancel: 'Cancel',
                    delete: 'Delete',
                    edit: 'Edit',
                    create: 'Create',
                    update: 'Update',
                    close: 'Close',
                    confirm: 'Confirm',
                    loading: 'Loading...',
                    error: 'Error',
                    success: 'Success',
                    warning: 'Warning',
                    info: 'Information',
                    yes: 'Yes',
                    no: 'No',
                    ok: 'OK',
                    search: 'Search',
                    filter: 'Filter',
                    sort: 'Sort',
                    export: 'Export',
                    import: 'Import',
                    download: 'Download',
                    upload: 'Upload',
                    refresh: 'Refresh',
                    reset: 'Reset',
                    apply: 'Apply',
                    back: 'Back',
                    next: 'Next',
                    previous: 'Previous',
                    first: 'First',
                    last: 'Last',
                    page: 'Page',
                    of: 'of',
                    items: 'items',
                    selected: 'selected',
                    all: 'All',
                    none: 'None'
                },
                
                // Status and messages
                status: {
                    connected: 'Connected',
                    disconnected: 'Disconnected',
                    connecting: 'Connecting...',
                    online: 'Online',
                    offline: 'Offline',
                    active: 'Active',
                    inactive: 'Inactive',
                    running: 'Running',
                    stopped: 'Stopped',
                    starting: 'Starting',
                    stopping: 'Stopping',
                    healthy: 'Healthy',
                    unhealthy: 'Unhealthy',
                    warning: 'Warning',
                    critical: 'Critical'
                },
                
                // Time and dates
                time: {
                    now: 'Now',
                    today: 'Today',
                    yesterday: 'Yesterday',
                    thisWeek: 'This Week',
                    lastWeek: 'Last Week',
                    thisMonth: 'This Month',
                    lastMonth: 'Last Month',
                    seconds: 'seconds',
                    minutes: 'minutes',
                    hours: 'hours',
                    days: 'days',
                    weeks: 'weeks',
                    months: 'months',
                    years: 'years',
                    ago: 'ago'
                }
            };

            // Persian translations
            this.translations.fa = {
                // Login page
                login: {
                    title: 'مدیریت OpenVPN',
                    subtitle: 'داشبورد مدیریت امن VPN',
                    apiKey: 'کلید API',
                    apiKeyPlaceholder: 'کلید API خود را وارد کنید',
                    signIn: 'ورود',
                    invalidCredentials: 'کلید API نامعتبر است. لطفا دوباره تلاش کنید.',
                    connectionError: 'خطا در اتصال. لطفا اتصال اینترنت خود را بررسی کنید.',
                    signingIn: 'در حال ورود...'
                },
                
                // Navigation
                nav: {
                    overview: 'نمای کلی',
                    users: 'کاربران',
                    openvpnSettings: 'تنظیمات OpenVPN',
                    charts: 'نمودارها و استفاده',
                    generalSettings: 'تنظیمات عمومی'
                },
                
                // Pages
                pages: {
                    overview: {
                        title: 'نمای کلی',
                        systemStats: 'آمار سیستم',
                        cpuUsage: 'استفاده از پردازنده',
                        ramUsage: 'استفاده از حافظه',
                        storageUsage: 'استفاده از فضای ذخیره',
                        onlineUsers: 'کاربران آنلاین',
                        activeUsers: 'کاربران فعال',
                        totalUsers: 'کل کاربران',
                        alerts: 'هشدارهای سیستم',
                        services: 'وضعیت سرویس‌ها',
                        quickActions: 'عملیات سریع',
                        backupNow: 'پشتیبان‌گیری',
                        restoreSystem: 'بازیابی سیستم',
                        viewLogs: 'مشاهده لاگ‌ها',
                        trafficOverview: 'نمای کلی ترافیک',
                        userActivity: 'فعالیت کاربران',
                        systemHealth: 'سلامت سیستم'
                    },
                    users: {
                        title: 'مدیریت کاربران',
                        summary: 'خلاصه کاربران',
                        createUser: 'ایجاد کاربر',
                        editUser: 'ویرایش کاربر',
                        deleteUser: 'حذف کاربر',
                        changePassword: 'تغییر رمز عبور',
                        setQuota: 'تعیین سهمیه',
                        downloadConfig: 'دانلود پیکربندی',
                        username: 'نام کاربری',
                        status: 'وضعیت',
                        protocol: 'پروتکل',
                        dataUsage: 'مصرف داده',
                        quota: 'سهمیه',
                        actions: 'عملیات',
                        online: 'آنلاین',
                        offline: 'آفلاین',
                        active: 'فعال',
                        inactive: 'غیرفعال',
                        unlimited: 'نامحدود',
                        searchUsers: 'جستجوی کاربران...',
                        exportUsers: 'خروجی کاربران',
                        importUsers: 'وارد کردن کاربران',
                        bulkActions: 'عملیات گروهی',
                        selectAll: 'انتخاب همه',
                        deleteSelected: 'حذف انتخاب شده‌ها',
                        confirmDelete: 'آیا مطمئن هستید که می‌خواهید این کاربر را حذف کنید؟',
                        confirmBulkDelete: 'آیا مطمئن هستید که می‌خواهید کاربران انتخاب شده را حذف کنید؟',
                        userCreated: 'کاربر با موفقیت ایجاد شد',
                        userUpdated: 'کاربر با موفقیت به‌روزرسانی شد',
                        userDeleted: 'کاربر با موفقیت حذف شد',
                        usersDeleted: 'کاربران با موفقیت حذف شدند'
                    },
                    openvpnSettings: {
                        title: 'تنظیمات OpenVPN',
                        currentSettings: 'تنظیمات فعلی',
                        serverPort: 'پورت سرور',
                        protocol: 'پروتکل',
                        dnsSettings: 'تنظیمات DNS',
                        cipherSelection: 'انتخاب رمزنگاری',
                        certificateSettings: 'تنظیمات گواهی',
                        applyChanges: 'اعمال تغییرات',
                        resetToDefaults: 'بازنشانی به پیش‌فرض',
                        backupConfig: 'پشتیبان‌گیری پیکربندی',
                        restoreConfig: 'بازیابی پیکربندی',
                        restartService: 'راه‌اندازی مجدد سرویس',
                        serviceWillRestart: 'هشدار: اعمال تغییرات باعث راه‌اندازی مجدد سرویس OpenVPN می‌شود.',
                        configurationBackup: 'پیکربندی قبل از اعمال تغییرات پشتیبان‌گیری می‌شود.',
                        settingsUpdated: 'تنظیمات با موفقیت به‌روزرسانی شد',
                        servicerestarted: 'سرویس OpenVPN مجدداً راه‌اندازی شد'
                    },
                    charts: {
                        title: 'نمودارها و تحلیل‌ها',
                        timeRange: 'بازه زمانی',
                        daily: 'روزانه',
                        weekly: 'هفتگی',
                        monthly: 'ماهانه',
                        custom: 'بازه سفارشی',
                        trafficAnalysis: 'تحلیل ترافیک',
                        uploadTraffic: 'ترافیک آپلود',
                        downloadTraffic: 'ترافیک دانلود',
                        totalTraffic: 'کل ترافیک',
                        peakUsage: 'اوج مصرف',
                        userActivity: 'فعالیت کاربران',
                        activeSessions: 'جلسات فعال',
                        topUsers: 'کاربران پرمصرف',
                        connectionDuration: 'مدت اتصال',
                        systemPerformance: 'عملکرد سیستم',
                        cpuTrend: 'روند استفاده از پردازنده',
                        memoryTrend: 'روند استفاده از حافظه',
                        storageTrend: 'رشد فضای ذخیره',
                        serviceAvailability: 'در دسترس بودن سرویس',
                        exportChart: 'خروجی نمودار',
                        exportData: 'خروجی داده‌ها',
                        generateReport: 'تولید گزارش'
                    },
                    generalSettings: {
                        title: 'تنظیمات عمومی',
                        appearance: 'ظاهر',
                        theme: 'تم',
                        language: 'زبان',
                        uiDensity: 'تراکم رابط کاربری',
                        light: 'روشن',
                        dark: 'تیره',
                        auto: 'خودکار',
                        compact: 'فشرده',
                        comfortable: 'راحت',
                        security: 'امنیت',
                        apiKeyManagement: 'مدیریت کلید API',
                        sessionTimeout: 'مهلت نشست',
                        ipRestrictions: 'محدودیت‌های IP',
                        twoFactorAuth: 'تأیید دو مرحله‌ای',
                        system: 'سیستم',
                        automaticBackup: 'پشتیبان‌گیری خودکار',
                        logRetention: 'مدت نگهداری لاگ‌ها',
                        notifications: 'تنظیمات اعلان‌ها',
                        updateCheck: 'بررسی به‌روزرسانی',
                        viewApiKey: 'مشاهده کلید API',
                        generateNewKey: 'تولید کلید جدید',
                        revokeKey: 'لغو کلید',
                        enable: 'فعال',
                        disable: 'غیرفعال',
                        saveSettings: 'ذخیره تنظیمات',
                        settingsSaved: 'تنظیمات با موفقیت ذخیره شد'
                    }
                },
                
                // Common elements
                common: {
                    save: 'ذخیره',
                    cancel: 'لغو',
                    delete: 'حذف',
                    edit: 'ویرایش',
                    create: 'ایجاد',
                    update: 'به‌روزرسانی',
                    close: 'بستن',
                    confirm: 'تأیید',
                    loading: 'در حال بارگذاری...',
                    error: 'خطا',
                    success: 'موفقیت',
                    warning: 'هشدار',
                    info: 'اطلاعات',
                    yes: 'بله',
                    no: 'خیر',
                    ok: 'تأیید',
                    search: 'جستجو',
                    filter: 'فیلتر',
                    sort: 'مرتب‌سازی',
                    export: 'خروجی',
                    import: 'ورودی',
                    download: 'دانلود',
                    upload: 'آپلود',
                    refresh: 'تازه‌سازی',
                    reset: 'بازنشانی',
                    apply: 'اعمال',
                    back: 'بازگشت',
                    next: 'بعدی',
                    previous: 'قبلی',
                    first: 'اول',
                    last: 'آخر',
                    page: 'صفحه',
                    of: 'از',
                    items: 'آیتم',
                    selected: 'انتخاب شده',
                    all: 'همه',
                    none: 'هیچ‌کدام'
                },
                
                // Status and messages
                status: {
                    connected: 'متصل',
                    disconnected: 'قطع شده',
                    connecting: 'در حال اتصال...',
                    online: 'آنلاین',
                    offline: 'آفلاین',
                    active: 'فعال',
                    inactive: 'غیرفعال',
                    running: 'در حال اجرا',
                    stopped: 'متوقف شده',
                    starting: 'در حال شروع',
                    stopping: 'در حال توقف',
                    healthy: 'سالم',
                    unhealthy: 'ناسالم',
                    warning: 'هشدار',
                    critical: 'بحرانی'
                },
                
                // Time and dates
                time: {
                    now: 'اکنون',
                    today: 'امروز',
                    yesterday: 'دیروز',
                    thisWeek: 'این هفته',
                    lastWeek: 'هفته گذشته',
                    thisMonth: 'این ماه',
                    lastMonth: 'ماه گذشته',
                    seconds: 'ثانیه',
                    minutes: 'دقیقه',
                    hours: 'ساعت',
                    days: 'روز',
                    weeks: 'هفته',
                    months: 'ماه',
                    years: 'سال',
                    ago: 'پیش'
                }
            };

            // Apply initial language
            this.applyLanguage();
            
            // Dispatch ready event to prevent race conditions
            window.dispatchEvent(new CustomEvent('i18nReady', {
                detail: { language: this.currentLanguage }
            }));
            
        } catch (error) {
            console.error('Failed to load translations:', error);
            
            // Dispatch ready event even on error
            window.dispatchEvent(new CustomEvent('i18nReady', {
                detail: { language: this.currentLanguage, error: true }
            }));
        }
    }

    /**
     * Get translation for a key
     */
    t(key, params = {}) {
        const keys = key.split('.');
        let value = this.translations[this.currentLanguage];
        
        for (const k of keys) {
            if (value && typeof value === 'object') {
                value = value[k];
            } else {
                value = null;
                break;
            }
        }
        
        // Fallback to English if translation not found
        if (value === null && this.currentLanguage !== this.fallbackLanguage) {
            let fallbackValue = this.translations[this.fallbackLanguage];
            for (const k of keys) {
                if (fallbackValue && typeof fallbackValue === 'object') {
                    fallbackValue = fallbackValue[k];
                } else {
                    fallbackValue = null;
                    break;
                }
            }
            value = fallbackValue;
        }
        
        // If still no translation found, return empty string to prevent "undefined"
        if (value === null) {
            console.warn(`Translation not found for key: ${key}`);
            return '';
        }
        
        // Replace parameters in translation
        if (typeof value === 'string' && Object.keys(params).length > 0) {
            return this.interpolate(value, params);
        }
        
        return value;
    }

    /**
     * Interpolate parameters in translation string
     */
    interpolate(text, params) {
        return text.replace(/\{\{(\w+)\}\}/g, (match, key) => {
            return params.hasOwnProperty(key) ? params[key] : match;
        });
    }

    /**
     * Set current language
     */
    setLanguage(lang) {
        if (!this.isValidLanguage(lang)) {
            console.warn(`Unsupported language: ${lang}`);
            return;
        }
        
        this.currentLanguage = lang;
        localStorage.setItem('openvpn-language', lang);
        this.applyLanguage();
        
        // Emit language change event
        window.dispatchEvent(new CustomEvent('languageChanged', {
            detail: { language: lang }
        }));
    }

    /**
     * Get current language
     */
    getCurrentLanguage() {
        return this.currentLanguage;
    }

    /**
     * Check if current language is RTL
     */
    isRTL() {
        return this.rtlLanguages.includes(this.currentLanguage);
    }

    /**
     * Apply language to the document
     */
    applyLanguage() {
        const html = document.documentElement;
        const body = document.body;
        
        // Set language attributes
        html.lang = this.currentLanguage;
        html.dir = this.isRTL() ? 'rtl' : 'ltr';
        
        // Update all elements with data-i18n attributes
        this.updateElements();
        
        // Update language flags in UI
        this.updateLanguageFlags();
    }

    /**
     * Update all elements with i18n attributes
     */
    updateElements() {
        // Update text content - prevent "undefined" display
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (key) {
                const translation = this.t(key);
                if (translation && translation !== key) {
                    element.textContent = translation;
                }
            }
        });
        
        // Update placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            if (key) {
                element.placeholder = this.t(key);
            }
        });
        
        // Update titles
        document.querySelectorAll('[data-i18n-title]').forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            if (key) {
                element.title = this.t(key);
            }
        });
        
        // Update aria-labels
        document.querySelectorAll('[data-i18n-aria-label]').forEach(element => {
            const key = element.getAttribute('data-i18n-aria-label');
            if (key) {
                element.setAttribute('aria-label', this.t(key));
            }
        });
    }

    /**
     * Update language flags in the UI
     */
    updateLanguageFlags() {
        const flagElements = document.querySelectorAll('#current-flag, #nav-current-flag');
        const langElements = document.querySelectorAll('#current-lang');
        
        const flagSrc = `assets/images/flags/${this.currentLanguage}.svg`;
        const langText = this.currentLanguage.toUpperCase();
        
        flagElements.forEach(el => {
            if (el) el.src = flagSrc;
        });
        
        langElements.forEach(el => {
            if (el) el.textContent = langText;
        });
    }

    /**
     * Format number according to current language
     */
    formatNumber(number) {
        try {
            const locale = this.currentLanguage === 'fa' ? 'fa-IR' : 'en-US';
            return new Intl.NumberFormat(locale).format(number);
        } catch (error) {
            return number.toString();
        }
    }

    /**
     * Format date according to current language
     */
    formatDate(date, options = {}) {
        try {
            const locale = this.currentLanguage === 'fa' ? 'fa-IR' : 'en-US';
            return new Intl.DateTimeFormat(locale, options).format(date);
        } catch (error) {
            return date.toString();
        }
    }

    /**
     * Format relative time (e.g., "2 hours ago")
     */
    formatRelativeTime(date) {
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) {
            return `${this.formatNumber(days)} ${this.t('time.days')} ${this.t('time.ago')}`;
        } else if (hours > 0) {
            return `${this.formatNumber(hours)} ${this.t('time.hours')} ${this.t('time.ago')}`;
        } else if (minutes > 0) {
            return `${this.formatNumber(minutes)} ${this.t('time.minutes')} ${this.t('time.ago')}`;
        } else {
            return `${this.formatNumber(seconds)} ${this.t('time.seconds')} ${this.t('time.ago')}`;
        }
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return `${this.formatNumber((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    }
}

// Create global instance
window.i18n = new I18n();