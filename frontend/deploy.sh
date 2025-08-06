#!/bin/bash

# OpenVPN Manager Frontend Deployment Script

set -e

echo "🚀 Starting OpenVPN Manager Frontend Deployment..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the project
echo "🔨 Building project..."
npm run build

# Check if build was successful
if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

echo "✅ Build completed successfully!"

# Optional: Deploy to web server
if [ "$1" = "--deploy" ]; then
    echo "🌐 Deploying to web server..."
    
    # Example deployment commands (customize based on your setup)
    # sudo cp -r dist/* /var/www/html/openvpn-dashboard/
    # sudo systemctl restart nginx
    
    echo "⚠️  Please configure deployment commands in this script for your environment"
fi

echo "🎉 Frontend deployment completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Serve the 'dist' folder using a web server (nginx, apache, etc.)"
echo "   2. Configure reverse proxy to backend API (http://localhost:5000)"
echo "   3. Set up SSL certificate for production use"
echo "   4. Configure environment variables if needed"
echo ""
echo "🔗 Development server: npm run dev"
echo "📁 Production files: ./dist/"