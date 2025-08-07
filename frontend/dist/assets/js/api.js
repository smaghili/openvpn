/**
 * API communication module for OpenVPN Manager
 * Handles all HTTP requests and authentication
 */

class API {
    constructor() {
        this.baseURL = '/api';
        this.token = this.getStoredToken();
        this.isAuthenticating = false;
        
        this.clearOldCache();
        this.setupInterceptors();
    }
    
    /**
     * Clear old cached data
     */
    clearOldCache() {
        try {
            const keys = Object.keys(localStorage);
            keys.forEach(key => {
                if (key.includes('api-v1') || key.includes('system/stats')) {
                    localStorage.removeItem(key);
                }
            });
        } catch (error) {
            console.warn('Failed to clear old cache:', error);
        }
    }

    /**
     * Get stored authentication token
     */
    getStoredToken() {
        return localStorage.getItem('openvpn-token');
    }

    /**
     * Store authentication token
     */
    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('openvpn-token', token);
        } else {
            localStorage.removeItem('openvpn-token');
        }
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.token;
    }

    /**
     * Setup request interceptors
     */
    setupInterceptors() {
        // Override fetch to add authentication headers
        const originalFetch = window.fetch;
        window.fetch = async (url, options = {}) => {
            // Add base URL if relative
            if (url.startsWith('/api')) {
                url = url;
            } else if (!url.startsWith('http')) {
                url = `${this.baseURL}${url}`;
            }

            // Add authentication headers
            const headers = {
                'Content-Type': 'application/json',
                ...options.headers
            };

            if (this.token) {
                headers.Authorization = `Bearer ${this.token}`;
            }

            const config = {
                ...options,
                headers
            };

                         const response = await originalFetch(url, config);
             
             if (response.status === 401 && !this.isAuthenticating && !url.includes('/auth/')) {
                 this.handleAuthError();
             }
             
             return response;
        };
    }

    /**
     * Handle authentication errors
     */
         handleAuthError() {
         if (this.isAuthenticating) return;
         this.isAuthenticating = true;
         
         this.setToken(null);
         window.dispatchEvent(new CustomEvent('authenticationFailed'));
     }

    /**
     * Make HTTP request
     */
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers,
                ...options
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new APIError(response.status, errorData.message || 'Request failed', errorData);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }
            throw new APIError(0, 'Network error', { originalError: error });
        }
    }

    /**
     * GET request
     */
    async get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin + this.baseURL);
        Object.keys(params).forEach(key => {
            if (params[key] !== undefined && params[key] !== null) {
                url.searchParams.append(key, params[key]);
            }
        });

        return this.request(url.pathname + url.search);
    }

    /**
     * POST request
     */
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT request
     */
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    /**
     * Upload file
     */
    async upload(endpoint, file, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            if (onProgress) {
                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable) {
                        const progress = (event.loaded / event.total) * 100;
                        onProgress(progress);
                    }
                });
            }

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        resolve(xhr.responseText);
                    }
                } else {
                    reject(new APIError(xhr.status, 'Upload failed'));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new APIError(0, 'Upload failed'));
            });

            xhr.open('POST', `${this.baseURL}${endpoint}`);
            
            if (this.token) {
                xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
            }
            
            xhr.send(formData);
        });
    }

    // Authentication API
    async login(username, password) {
        this.isAuthenticating = true;
        try {
            const response = await this.post('/auth/login', { username, password });
            if (response.token) {
                this.setToken(response.token);
            }
            return response;
        } finally {
            this.isAuthenticating = false;
        }
    }

    async logout() {
        this.setToken(null);
    }

    async validateToken() {
        try {
            const response = await this.get('/auth/validate');
            return response.valid;
        } catch (error) {
            return false;
        }
    }

    // System API
    async getSystemStats() {
        return this.get('/system/status');
    }

    async getSystemHealth() {
        return this.get('/system/health');
    }

    async getSystemServices() {
        return this.get('/system/services');
    }

    async restartService(serviceName) {
        return this.post(`/system/services/${serviceName}/restart`);
    }

    async getSystemLogs(params = {}) {
        return this.get('/system/logs', params);
    }

    async createBackup() {
        return this.post('/system/backup');
    }

    async restoreBackup(backupId) {
        return this.post(`/system/restore/${backupId}`);
    }

    // Users API
    async getUsers(params = {}) {
        return this.get('/users', params);
    }

    async getUserStats() {
        return this.get('/users/stats');
    }

    async createUser(userData) {
        return this.post('/users', userData);
    }

    async updateUser(userId, userData) {
        return this.put(`/users/${userId}`, userData);
    }

    async deleteUser(userId) {
        return this.delete(`/users/${userId}`);
    }

    async deleteUsers(userIds) {
        return this.post('/users/bulk-delete', { user_ids: userIds });
    }

    async changeUserPassword(userId, newPassword) {
        return this.post(`/users/${userId}/password`, { password: newPassword });
    }

    async setUserQuota(userId, quota) {
        return this.post(`/users/${userId}/quota`, { quota });
    }

    async getUserConfig(userId) {
        const response = await fetch(`${this.baseURL}/users/${userId}/config`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        
        if (!response.ok) {
            throw new APIError(response.status, 'Failed to get user config');
        }
        
        return response.blob();
    }

    async exportUsers(format = 'csv') {
        const response = await fetch(`${this.baseURL}/users/export?format=${format}`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        
        if (!response.ok) {
            throw new APIError(response.status, 'Failed to export users');
        }
        
        return response.blob();
    }

    async importUsers(file) {
        return this.upload('/users/import', file);
    }

    // OpenVPN Settings API
    async getOpenVPNSettings() {
        return this.get('/openvpn/settings');
    }

    async updateOpenVPNSettings(settings) {
        return this.put('/openvpn/settings', settings);
    }

    async restartOpenVPN() {
        return this.post('/openvpn/restart');
    }

    async getOpenVPNStatus() {
        return this.get('/openvpn/status');
    }

    async backupOpenVPNConfig() {
        return this.post('/openvpn/backup');
    }

    async restoreOpenVPNConfig(backupId) {
        return this.post(`/openvpn/restore/${backupId}`);
    }

    // Analytics API
    async getTrafficStats(params = {}) {
        return this.get('/analytics/traffic', params);
    }

    async getUserActivity(params = {}) {
        return this.get('/analytics/user-activity', params);
    }

    async getSystemMetrics(params = {}) {
        return this.get('/analytics/system-metrics', params);
    }

    async generateReport(params = {}) {
        return this.post('/analytics/report', params);
    }

    // Settings API
    async getSettings() {
        return this.get('/settings');
    }

    async updateSettings(settings) {
        return this.put('/settings', settings);
    }

    async generateAPIKey() {
        return this.post('/settings/api-key/generate');
    }

    async revokeAPIKey(keyId) {
        return this.delete(`/settings/api-key/${keyId}`);
    }

    // Real-time updates
    setupWebSocket() {
        if (this.ws) {
            this.ws.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            // Send authentication
            if (this.token) {
                this.ws.send(JSON.stringify({
                    type: 'auth',
                    token: this.token
                }));
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                window.dispatchEvent(new CustomEvent('wsMessage', { detail: data }));
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code);
            // Reconnect after delay if not intentional
            if (event.code !== 1000) {
                setTimeout(() => this.setupWebSocket(), 5000);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        return this.ws;
    }

    closeWebSocket() {
        if (this.ws) {
            this.ws.close(1000);
            this.ws = null;
        }
    }
}

/**
 * Custom API Error class
 */
class APIError extends Error {
    constructor(status, message, data = {}) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }

    isNetworkError() {
        return this.status === 0;
    }

    isAuthError() {
        return this.status === 401;
    }

    isForbiddenError() {
        return this.status === 403;
    }

    isNotFoundError() {
        return this.status === 404;
    }

    isServerError() {
        return this.status >= 500;
    }

    isClientError() {
        return this.status >= 400 && this.status < 500;
    }
}

// Create global API instance
window.api = new API();
window.APIError = APIError;