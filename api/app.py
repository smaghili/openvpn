#!/usr/bin/env python3
import os
import sys
import hmac
from flask import Flask, send_from_directory, send_file, request, make_response, jsonify
from flask_cors import CORS
import mimetypes
import gzip
from datetime import datetime, timedelta

real_script_path = os.path.realpath(__file__)
project_root = os.path.abspath(os.path.join(os.path.dirname(real_script_path), '..'))
os.chdir(project_root)
sys.path.insert(0, project_root)

from api.routes.user_routes import user_bp
from api.routes.quota_routes import quota_bp  
from api.routes.system_routes import system_bp
from api.middleware.auth_middleware import AuthMiddleware
from api.middleware.error_handler import ErrorHandler

def create_app() -> Flask:
    """
    Creates and configures the Flask application with all routes and middleware.
    Serves both API endpoints and static frontend files.
    """
    app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
    app.config['SECRET_KEY'] = os.environ.get('API_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Optimize for static file serving
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static assets
    
    CORS(app)
    
    AuthMiddleware.init_app(app)
    ErrorHandler.init_app(app)
    
    # API routes
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(quota_bp, url_prefix='/api/quota')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'OpenVPN Manager API is running'}
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Authenticate with API key and return success status."""
        data = request.get_json()
        if not data or 'api_key' not in data:
            return jsonify({
                'error': 'API key required',
                'message': 'Please provide api_key in request body'
            }), 400
        
        provided_key = data['api_key']
        expected_key = os.environ.get('OPENVPN_API_KEY')
        
        if not expected_key:
            return jsonify({
                'error': 'API not configured',
                'message': 'API key not configured on server'
            }), 500
        
        if not hmac.compare_digest(provided_key.encode(), expected_key.encode()):
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is invalid'
            }), 401
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'token': provided_key  # Use API key as token
        })
    
    # Frontend routes - serve static files
    @app.route('/')
    def serve_index():
        """Serve the main index.html file with security headers"""
        try:
            response = make_response(send_file(os.path.join(project_root, 'frontend/dist/index.html')))
            
            # No cache for main HTML
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            # Security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws: wss:;"
            
            return response
        except FileNotFoundError:
            return {'error': 'Frontend not built', 'message': 'Please build the frontend first'}, 404
    
    @app.route('/<path:path>')
    def serve_static_files(path):
        """Serve static files with optimized caching and compression"""
        static_dir = os.path.join(project_root, 'frontend/dist')
        file_path = os.path.join(static_dir, path)
        
        # If file exists, serve it with optimized headers
        if os.path.exists(file_path):
            response = make_response(send_from_directory(static_dir, path))
            
            # Set cache headers based on file type
            if path.endswith(('.css', '.js', '.svg', '.woff', '.woff2', '.ttf', '.eot')):
                # Static assets - cache for 1 year
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                response.headers['Expires'] = (datetime.utcnow() + timedelta(days=365)).strftime('%a, %d %b %Y %H:%M:%S GMT')
            elif path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico')):
                # Images - cache for 30 days
                response.headers['Cache-Control'] = 'public, max-age=2592000'
                response.headers['Expires'] = (datetime.utcnow() + timedelta(days=30)).strftime('%a, %d %b %Y %H:%M:%S GMT')
            elif path.endswith('.html'):
                # HTML files - no cache
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            
            # Add security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Add compression hint for text files
            if path.endswith(('.css', '.js', '.html', '.svg', '.json')):
                response.headers['Vary'] = 'Accept-Encoding'
            
            return response
        
        # If it's a frontend route (not API), serve index.html for SPA routing
        if not path.startswith('api/'):
            try:
                response = make_response(send_file(os.path.join(static_dir, 'index.html')))
                # No cache for SPA routes
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                
                # Security headers
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'DENY'
                response.headers['X-XSS-Protection'] = '1; mode=block'
                response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws: wss:;"
                
                return response
            except FileNotFoundError:
                return {'error': 'Frontend not built', 'message': 'Please build the frontend first'}, 404
        
        # Return 404 for unknown API routes
        return {'error': 'Not found'}, 404
    
    return app

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("API server must be run as root for OpenVPN operations.")
        sys.exit(1)
        
    app = create_app()
    print("🚀 Starting OpenVPN Manager on http://0.0.0.0:5000")
    print("📱 Web Panel: http://YOUR_IP:5000")
    print("🔗 API: http://YOUR_IP:5000/api")
    app.run(host='0.0.0.0', port=5000, debug=False)