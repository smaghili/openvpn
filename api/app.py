#!/usr/bin/env python3
import os
import sys
from flask import Flask, send_from_directory, request, redirect, url_for
from flask_cors import CORS
from config.app_config import get_config
from core.logging_config import setup_structured_logging, get_logger
from core.health_check_manager import get_health_check_manager

from .routes.user_routes import user_bp
from .routes.quota_routes import quota_bp
from .routes.system_routes import system_bp
from .routes.auth_routes import auth_bp
from .routes.admin_routes import admin_bp
from .routes.permission_routes import permission_bp
from .routes import profile_routes
from .middleware.jwt_middleware import JWTMiddleware
from .middleware.error_handler import ErrorHandler
from .middleware.auth_middleware import AuthMiddleware

def create_app() -> Flask:
    setup_structured_logging()
    logger = get_logger("app")
    app = Flask(__name__, static_folder='../ui', static_url_path='/')
    config = get_config()
    app.config['SECRET_KEY'] = config.security.secret_key
    
    CORS(app)

    AuthMiddleware.init_app(app)
    JWTMiddleware.init_app(app)
    ErrorHandler.init_app(app)
    
    # API routes
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admins')
    app.register_blueprint(permission_bp, url_prefix='/api/permissions')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(quota_bp, url_prefix='/api/quota')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    app.register_blueprint(profile_routes.profile_bp, url_prefix="/api/profile")

    @app.route("/api/health")
    def health_check():
        try:
            health_manager = get_health_check_manager()
            health_status = health_manager.check_all_services()
            return health_status, 200
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}, 500

    # Public profile routes (no authentication required)
    @app.route("/profile/<profile_token>")
    def public_profile_view(profile_token):
        return profile_routes.public_profile_view(profile_token)

    @app.route("/profile/<profile_token>/data")
    def public_profile_data(profile_token):
        return profile_routes.public_profile_data(profile_token)

    @app.route('/profile/<profile_token>/config.ovpn')
    def download_ovpn_config(profile_token):
        return profile_routes.download_ovpn_config(profile_token)
    
    # Web UI routes
    @app.route('/')
    def index():
        return redirect('/login')
    @app.route('/login')
    def login():
        return app.send_static_file('login/login.html')
    @app.route('/overview')
    def overview():
        return app.send_static_file('overview/overview.html')
    
    @app.route('/users')
    def users():
        return app.send_static_file('users.html')
    
    @app.route('/openvpn')
    def openvpn():
        return app.send_static_file('openvpn.html')
    
    @app.route('/wireguard')
    def wireguard():
        return app.send_static_file('wireguard.html')
    
    @app.route('/settings')
    def settings():
        return app.send_static_file('settings.html')
    
    @app.route('/shared/sidebar.html')
    def sidebar():
        return app.send_static_file('shared/sidebar.html')
    
    @app.route('/ui/image/<filename>')
    def serve_image(filename):
        return send_from_directory('../ui/image', filename)
    return app


def main() -> None:
    if os.geteuid() != 0:
        logger.error("API server must be run as root for OpenVPN operations.")
        sys.exit(1)

    try:
        app = create_app()
        config = get_config()
        
        logger.info(
            "Starting OpenVPN Manager API Server",
            host=config.server.host,
            port=config.server.port,
            threads=config.server.threads
        )

        from waitress import serve
        import logging
        logging.getLogger('waitress.queue').setLevel(logging.ERROR)

        serve(
            app, 
            host=config.server.host, 
            port=config.server.port, 
            threads=config.server.threads
        )
        
    except Exception as e:
        logger.error("Failed to start API server", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
