/**
 * Lightweight charts module for OpenVPN Manager
 * Uses Chart.js for data visualization
 */

class Charts {
    constructor() {
        this.charts = new Map();
        this.colors = {
            primary: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444',
            info: '#06b6d4',
            gray: '#6b7280'
        };
        
        // Load Chart.js if not already loaded
        this.loadChartJS();
    }

    /**
     * Load Chart.js library dynamically with proper timing
     */
    async loadChartJS() {
        // Check if already loaded
        if (window.Chart && window.Chart.registerables) {
            this.setupChart();
            return;
        }

        try {
            // Load Chart.js from CDN with timeout
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
            
            const loadPromise = new Promise((resolve, reject) => {
                script.onload = () => {
                    // Wait for Chart.registerables to be available
                    const checkRegisterables = () => {
                        if (window.Chart && window.Chart.registerables) {
                            resolve();
                        } else {
                            setTimeout(checkRegisterables, 50);
                        }
                    };
                    checkRegisterables();
                };
                script.onerror = reject;
                
                // 10 second timeout
                setTimeout(() => reject(new Error('Chart.js load timeout')), 10000);
            });
            
            document.head.appendChild(script);
            await loadPromise;
            
            this.setupChart();
            
        } catch (error) {
            console.error('Error loading Chart.js:', error);
            this.fallbackToSimpleCharts();
        }
    }

    /**
     * Setup Chart.js configuration with proper error handling
     */
    setupChart() {
        if (!window.Chart || !window.Chart.registerables) {
            console.warn('Chart.js not properly loaded');
            return;
        }

        try {
            // Register Chart.js components (Chart.js v4 compatible)
            if (Array.isArray(Chart.registerables)) {
                Chart.register(...Chart.registerables);
            } else if (Chart.registerables) {
                // For different structure
                Chart.register(Chart.registerables);
            } else {
                console.warn('Chart.registerables not found');
                return;
            }
        } catch (error) {
            console.error('Failed to register Chart.js components:', error);
            this.fallbackToSimpleCharts();
            return;
        }

        // Set global defaults
        Chart.defaults.font.family = 'var(--font-family-base)';
        Chart.defaults.color = 'var(--text-secondary)';
        Chart.defaults.borderColor = 'var(--border-secondary)';
        Chart.defaults.backgroundColor = 'var(--bg-secondary)';

        // Setup responsive defaults
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
        Chart.defaults.interaction.intersect = false;
        Chart.defaults.interaction.mode = 'index';
    }

    /**
     * Initialize all charts for the charts page
     */
    async initializeCharts() {
        try {
            await this.createTrafficChart();
            await this.createUserActivityChart();
            await this.createSystemPerformanceChart();
            
            // Setup time range buttons
            this.setupTimeRangeButtons();
        } catch (error) {
            console.error('Failed to initialize charts:', error);
        }
    }

