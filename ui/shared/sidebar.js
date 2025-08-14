// ===== Shared Sidebar Component JavaScript =====

class SidebarManager {
    constructor() {
        this.currentPage = this.getCurrentPage();
        this.init();
    }

    init() {
        this.loadSidebar();
    }

    loadSidebar() {
        fetch('/shared/sidebar.html')
            .then(response => response.text())
            .then(html => {
                const sidebarContainer = document.querySelector('.sidebar-container');
                if (sidebarContainer) {
                    sidebarContainer.innerHTML = html;
                    this.initializeSidebarFeatures();
                }
            })
            .catch(error => {
                console.error('Error loading sidebar:', error);
            });
    }

        initializeSidebarFeatures() {
        // Wait for DOM to be ready
        setTimeout(() => {
            this.initializeTheme();
            this.initializeNavigation();
            this.initializeLogout();
            this.setActivePage();
        }, 100);
    }

    getCurrentPage() {
        const path = window.location.pathname;
        if (path === '/' || path === '/overview') return 'overview';
        if (path.startsWith('/users')) return 'users';
        if (path.startsWith('/openvpn')) return 'openvpn';
        if (path.startsWith('/wireguard')) return 'wireguard';
        if (path.startsWith('/settings')) return 'settings';
        return 'overview';
    }

    setActivePage() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.classList.remove('active');
            if (item.dataset.page === this.currentPage) {
                item.classList.add('active');
            }
        });
    }

    initializeTheme() {
        const sidebarTheme = document.getElementById('sidebarTheme');
        if (sidebarTheme) {
            const currentTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            sidebarTheme.textContent = currentTheme === 'dark' ? '☀️' : '🌙';
            
            sidebarTheme.addEventListener('click', () => {
                const htmlEl = document.documentElement;
                const isDark = htmlEl.classList.contains('dark');
                const newTheme = isDark ? 'light' : 'dark';
                
                htmlEl.classList.toggle('dark', newTheme === 'dark');
                localStorage.setItem('theme', newTheme);
                sidebarTheme.textContent = newTheme === 'dark' ? '☀️' : '🌙';
            });
        }
    }

    initializeNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');
                if (href && href !== window.location.pathname) {
                    // Let the browser handle navigation naturally
                    return true;
                }
                e.preventDefault();
            });
        });
    }

    initializeLogout() {
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.handleLogout();
            });
        }
    }

    handleLogout() {
        if (typeof showModal === 'function') {
            showModal(
                'Are you sure you want to logout?',
                () => {
                    localStorage.removeItem('token');
                    window.location.href = '/login';
                }
            );
        } else {
            const confirmed = confirm('Are you sure you want to logout?');
            if (confirmed) {
                localStorage.removeItem('token');
                window.location.href = '/login';
            }
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.sidebarManager = new SidebarManager();
});

// Export for manual initialization if needed
window.SidebarManager = SidebarManager;