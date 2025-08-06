#!/usr/bin/env python3
import os
import sys
from flask import Flask, send_from_directory, send_file
from flask_cors import CORS

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
    
    # Frontend routes - serve static files
    @app.route('/')
    def serve_index():
        """Serve the main index.html file"""
        try:
            return send_file(os.path.join(project_root, 'frontend/dist/index.html'))
        except FileNotFoundError:
            return {'error': 'Frontend not built', 'message': 'Please build the frontend first'}, 404
    
    @app.route('/<path:path>')
    def serve_static_files(path):
        """Serve static files (CSS, JS, images, etc.)"""
        static_dir = os.path.join(project_root, 'frontend/dist')
        
        # If file exists, serve it
        if os.path.exists(os.path.join(static_dir, path)):
            return send_from_directory(static_dir, path)
        
        # If it's a frontend route (not API), serve index.html for SPA routing
        if not path.startswith('api/'):
            try:
                return send_file(os.path.join(static_dir, 'index.html'))
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