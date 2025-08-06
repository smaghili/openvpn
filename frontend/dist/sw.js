/**
 * Service Worker for OpenVPN Manager
 * Provides basic offline functionality and caching
 */

const CACHE_NAME = 'openvpn-manager-v1';
const urlsToCache = [
    '/',
    '/assets/css/main.css',
    '/assets/css/themes.css',
    '/assets/css/responsive.css',
    '/assets/js/i18n.js',
    '/assets/js/api.js',
    '/assets/js/router.js',
    '/assets/js/charts.js',
    '/assets/js/app.js',
    '/assets/icons/sprite.svg',
    '/assets/icons/favicon.svg',
    '/assets/images/flags/en.svg',
    '/assets/images/flags/fa.svg',
    '/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(urlsToCache);
            })
            .catch((error) => {
                console.error('Failed to cache resources:', error);
            })
    );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Skip API requests
    if (event.request.url.includes('/api/')) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                return response || fetch(event.request);
            })
            .catch(() => {
                // If both cache and network fail, return offline page for navigation requests
                if (event.request.mode === 'navigate') {
                    return caches.match('/');
                }
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});