    /**
     * Create traffic analysis chart
     */
    async createTrafficChart() {
        const canvas = document.getElementById('traffic-chart');
        if (!canvas) return;

        try {
            const data = await window.api.getTrafficStats({ range: 'daily' });
            
            const chart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: data.labels || [],
                    datasets: [
                        {
                            label: window.i18n?.t('pages.charts.uploadTraffic') || 'Upload',
                            data: data.upload || [],
                            borderColor: this.colors.primary,
                            backgroundColor: this.colors.primary + '20',
                            fill: false,
                            tension: 0.4
                        },
                        {
                            label: window.i18n?.t('pages.charts.downloadTraffic') || 'Download',
                            data: data.download || [],
                            borderColor: this.colors.success,
                            backgroundColor: this.colors.success + '20',
                            fill: false,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: window.i18n?.t('pages.charts.trafficAnalysis') || 'Traffic Analysis'
                        },
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return window.i18n?.formatFileSize(value) || value;
                                }
                            }
                        }
                    },
                    interaction: {
                        intersect: false
                    }
                }
            });

            this.charts.set('traffic', chart);
        } catch (error) {
            console.error('Failed to create traffic chart:', error);
            this.showChartError(canvas, 'Failed to load traffic data');
        }
    }

    /**
     * Create user activity chart
     */
    async createUserActivityChart() {
        const canvas = document.getElementById('user-activity-chart');
        if (!canvas) return;

        try {
            const data = await window.api.getUserActivity({ range: 'daily' });
            
            const chart = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: data.labels || [],
                    datasets: [
                        {
                            label: window.i18n?.t('pages.charts.activeSessions') || 'Active Sessions',
                            data: data.sessions || [],
                            backgroundColor: this.colors.info + '80',
                            borderColor: this.colors.info,
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: window.i18n?.t('pages.charts.userActivity') || 'User Activity'
                        },
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });

            this.charts.set('userActivity', chart);
        } catch (error) {
            console.error('Failed to create user activity chart:', error);
            this.showChartError(canvas, 'Failed to load user activity data');
        }
    }

    /**
     * Create system performance chart
     */
    async createSystemPerformanceChart() {
        const canvas = document.getElementById('system-performance-chart');
        if (!canvas) return;

        try {
            const data = await window.api.getSystemMetrics({ range: 'daily' });
            
            const chart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: data.labels || [],
                    datasets: [
                        {
                            label: 'CPU Usage (%)',
                            data: data.cpu || [],
                            borderColor: this.colors.warning,
                            backgroundColor: this.colors.warning + '20',
                            fill: false,
                            tension: 0.4
                        },
                        {
                            label: 'Memory Usage (%)',
                            data: data.memory || [],
                            borderColor: this.colors.error,
                            backgroundColor: this.colors.error + '20',
                            fill: false,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: window.i18n?.t('pages.charts.systemPerformance') || 'System Performance'
                        },
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });

            this.charts.set('systemPerformance', chart);
        } catch (error) {
            console.error('Failed to create system performance chart:', error);
            this.showChartError(canvas, 'Failed to load system metrics');
        }
    }

    /**
     * Create simple progress bar chart (fallback)
     */
    createProgressChart(canvas, value, max = 100, color = this.colors.primary) {
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        // Calculate progress
        const progress = Math.min(value / max, 1);
        const progressWidth = width * progress;
        
        // Draw background
        ctx.fillStyle = this.colors.gray + '20';
        ctx.fillRect(0, 0, width, height);
        
        // Draw progress
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, progressWidth, height);
        
        // Draw text
        ctx.fillStyle = 'var(--text-primary)';
        ctx.font = '14px var(--font-family-base)';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${Math.round(value)}%`, width / 2, height / 2);
    }

    /**
     * Create simple line chart (fallback)
     */
    createSimpleLineChart(canvas, data, labels, color = this.colors.primary) {
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        if (!data || data.length === 0) {
            this.showChartError(canvas, 'No data available');
            return;
        }
        
        // Calculate scales
        const maxValue = Math.max(...data);
        const minValue = Math.min(...data);
        const range = maxValue - minValue || 1;
        
        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;
        
        // Draw axes
        ctx.strokeStyle = this.colors.gray;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();
        
        // Draw line
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        for (let i = 0; i < data.length; i++) {
            const x = padding + (i / (data.length - 1)) * chartWidth;
            const y = height - padding - ((data[i] - minValue) / range) * chartHeight;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        
        ctx.stroke();
        
        // Draw points
        ctx.fillStyle = color;
        for (let i = 0; i < data.length; i++) {
            const x = padding + (i / (data.length - 1)) * chartWidth;
            const y = height - padding - ((data[i] - minValue) / range) * chartHeight;
            
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    /**
     * Setup time range buttons
     */
    setupTimeRangeButtons() {
        const buttons = document.querySelectorAll('[data-range]');
        buttons.forEach(button => {
            button.addEventListener('click', async (e) => {
                // Remove active class from all buttons
                buttons.forEach(btn => btn.classList.remove('active'));
                
                // Add active class to clicked button
                e.target.classList.add('active');
                
                // Refresh charts with new range
                const range = e.target.getAttribute('data-range');
                await this.refreshCharts(range);
            });
        });
    }

    /**
     * Refresh all charts with new data
     */
    async refreshCharts(range = 'daily') {
        try {
            // Update traffic chart
            const trafficChart = this.charts.get('traffic');
            if (trafficChart) {
                const trafficData = await window.api.getTrafficStats({ range });
                trafficChart.data.labels = trafficData.labels || [];
                trafficChart.data.datasets[0].data = trafficData.upload || [];
                trafficChart.data.datasets[1].data = trafficData.download || [];
                trafficChart.update();
            }

            // Update user activity chart
            const userActivityChart = this.charts.get('userActivity');
            if (userActivityChart) {
                const activityData = await window.api.getUserActivity({ range });
                userActivityChart.data.labels = activityData.labels || [];
                userActivityChart.data.datasets[0].data = activityData.sessions || [];
                userActivityChart.update();
            }

            // Update system performance chart
            const systemChart = this.charts.get('systemPerformance');
            if (systemChart) {
                const systemData = await window.api.getSystemMetrics({ range });
                systemChart.data.labels = systemData.labels || [];
                systemChart.data.datasets[0].data = systemData.cpu || [];
                systemChart.data.datasets[1].data = systemData.memory || [];
                systemChart.update();
            }
        } catch (error) {
            console.error('Failed to refresh charts:', error);
        }
    }

    /**
     * Show error message in chart container
     */
    showChartError(canvas, message) {
        const container = canvas.parentElement;
        if (container) {
            container.innerHTML = `
                <div class="chart-error">
                    <svg width="48" height="48" class="error-icon">
                        <use href="assets/icons/sprite.svg#exclamation-triangle"></use>
                    </svg>
                    <p>${message}</p>
                    <button class="btn btn-sm btn-secondary" onclick="location.reload()">
                        <span data-i18n="common.refresh">Refresh</span>
                    </button>
                </div>
            `;
        }
    }

    /**
     * Fallback to simple charts when Chart.js fails to load
     */
    fallbackToSimpleCharts() {
        console.warn('Using fallback simple charts');
        
        // Create simple implementations for critical charts
        this.createFallbackCharts();
    }

    /**
     * Create fallback charts using canvas
     */
    async createFallbackCharts() {
        // Traffic chart fallback
        const trafficCanvas = document.getElementById('traffic-chart');
        if (trafficCanvas) {
            try {
                const data = await window.api.getTrafficStats({ range: 'daily' });
                this.createSimpleLineChart(trafficCanvas, data.upload, data.labels, this.colors.primary);
            } catch (error) {
                this.showChartError(trafficCanvas, 'Failed to load traffic data');
            }
        }

        // User activity chart fallback
        const activityCanvas = document.getElementById('user-activity-chart');
        if (activityCanvas) {
            try {
                const data = await window.api.getUserActivity({ range: 'daily' });
                this.createSimpleBarChart(activityCanvas, data.sessions, data.labels, this.colors.info);
            } catch (error) {
                this.showChartError(activityCanvas, 'Failed to load user activity data');
            }
        }

        // System performance chart fallback
        const systemCanvas = document.getElementById('system-performance-chart');
        if (systemCanvas) {
            try {
                const data = await window.api.getSystemMetrics({ range: 'daily' });
                this.createSimpleLineChart(systemCanvas, data.cpu, data.labels, this.colors.warning);
            } catch (error) {
                this.showChartError(systemCanvas, 'Failed to load system metrics');
            }
        }
    }

    /**
     * Create simple bar chart (fallback)
     */
    createSimpleBarChart(canvas, data, labels, color = this.colors.primary) {
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        if (!data || data.length === 0) {
            this.showChartError(canvas, 'No data available');
            return;
        }
        
        const maxValue = Math.max(...data);
        const barWidth = (width - padding * 2) / data.length * 0.8;
        const barSpacing = (width - padding * 2) / data.length * 0.2;
        
        // Draw axes
        ctx.strokeStyle = this.colors.gray;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();
        
        // Draw bars
        ctx.fillStyle = color;
        for (let i = 0; i < data.length; i++) {
            const barHeight = (data[i] / maxValue) * (height - padding * 2);
            const x = padding + i * (barWidth + barSpacing) + barSpacing / 2;
            const y = height - padding - barHeight;
            
            ctx.fillRect(x, y, barWidth, barHeight);
        }
    }

    /**
     * Update theme colors when theme changes
     */
    updateThemeColors() {
        const isDark = document.body.classList.contains('theme-dark');
        
        if (isDark) {
            this.colors = {
                ...this.colors,
                gray: '#9ca3af'
            };
        } else {
            this.colors = {
                ...this.colors,
                gray: '#6b7280'
            };
        }
        
        // Update existing charts
        this.charts.forEach(chart => {
            if (chart.update) {
                chart.update();
            }
        });
    }

    /**
     * Destroy all charts
     */
    destroyCharts() {
        this.charts.forEach(chart => {
            if (chart.destroy) {
                chart.destroy();
            }
        });
        this.charts.clear();
    }

    /**
     * Resize all charts
     */
    resizeCharts() {
        this.charts.forEach(chart => {
            if (chart.resize) {
                chart.resize();
            }
        });
    }
}

// Create global charts instance
window.charts = new Charts();

// Listen for theme changes
window.addEventListener('themeChanged', () => {
    if (window.charts) {
        window.charts.updateThemeColors();
    }
});

// Listen for window resize
window.addEventListener('resize', () => {
    if (window.charts) {
        window.charts.resizeCharts();
    }
});