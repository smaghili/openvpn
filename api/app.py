#!/usr/bin/env python3
import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS

real_script_path = os.path.realpath(__file__)
project_root = os.path.abspath(os.path.join(os.path.dirname(real_script_path), '..'))
os.chdir(project_root)
sys.path.insert(0, project_root)

from api.routes.user_routes import user_bp
from api.routes.quota_routes import quota_bp  
from api.routes.system_routes import system_bp
from api.routes.auth_routes import auth_bp
from api.routes.admin_routes import admin_bp
from api.routes.permission_routes import permission_bp
from api.routes.profile_routes import profile_bp
from api.middleware.jwt_middleware import JWTMiddleware
from api.middleware.error_handler import ErrorHandler

def create_app() -> Flask:
    """
    Creates and configures the Flask application with API endpoints only.
    Frontend web panel has been removed - only REST API is available.
    """
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('API_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    CORS(app)
    
    JWTMiddleware.init_app(app)
    ErrorHandler.init_app(app)
    
    # API routes
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admins')
    app.register_blueprint(permission_bp, url_prefix='/api/permissions')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(quota_bp, url_prefix='/api/quota')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    
    # Profile routes
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'OpenVPN Manager API is running'}
    
    # Public profile routes (no authentication required)
    @app.route('/profile/<profile_token>')
    def public_profile_view(profile_token):
        """Public profile view - delegate to profile routes."""
        from api.routes.profile_routes import public_profile_view as profile_view
        return profile_view(profile_token)
    
    @app.route('/profile/<profile_token>/data')
    def public_profile_data(profile_token):
        """Public profile data API - delegate to profile routes."""
        from api.routes.profile_routes import public_profile_data as profile_data
        return profile_data(profile_token)
    
    @app.route('/profile/<profile_token>/config.ovpn')
    def download_ovpn_config(profile_token):
        """Download OpenVPN config - delegate to profile routes."""
        from api.routes.profile_routes import download_ovpn_config as download_config
        return download_config(profile_token)
    

    
    # API-only server - no frontend routes
    @app.route('/')
    def api_info():
        """API information endpoint"""
        return {
            'message': 'OpenVPN Manager API Server',
            'version': '2.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/api/health',
                'auth': '/api/auth/*',
                'users': '/api/users/*',
                'system': '/api/system/*',
                'profiles': '/api/profile/*'
            },
            'note': 'Web panel has been removed - API only'
        }
    
    return app

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("API server must be run as root for OpenVPN operations.")
        sys.exit(1)
        
    app = create_app()
    port = int(os.environ.get('API_PORT', 5000))
    print(f"🚀 Starting OpenVPN Manager API Server on http://0.0.0.0:{port}")
    print(f"🔗 API Endpoints: http://YOUR_IP:{port}/api")
    print(f"📊 Health Check: http://YOUR_IP:{port}/api/health")
    print(f"ℹ️  Web Panel: REMOVED (API-only mode)")
    app.run(host='0.0.0.0', port=port, debug=False)