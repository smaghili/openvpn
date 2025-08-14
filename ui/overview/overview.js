// ===== Overview Dashboard JavaScript ===== 

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication first
    if (!checkAuth()) {
        window.location.href = '/login';
        return;
    }
    
    // Apply saved language
    applySavedLanguage();
    
    initializeOverview();
    initializeServiceActions();
    initializeQuickActions();
    startDataRefresh();
});

// Check if user is authenticated
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        return false;
    }
    
    // Basic JWT validation (check if not expired)
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const currentTime = Math.floor(Date.now() / 1000);
        
        if (payload.exp && payload.exp < currentTime) {
            localStorage.removeItem('token');
            return false;
        }
        
        return true;
    } catch (error) {
        localStorage.removeItem('token');
        return false;
    }
}

// Apply saved language from localStorage
function applySavedLanguage() {
    const savedLang = localStorage.getItem('selectedLanguage') || 'fa';
    const htmlEl = document.documentElement;
    
    if (savedLang === 'fa') {
        htmlEl.setAttribute('lang', 'fa');
        htmlEl.setAttribute('dir', 'rtl');
    } else {
        htmlEl.setAttribute('lang', 'en');
        htmlEl.setAttribute('dir', 'ltr');
    }
    
    // Apply translations if available
    if (typeof window.applyTranslations === 'function') {
        window.applyTranslations(savedLang);
    }
}

// Initialize overview functionality
function initializeOverview() {
    updateSystemStats();
    updateServiceStatuses();
    setCurrentYear();
}



// Update system statistics from API
async function updateSystemStats() {
    try {
        const response = await fetch('/api/system/stats', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.message || 'Failed to fetch system stats');
        }

        const data = result.data;
        updateStatDisplay('storage', data.storage);
        updateStatDisplay('cpu', data.cpu);
        updateStatDisplay('ram', data.ram);
        updateStatDisplay('swap', data.swap);
        
        // Update summary info
        if (data.summary) {
            updateSummaryDisplay(data.summary);
        }

    } catch (error) {
        console.error('Error fetching system stats:', error);
        showToast('Failed to load system statistics', 'error');
        
        // Fallback to show loading state
        ['storage', 'cpu', 'ram', 'swap'].forEach(stat => {
            const valueEl = document.getElementById(`${stat}Value`);
            const percentEl = document.getElementById(`${stat}Percent`);
            if (valueEl) valueEl.textContent = '--';
            if (percentEl) percentEl.textContent = 'Loading...';
        });
    }
}

function updateStatDisplay(type, data) {
    const valueEl = document.getElementById(`${type}Value`);
    const percentEl = document.getElementById(`${type}Percent`);
    const progressEl = document.querySelector(`.${type}-progress`);

    if (!data) return;

    switch (type) {
        case 'storage':
            if (valueEl) valueEl.textContent = `${data.used_gb}GB`;
            if (percentEl) percentEl.textContent = `${data.percent}%`;
            if (progressEl) progressEl.style.width = `${data.percent}%`;
            break;
            
        case 'cpu':
            if (valueEl) valueEl.textContent = `${data.percent}%`;
            if (percentEl) percentEl.textContent = `${data.cores} Core${data.cores > 1 ? 's' : ''}`;
            if (progressEl) progressEl.style.width = `${data.percent}%`;
            break;
            
        case 'ram':
            console.log('RAM Data:', data); // Debug log
            if (valueEl) valueEl.textContent = `${data.percent}%`;
            if (percentEl) percentEl.textContent = `${data.used_mb}/${Math.round(data.total_mb)}MB`;
            if (progressEl) progressEl.style.width = `${data.percent}%`;
            break;
            
        case 'swap':
            if (valueEl) valueEl.textContent = `${data.percent}%`;
            if (percentEl) percentEl.textContent = data.total_mb > 0 ? `${data.used_mb}/${data.total_mb}MB` : 'No Swap';
            if (progressEl) progressEl.style.width = `${data.percent}%`;
            break;
    }
}

function updateSummaryDisplay(summary) {
    const totalUsersEl = document.getElementById('totalUsers');
    const totalUsageEl = document.getElementById('totalUsage');
    
    if (totalUsersEl) {
        totalUsersEl.textContent = summary.total_users || 0;
    }
    if (totalUsageEl) {
        totalUsageEl.textContent = summary.total_usage || '--';
    }
}

// Update service statuses from API
async function updateServiceStatuses(forceRefresh = false) {
    try {
        const url = forceRefresh ? '/api/system/services?force=true' : '/api/system/services';
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.message || 'Failed to fetch service status');
        }

        const services = result.data;
        Object.keys(services).forEach(service => {
            const statusEl = document.getElementById(`${service}Status`);
            const uptimeEl = document.getElementById(`${service}Uptime`);
            
            if (statusEl) {
                statusEl.className = `status-indicator ${services[service].status}`;
                
                // Update status text
                const statusTextEl = statusEl.querySelector('.status-text');
                if (statusTextEl) {
                    const statusText = services[service].status.toUpperCase();
                    statusTextEl.textContent = statusText;
                }
            }
            if (uptimeEl) {
                uptimeEl.textContent = services[service].uptime;
            }
        });

    } catch (error) {
        console.error('Error fetching service status:', error);
        showToast('Failed to load service status', 'error');
    }
}

