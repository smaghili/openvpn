document.addEventListener('DOMContentLoaded', function() {
    new OverviewDashboard();
});

class OverviewDashboard {
    constructor() {
        this.refreshInterval = null;
        this.liveLogInterval = null;
        this.currentLogService = null;
        this.isLiveMode = false;
        this.hasStoredPassword = false;
        this.backupInProgress = false;
        this.init();
    }

    init() {
        this.setupI18n();
        this.setupServiceControls();
        this.setupLogSystem();
        this.setupBackupRestore();
        this.setupModals();
        this.loadInitialData();
        this.startAutoRefresh();
    }

    setupI18n() {
        if (window.i18n) {
            window.i18n.translatePage();
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadSystemStats(),
            this.loadServiceStatus(),
            this.loadUserStats(),
            this.loadSystemUptime(),
            this.checkStoredPassword()
        ]);
    }

    async loadSystemStats() {
    try {
        const response = await fetch('/api/system/stats', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            
            if (!response.ok) throw new Error('Failed to load system stats');
            
            const data = await response.json();
            this.updateSystemStats(data);
        } catch (error) {
            console.error('Error loading system stats:', error);
            this.showToast(window.i18n ? window.i18n.t('toasts.systemStatsError') : 'Error loading system stats', 'error');
        }
    }

    updateSystemStats(data) {
        const stats = data.data || {};
        
        this.updateStatCard('cpu', stats.cpu_usage || 0);
        this.updateStatCard('ram', stats.memory_usage || 0);
        this.updateStatCard('swap', stats.swap_usage || 0);
        this.updateStatCard('storage', stats.disk_usage || 0);
    }

    async checkStoredPassword() {
        try {
            const response = await fetch('/api/system/backup/password/check', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.hasStoredPassword = data.has_stored_password;
                this.updateBackupUI();
            }
        } catch (error) {
            console.error('Error checking stored password:', error);
            this.hasStoredPassword = false;
        }
    }

    updateBackupUI() {
        const createButton = document.getElementById('createBackup');
        if (createButton && this.hasStoredPassword) {
            createButton.textContent = window.i18n ? 
                window.i18n.t('backup.createWithStored') : 
                'Create Backup (Stored)';
            createButton.classList.add('has-stored-password');
        }
    }

    updateStatCard(type, usage) {
    const valueEl = document.getElementById(`${type}Value`);
    const percentEl = document.getElementById(`${type}Percent`);
    const progressEl = document.querySelector(`.${type}-progress`);

        if (valueEl) valueEl.textContent = `${usage.toFixed(1)}%`;
        if (percentEl) percentEl.textContent = `${usage.toFixed(1)}%`;
        if (progressEl) progressEl.style.width = `${usage}%`;
    }

    async loadServiceStatus() {
        try {
            const response = await fetch('/api/system/services', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            
            if (!response.ok) throw new Error('Failed to load service status');
            
            const data = await response.json();
            this.updateServiceStatus(data.data || {});
        } catch (error) {
            console.error('Error loading service status:', error);
            this.showToast(window.i18n ? window.i18n.t('toasts.serviceStatusError') : 'Error loading service status', 'error');
        }
    }

    updateServiceStatus(services) {
        const serviceMap = {
            'openvpn-uds-monitor': { statusId: 'udsStatus', uptimeId: 'udsUptime', ramId: 'uds-ram', cpuId: 'uds-cpu' },
            'wg-quick@wg0': { statusId: 'wireguardStatus', uptimeId: 'wireguardUptime', ramId: 'wg-ram', cpuId: 'wg-cpu' },
            'openvpn-server@server-login': { statusId: 'loginStatus', uptimeId: 'loginUptime', ramId: 'ovpn-login-ram', cpuId: 'ovpn-login-cpu' },
            'openvpn-server@server-cert': { statusId: 'certStatus', uptimeId: 'certUptime', ramId: 'ovpn-cert-ram', cpuId: 'ovpn-cert-cpu' }
        };

        Object.entries(services).forEach(([serviceName, serviceData]) => {
            const mapping = serviceMap[serviceName];
            if (!mapping) return;

            this.updateServiceCard(mapping, serviceData);
        });
    }

    updateServiceCard(mapping, serviceData) {
        const statusEl = document.getElementById(mapping.statusId);
        const uptimeEl = document.getElementById(mapping.uptimeId);
        const ramEl = document.getElementById(mapping.ramId);
        const cpuEl = document.getElementById(mapping.cpuId);

        if (statusEl) {
            const dot = statusEl.querySelector('.status-dot');
            const text = statusEl.querySelector('.status-text');
            
            if (dot) {
                dot.className = 'status-dot';
                const status = serviceData.status || 'inactive';
                dot.classList.add(status);
            }
            
            if (text) {
                const status = serviceData.status || 'inactive';
                const statusKey = `services.card.status.${status}`;
                text.textContent = window.i18n ? window.i18n.t(statusKey) : (status === 'active' ? 'Active' : status === 'inactive' ? 'Inactive' : 'Unknown');
            }
        }

        if (uptimeEl) {
            uptimeEl.textContent = serviceData.uptime || '--';
        }

        if (ramEl) {
            ramEl.textContent = serviceData.memory_usage ? `${serviceData.memory_usage}MB` : '--';
        }

        if (cpuEl) {
            cpuEl.textContent = serviceData.cpu_usage ? `${serviceData.cpu_usage}%` : '--';
        }
    }

    async loadUserStats() {
        try {
            const response = await fetch('/api/users/stats', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            
            if (!response.ok) throw new Error('Failed to load user stats');
            
            const data = await response.json();
            this.updateUserStats(data.data || {});
    } catch (error) {
            console.error('Error loading user stats:', error);
        }
    }

    updateUserStats(stats) {
    const totalUsersEl = document.getElementById('totalUsers');
        const onlineUsersEl = document.getElementById('onlineUsers');
    const totalUsageEl = document.getElementById('totalUsage');
    
        if (totalUsersEl) totalUsersEl.textContent = stats.total_users || '0';
        if (onlineUsersEl) onlineUsersEl.textContent = stats.online_users || '0';
        if (totalUsageEl) {
            const usage = stats.total_usage || 0;
            totalUsageEl.textContent = window.i18n ? window.i18n.formatBytes(usage) : `${(usage / (1024**3)).toFixed(1)}GB`;
        }
    }

    async loadSystemUptime() {
        try {
            const response = await fetch('/api/system/uptime', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            
            if (!response.ok) throw new Error('Failed to load system uptime');
            
            const data = await response.json();
            this.updateSystemUptime(data.data || {});
        } catch (error) {
            console.error('Error loading system uptime:', error);
        }
    }

    updateSystemUptime(uptime) {
        const systemUptimeEl = document.getElementById('systemUptime');
        const lastBootEl = document.getElementById('lastBoot');

        if (systemUptimeEl) {
            if (window.i18n && uptime.uptime_parts) {
                systemUptimeEl.textContent = window.i18n.formatUptime(uptime.uptime_parts);
            } else {
                systemUptimeEl.textContent = uptime.uptime_formatted || '--';
            }
        }

        if (lastBootEl) {
            lastBootEl.textContent = uptime.last_boot || '--';
        }
    }

    setupServiceControls() {
        document.querySelectorAll('.service-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const service = e.target.dataset.service;
                const action = e.target.dataset.action;
                
                if (service && action) {
                    this.handleServiceAction(service, action, e.target);
                }
            });
        });
    }

    async handleServiceAction(service, action, button) {
        const confirmMsg = window.i18n ? 
            window.i18n.t(`services.actions.${action}`) + ` ${window.i18n.t('service')} ${service}?` :
            `${action} service ${service}?`;

        if (!confirm(confirmMsg)) return;

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = window.i18n ? window.i18n.t(`services.actions.${action}ing`) : `${action}ing...`;

        try {
            const response = await fetch(`/api/system/services/${service}/${action}`, {
                method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            }
        });

            if (!response.ok) throw new Error(`Service ${action} failed`);

            const result = await response.json();
            this.showToast(result.message || `Service ${action} successful`, 'success');
            
            setTimeout(() => this.loadServiceStatus(), 2000);
        } catch (error) {
            console.error(`Service ${action} error:`, error);
            this.showToast(window.i18n ? window.i18n.t('toasts.serviceActionError') : 'Service operation error', 'error');
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    setupLogSystem() {
        document.querySelectorAll('.log-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const service = e.target.dataset.service;
                this.openLogModal(service);
            });
        });
    }

    openLogModal(service) {
        this.currentLogService = service;
        const modal = document.getElementById('logModal');
        const title = document.getElementById('logModalTitle');
        
        if (title) {
            const serviceKey = `logs.services.${service}`;
            title.textContent = window.i18n ? window.i18n.t(serviceKey) : `${service} Logs`;
        }
        
        modal.style.display = 'block';
        this.loadLogs(service);
    }

    async loadLogs(service) {
        const output = document.getElementById('logOutput');
        if (output) {
            output.textContent = window.i18n ? window.i18n.t('logs.modal.loading') : 'Loading...';
        }

        try {
            const response = await fetch(`/api/system/logs/${service}?lines=100`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });

            if (!response.ok) throw new Error('Failed to load logs');

            const data = await response.json();
            if (output) {
                output.textContent = data.logs || (window.i18n ? window.i18n.t('logs.modal.empty') : 'No logs available');
            }
        } catch (error) {
            console.error('Error loading logs:', error);
            if (output) {
                output.textContent = window.i18n ? window.i18n.t('errors.server') : 'Error loading logs';
            }
        }
    }

    toggleLiveMode() {
        const liveBtn = document.getElementById('liveLog');
        
        if (this.isLiveMode) {
            clearInterval(this.liveLogInterval);
            this.isLiveMode = false;
            liveBtn.textContent = window.i18n ? window.i18n.t('logs.modal.live') : 'Live tail';
        } else {
            this.isLiveMode = true;
            liveBtn.textContent = 'Stop Live';
            this.liveLogInterval = setInterval(() => {
                if (this.currentLogService) {
                    this.loadLogs(this.currentLogService);
                }
            }, 2000);
        }
    }

    async downloadLogs(service) {
        try {
            const response = await fetch(`/api/system/logs/${service}/download`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });

            if (!response.ok) throw new Error('Failed to download logs');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${service}_logs_${new Date().toISOString().split('T')[0]}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showToast(window.i18n ? window.i18n.t('toasts.logDownloadSuccess') : 'Log file downloaded', 'success');
    } catch (error) {
            console.error('Error downloading logs:', error);
            this.showToast(window.i18n ? window.i18n.t('toasts.logDownloadError') : 'Error downloading log file', 'error');
        }
    }

    setupBackupRestore() {
        document.getElementById('createBackup').addEventListener('click', () => {
            if (this.hasStoredPassword) {
                // Direct backup with stored password
                this.createBackupWithStoredPassword();
            } else {
                // Show password dialog
                this.showPasswordDialog('backup');
            }
        });

        document.getElementById('restoreBackup').addEventListener('click', () => {
            this.showFileDialog();
        });
    }

    async createBackupWithStoredPassword() {
        if (this.backupInProgress) return;
        
        this.backupInProgress = true;
        const createButton = document.getElementById('createBackup');
        const originalText = createButton.textContent;
        
        try {
            createButton.textContent = window.i18n ? 
                window.i18n.t('backup.creating') : 
                'Creating...';
            createButton.disabled = true;
            
            await this.createBackup(null, false, true); // password=null, remember=false, useStored=true
            
        } catch (error) {
            console.error('Backup with stored password failed:', error);
            this.showToast(window.i18n ? window.i18n.t('toasts.backupError') : 'Error creating backup', 'error');
        } finally {
            this.backupInProgress = false;
            createButton.textContent = originalText;
            createButton.disabled = false;
        }
    }

    showPasswordDialog(type) {
        const modal = document.getElementById('passwordDialog');
        const title = document.getElementById('passwordTitle');
        const rememberGroup = document.getElementById('rememberGroup');
        
        if (type === 'backup') {
            title.textContent = window.i18n ? window.i18n.t('backup.prompt.password') : 'Backup Password';
            rememberGroup.style.display = 'block';
        } else {
            title.textContent = window.i18n ? window.i18n.t('restore.prompt.password') : 'Restore Password';
            rememberGroup.style.display = 'none';
        }
        
        modal.style.display = 'block';
        modal.dataset.type = type;
    }

    showFileDialog() {
        const modal = document.getElementById('fileDialog');
        modal.style.display = 'block';
    }

    setupModals() {
        document.querySelectorAll('.modal-close').forEach(button => {
            button.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                    if (modal.id === 'logModal' && this.isLiveMode) {
                        this.toggleLiveMode();
                    }
                }
            });
        });

        document.getElementById('refreshLog').addEventListener('click', () => {
            if (this.currentLogService) {
                this.loadLogs(this.currentLogService);
            }
        });

        document.getElementById('liveLog').addEventListener('click', () => {
            this.toggleLiveMode();
        });

        document.getElementById('downloadLog').addEventListener('click', () => {
            if (this.currentLogService) {
                this.downloadLogs(this.currentLogService);
            }
        });

        document.getElementById('passwordForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const modal = document.getElementById('passwordDialog');
            const type = modal.dataset.type;
            const password = document.getElementById('password').value;
            const remember = document.getElementById('rememberPassword').checked;
            
            if (type === 'backup') {
                this.createBackup(password, remember);
            } else {
                this.restoreWithPassword = password;
                this.executeRestore();
            }
            
            modal.style.display = 'none';
            document.getElementById('password').value = '';
        });

        document.getElementById('fileForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const file = document.getElementById('restoreFile').files[0];
            if (file) {
                this.restoreFile = file;
                this.showPasswordDialog('restore');
            }
            document.getElementById('fileDialog').style.display = 'none';
        });

        document.getElementById('cancelPassword').addEventListener('click', () => {
            document.getElementById('passwordDialog').style.display = 'none';
        });

        document.getElementById('cancelFile').addEventListener('click', () => {
            document.getElementById('fileDialog').style.display = 'none';
        });
    }

    async createBackup(password, remember = false, useStored = false) {
        try {
            const payload = {};
            
            if (useStored) {
                payload.use_stored = true;
            } else {
                payload.password = password;
                payload.remember = remember;
            }
            
            const response = await fetch('/api/system/backup', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Backup creation failed');
            }

            const result = await response.json();
            
            // If password was stored, update UI
            if (remember) {
                this.hasStoredPassword = true;
                this.updateBackupUI();
            }
            
            // Handle download
            if (result.download_url) {
                const a = document.createElement('a');
                a.href = result.download_url;
                a.download = result.filename || `backup_${new Date().toISOString().split('T')[0]}.gpg`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }

            const successMsg = window.i18n ? 
                window.i18n.t('backup.success') : 
                'Backup created successfully';
            this.showToast(successMsg, 'success');
            
    } catch (error) {
            console.error('Backup error:', error);
            const errorMsg = window.i18n ? 
                window.i18n.t('toasts.backupError') : 
                `Error creating backup: ${error.message}`;
            this.showToast(errorMsg, 'error');
            throw error;
        }
    }

    async executeRestore() {
        if (!this.restoreFile || !this.restoreWithPassword) return;

        const confirmMsg = window.i18n ? 
            window.i18n.t('restore.confirm.restartSystem') : 
            'The system will restart after restore. Continue?';

        if (!confirm(confirmMsg)) return;

        const formData = new FormData();
        formData.append('file', this.restoreFile);
        formData.append('password', this.restoreWithPassword);

        try {
            const response = await fetch('/api/system/restore', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: formData
            });

            if (!response.ok) throw new Error('Restore failed');

            this.showToast(window.i18n ? window.i18n.t('toasts.restoreStarted') : 'Restore started. System will restart...', 'success');
            
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        } catch (error) {
            console.error('Restore error:', error);
            this.showToast(window.i18n ? window.i18n.t('toasts.restoreError') : 'Error in restore', 'error');
        }
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadSystemStats();
            this.loadServiceStatus();
            this.loadUserStats();
        }, 30000);
    }

    showToast(message, type = 'info') {
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

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.liveLogInterval) {
            clearInterval(this.liveLogInterval);
        }
    }
}