# OpenVPN Manager - Static Frontend

A lightweight, production-ready frontend for OpenVPN Manager with **30-second deployment** capability.

## 🚀 Quick Start

The frontend is **pre-built and ready to deploy** - no build process required!

```bash
# Deploy instantly
./deploy.sh

# Or deploy to external web server
./deploy.sh --nginx   # Deploy to Nginx with reverse proxy
./deploy.sh --apache  # Deploy to Apache with reverse proxy
```

## 📦 What's Included

### Core Files
- `dist/index.html` - Main application file
- `dist/manifest.json` - PWA manifest
- `dist/sw.js` - Service worker for offline support

### Stylesheets
- `dist/assets/css/main.css` - Core styles and design system
- `dist/assets/css/themes.css` - Light/Dark theme system  
- `dist/assets/css/responsive.css` - Mobile-first responsive design

### JavaScript Modules
- `dist/assets/js/app.js` - Main application controller
- `dist/assets/js/api.js` - API communication and authentication
- `dist/assets/js/router.js` - Client-side routing system
- `dist/assets/js/charts.js` - Data visualization (Chart.js integration)
- `dist/assets/js/i18n.js` - Internationalization system

### Assets
- `dist/assets/icons/sprite.svg` - Complete icon system
- `dist/assets/images/flags/` - Language flags (EN/FA)
- `dist/assets/icons/favicon.svg` - Application favicon

## ✨ Features

### 🎨 User Interface
- **Modern Design** - Clean, professional interface
- **Responsive Layout** - Works on desktop, tablet, and mobile
- **Dark/Light Themes** - System preference detection + manual toggle
- **Multi-language** - English and Persian (Farsi) with RTL support

### 📱 Progressive Web App
- **Offline Support** - Basic functionality when offline
- **Install Prompt** - Can be installed as a native app
- **Fast Loading** - Optimized for performance on slow connections
- **Mobile Optimized** - Touch-friendly interface

### 🔧 Technical Features
- **No Build Process** - Deploy instantly without compilation
- **Lightweight** - Total size < 500KB (gzipped)
- **Browser Support** - Chrome 80+, Firefox 75+, Safari 13+, Edge 80+
- **Security Headers** - CSP, XSS protection, clickjacking prevention

## 🗂️ Page Structure

### Overview Dashboard
- System statistics (CPU, RAM, Storage)
- Online/Active user counts
- Quick actions (Backup, Restore, Logs)
- Service status monitoring
- Real-time updates via WebSocket

### Users Management
- Complete user CRUD operations
- Bulk actions and CSV export/import
- Real-time status updates
- Data usage and quota management
- OpenVPN config download

### OpenVPN Settings
- Server configuration management
- Port, protocol, DNS settings
- Cipher selection and security options
- Configuration backup/restore
- Service restart capabilities

### Charts & Analytics
- Traffic analysis (upload/download)
- User activity monitoring
- System performance metrics
- Time range selection (daily/weekly/monthly)
- Export functionality

### General Settings
- Theme and language preferences
- API key management
- Security settings
- System configuration options
- Session management

## 🔌 API Integration

The frontend communicates with the Flask API backend via:

- **REST API** - Standard CRUD operations
- **WebSocket** - Real-time updates for system stats
- **File Upload** - Config import/export functionality
- **Authentication** - API key based authentication

### API Endpoints Used
- `/api/auth/*` - Authentication and session management
- `/api/users/*` - User management operations
- `/api/system/*` - System statistics and health
- `/api/openvpn/*` - OpenVPN server configuration
- `/api/analytics/*` - Charts and usage data

## 🛠️ Development

### File Structure
```
frontend/
├── dist/                    # Production-ready files
│   ├── index.html          # Main HTML file
│   ├── manifest.json       # PWA manifest
│   ├── sw.js              # Service worker
│   └── assets/
│       ├── css/           # Stylesheets
│       ├── js/            # JavaScript modules
│       ├── icons/         # SVG icons and favicon
│       └── images/        # Flags and logos
├── deploy.sh              # Deployment script
└── README.md             # This file
```

### Customization

#### Themes
Edit `dist/assets/css/themes.css` to modify colors and styling:
```css
.theme-light {
    --primary-500: #your-color;
    --bg-primary: #your-bg;
}
```

#### Languages
Add new languages in `dist/assets/js/i18n.js`:
```javascript
this.translations.es = {
    // Spanish translations
};
```

#### Branding
- Replace logo SVG in `dist/assets/icons/sprite.svg`
- Update favicon at `dist/assets/icons/favicon.svg`
- Modify app name in `dist/manifest.json`

## 📊 Performance

### Optimization Features
- **Static Assets Caching** - 1 year cache for CSS/JS/images
- **Gzip Compression** - Automatic compression for text files
- **Lazy Loading** - Charts and heavy components load on demand
- **Efficient Rendering** - Virtual scrolling for large data sets
- **Minimal Dependencies** - Only Chart.js loaded from CDN

### Bundle Size
- **HTML**: ~12KB
- **CSS**: ~45KB (all themes included)
- **JavaScript**: ~85KB (all modules)
- **Icons & Images**: ~25KB
- **Total**: ~167KB (< 60KB gzipped)

## 🔒 Security

### Security Headers
- Content Security Policy (CSP)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block

### Authentication
- API key based authentication
- Session timeout management
- Secure token storage
- Automatic logout on token expiry

## 🚀 Deployment Options

### 1. Flask Integration (Recommended)
Frontend is served directly by the Flask API server:
```bash
cd /path/to/project
python3 api/app.py
# Access at http://localhost:5000
```

### 2. Nginx Reverse Proxy
```bash
./deploy.sh --nginx
# Nginx serves static files, proxies API calls
```

### 3. Apache Reverse Proxy
```bash
./deploy.sh --apache
# Apache serves static files, proxies API calls
```

## 🆘 Troubleshooting

### Common Issues

**Frontend not loading**
- Check that `dist/` directory exists and contains files
- Verify Flask app.py is serving static files correctly
- Check browser console for JavaScript errors

**API calls failing**
- Verify Flask API is running on port 5000
- Check API key is valid and not expired
- Confirm CORS settings in Flask app

**Charts not displaying**
- Check internet connection (Chart.js loads from CDN)
- Verify API endpoints return valid data
- Check browser compatibility

**Language switching not working**
- Verify flag images exist in `dist/assets/images/flags/`
- Check browser localStorage permissions
- Confirm i18n.js loaded correctly

### Browser Support
- **Chrome 80+** ✅ Full support
- **Firefox 75+** ✅ Full support  
- **Safari 13+** ✅ Full support
- **Edge 80+** ✅ Full support
- **IE 11** ❌ Not supported

## 📝 License

This frontend is part of the OpenVPN Manager project and follows the same license terms.

---

**Built with ❤️ for simplicity and performance**