// Initialize service action buttons
function initializeServiceActions() {
    const serviceButtons = document.querySelectorAll('.service-btn');
    
    serviceButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const service = this.dataset.service;
            const action = this.className.includes('restart') ? 'restart' :
                          this.className.includes('start') ? 'start' :
                          this.className.includes('config') ? 'config' : 'fix';
            
            handleServiceAction(service, action);
        });
    });
}

// Handle service actions
function handleServiceAction(service, action) {
    const actionMessages = {
        restart: `Restarting ${service}...`,
        start: `Starting ${service}...`,
        config: `Opening ${service} config...`,
        fix: `Fixing ${service} issues...`
    };

    showToast(actionMessages[action], 'info');
    
    // Simulate API call
    setTimeout(() => {
        if (action === 'start' && service === 'wireguard') {
            const statusEl = document.getElementById('wireguardStatus');
            const uptimeEl = document.getElementById('wireguardUptime');
            if (statusEl) statusEl.className = 'status-indicator up';
            if (uptimeEl) uptimeEl.textContent = 'Started now';
            
            const btn = document.querySelector(`[data-service="${service}"]`);
            if (btn) {
                btn.className = 'service-btn restart';
                btn.textContent = 'Restart';
            }
        }
        
        showToast(`${service} ${action} completed successfully`, 'success');
    }, 2000);
}

// Initialize quick actions
function initializeQuickActions() {
    const addUserBtn = document.getElementById('addUser');
    const backupBtn = document.getElementById('backupConfig');
    const logsBtn = document.getElementById('viewLogs');
    const restartBtn = document.getElementById('systemRestart');

    if (addUserBtn) {
        addUserBtn.addEventListener('click', () => {
            window.location.href = '/users';
        });
    }

    if (backupBtn) {
        backupBtn.addEventListener('click', () => {
            handleBackup();
        });
    }

    if (logsBtn) {
        logsBtn.addEventListener('click', () => {
            handleViewLogs();
        });
    }

    if (restartBtn) {
        restartBtn.addEventListener('click', () => {
            handleSystemRestart();
        });
    }

    // Refresh button
    const refreshBtn = document.getElementById('refreshData');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshData();
        });
    }


}

// Handle backup
function handleBackup() {
    showToast('Creating backup file...', 'info');
    
    // Simulate backup process
    setTimeout(() => {
        showToast('Backup file created successfully', 'success');
    }, 3000);
}

// Handle view logs
function handleViewLogs() {
    showToast('Opening logs...', 'info');
    // In real implementation, this would open logs page or modal
}

// Handle system restart
function handleSystemRestart() {
    showModal(
        'Are you sure you want to restart the system?',
        () => {
            showToast('Restarting system...', 'warning');
            // In real implementation, this would restart the system
        }
    );
}



// Refresh all data with force cache clear
async function refreshData() {
    const refreshBtn = document.getElementById('refreshData');
    if (refreshBtn) {
        refreshBtn.classList.add('loading');
        refreshBtn.disabled = true;
    }

    try {
        // Force refresh with cache clear
        await Promise.all([
            updateSystemStats(),
            updateServiceStatuses(true) // Force refresh
        ]);
        showToast('Data refreshed successfully', 'success');
    } catch (error) {
        showToast('Refresh failed', 'error');
    } finally {
        if (refreshBtn) {
            refreshBtn.classList.remove('loading');
            refreshBtn.disabled = false;
        }
    }
}

// Start real-time refresh with optimization
function startDataRefresh() {
    let isUpdating = false;
    let errorCount = 0;
    
    const refreshData = async () => {
        // Prevent overlapping requests
        if (isUpdating) return;
        isUpdating = true;
        
        try {
            // Run both updates in parallel for efficiency
            await Promise.all([
                updateSystemStats(),
                updateServiceStatuses()
            ]);
            errorCount = 0; // Reset error count on success
        } catch (error) {
            errorCount++;
            console.warn('Data refresh failed:', error);
            
            // If too many errors, slow down refresh rate
            if (errorCount > 3) {
                console.warn('Too many errors, slowing refresh rate');
                return; // Skip this cycle
            }
        } finally {
            isUpdating = false;
        }
    };
    
    // Real-time refresh every 5 seconds
    setInterval(refreshData, 5000);
    
    // Initial load
    refreshData();
}

// Set current year in footer
function setCurrentYear() {
    const yearEl = document.querySelector('.year');
    if (yearEl) {
        yearEl.textContent = new Date().getFullYear();
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-message">${message}</span>
            <button class="toast-close">&times;</button>
        </div>
    `;

    const container = document.querySelector('.toast-container');
    if (container) {
        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.add('fade-out');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }
        }, 5000);

        // Close button
        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                toast.classList.add('fade-out');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            });
        }
    }
}

// Show modal
function showModal(message, onConfirm) {
    const modal = document.querySelector('.modal');
    const modalMessage = document.querySelector('.modal-message');
    const yesBtn = document.querySelector('.modal .yes');
    const noBtn = document.querySelector('.modal .no');

    if (modal && modalMessage && yesBtn && noBtn) {
        modalMessage.textContent = message;
        modal.style.display = 'flex';

        const handleYes = () => {
            modal.style.display = 'none';
            onConfirm();
            yesBtn.removeEventListener('click', handleYes);
            noBtn.removeEventListener('click', handleNo);
        };

        const handleNo = () => {
            modal.style.display = 'none';
            yesBtn.removeEventListener('click', handleYes);
            noBtn.removeEventListener('click', handleNo);
        };

        yesBtn.addEventListener('click', handleYes);
        noBtn.addEventListener('click', handleNo);

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                handleNo();
            }
        });
    }
}