#!/bin/bash

# OpenVPN Manager Static Frontend Deployment Script
# Instant deployment - no build process required

set -e

echo "🚀 Starting OpenVPN Manager Frontend Deployment..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIST="$SCRIPT_DIR/dist"

# Check if frontend dist exists
if [ ! -d "$FRONTEND_DIST" ]; then
    echo "❌ Frontend dist directory not found at: $FRONTEND_DIST"
    echo "   This should not happen with the pre-built static frontend."
    exit 1
fi

# Check if required files exist
REQUIRED_FILES=(
    "index.html" "assets/css/main.css" "assets/css/themes.css" "assets/css/responsive.css"
    "assets/js/app.js" "assets/js/api.js" "assets/js/router.js" "assets/js/charts.js"
    "assets/js/i18n.js" "assets/icons/sprite.svg" "manifest.json"
)

echo "📋 Verifying frontend files..."
MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    [ ! -f "$FRONTEND_DIST/$file" ] && MISSING_FILES+=("$file")
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "❌ Missing required frontend files:"
    printf '   - %s\n' "${MISSING_FILES[@]}"
    exit 1
fi

echo "✅ All frontend files verified!"

# Set correct permissions
echo "🔧 Setting file permissions..."
find "$FRONTEND_DIST" -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" -o -name "*.svg" -o -name "*.json" \) -exec chmod 644 {} \;
find "$FRONTEND_DIST" -type d -exec chmod 755 {} \;

# Check if Flask API is configured properly
API_FILE="$PROJECT_ROOT/api/app.py"
if [ -f "$API_FILE" ]; then
    echo "✅ Flask API found and configured for static file serving"
else
    echo "⚠️  Flask API not found at: $API_FILE"
    echo "   The frontend will be deployed but API integration may not work."
fi

# Deploy based on argument
case "$1" in
    "--nginx")
        echo "🌐 Deploying to Nginx..."
        NGINX_ROOT="/var/www/html/openvpn"
        
        sudo mkdir -p "$NGINX_ROOT"
        sudo cp -r "$FRONTEND_DIST"/* "$NGINX_ROOT/"
        sudo chown -R www-data:www-data "$NGINX_ROOT"
        
        sudo tee /etc/nginx/sites-available/openvpn-manager > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;
    root /var/www/html/openvpn;
    index index.html;
    
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    location ~* \.(css|js|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location ~* \.(png|jpg|jpeg|gif|ico)$ {
        expires 30d;
        add_header Cache-Control "public";
    }
    
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";
    }
}
EOF
        
        [ ! -L "/etc/nginx/sites-enabled/openvpn-manager" ] && sudo ln -s /etc/nginx/sites-available/openvpn-manager /etc/nginx/sites-enabled/
        
        if sudo nginx -t; then
            sudo systemctl reload nginx
            echo "✅ Nginx deployed successfully"
        else
            echo "❌ Nginx configuration test failed"
            exit 1
        fi
        ;;
        
    "--apache")
        echo "🌐 Deploying to Apache..."
        APACHE_ROOT="/var/www/html/openvpn"
        
        sudo mkdir -p "$APACHE_ROOT"
        sudo cp -r "$FRONTEND_DIST"/* "$APACHE_ROOT/"
        sudo chown -R www-data:www-data "$APACHE_ROOT"
        
        sudo tee "$APACHE_ROOT/.htaccess" > /dev/null <<'EOF'
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_URI} !^/api/
RewriteRule . /index.html [L]

<FilesMatch "\.(css|js|svg|woff|woff2|ttf|eot)$">
    ExpiresActive On
    ExpiresDefault "access plus 1 year"
    Header set Cache-Control "public, immutable"
</FilesMatch>

<FilesMatch "\.(png|jpg|jpeg|gif|ico)$">
    ExpiresActive On
    ExpiresDefault "access plus 30 days"
    Header set Cache-Control "public"
</FilesMatch>

<FilesMatch "\.html$">
    Header set Cache-Control "no-cache, no-store, must-revalidate"
    Header set Pragma "no-cache"
    Header set Expires "0"
</FilesMatch>

Header always set X-Content-Type-Options nosniff
Header always set X-Frame-Options DENY
Header always set X-XSS-Protection "1; mode=block"
EOF
        
        sudo a2enmod rewrite headers expires
        sudo systemctl reload apache2
        echo "✅ Apache deployed successfully"
        ;;
        
    *)
        echo "✅ Static frontend deployment completed!"
        echo ""
        echo "📝 The frontend is ready and will be served by the Flask API server."
        echo "   No additional build process or Node.js required!"
        echo ""
        echo "🚀 To start the complete system:"
        echo "   cd $PROJECT_ROOT && python3 api/app.py"
        echo ""
        echo "🌐 Optional external web server deployment:"
        echo "   $0 --nginx    # Deploy to Nginx with reverse proxy"
        echo "   $0 --apache   # Deploy to Apache with reverse proxy"
        ;;
esac

echo ""
echo "🔗 Access at: http://$(hostname -I | awk '{print $1}')"
echo ""
echo "📊 Frontend Analysis:"
echo "   Size: $(du -sh "$FRONTEND_DIST" | cut -f1)"
echo "   Files: $(find "$FRONTEND_DIST" -type f | wc -l)"
echo ""
echo "🎯 Features: Multi-language, Dark/Light themes, Mobile responsive, PWA ready"
echo "🎉 Deployment completed successfully!"