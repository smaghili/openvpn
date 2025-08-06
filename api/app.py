#!/usr/bin/env python3
import os
import sys
from flask import Flask
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
    """
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('API_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    CORS(app)
    
    AuthMiddleware.init_app(app)
    ErrorHandler.init_app(app)
    
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(quota_bp, url_prefix='/api/quota')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'OpenVPN Manager API is running'}
    
    return app

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("API server must be run as root for OpenVPN operations.")
        sys.exit(1)
        
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)