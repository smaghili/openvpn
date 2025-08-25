#!/usr/bin/env python3
import os
import sys
from flask import Flask, send_from_directory, request, redirect, url_for
from flask_cors import CORS


from .routes.user_routes import user_bp
from .routes.quota_routes import quota_bp
from .routes.system_routes import system_bp
from .routes.auth_routes import auth_bp
from .routes.admin_routes import admin_bp
from .routes.permission_routes import permission_bp
from .routes.profile_routes import profile_bp
from .middleware.jwt_middleware import JWTMiddleware
from .middleware.error_handler import ErrorHandler
from .middleware.auth_middleware import AuthMiddleware

def create_app() -> Flask:
    """
    Creates and configures the Flask application serving both API and web UI.
    """
    app = Flask(__name__, static_folder='../ui', static_url_path='/')
    secret_key = os.environ.get('API_SECRET_KEY')
    if not secret_key:
        raise RuntimeError('API_SECRET_KEY environment variable is required')
    app.config['SECRET_KEY'] = secret_key
    
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

    # Profile routes
    app.register_blueprint(profile_bp, url_prefix="/api/profile")

    @app.route("/api/health")
    def health_check():
        return {"status": "healthy", "message": "OpenVPN Manager API is running"}

    # Public profile routes (no authentication required)
    @app.route("/profile/<profile_token>")
    def public_profile_view(profile_token):
        """Public profile view - delegate to profile routes."""
        from .routes.profile_routes import public_profile_view as profile_view
        return profile_view(profile_token)

    @app.route("/profile/<profile_token>/data")
    def public_profile_data(profile_token):
        """Public profile data API - delegate to profile routes."""
        from .routes.profile_routes import public_profile_data as profile_data
        return profile_data(profile_token)

    @app.route('/profile/<profile_token>/config.ovpn')
    def download_ovpn_config(profile_token):
        """Download OpenVPN config - delegate to profile routes."""
        from .routes.profile_routes import download_ovpn_config as download_config
        return download_config(profile_token)
    
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

    @app.route('/<path:path>')
    def static_proxy(path):
        if path.endswith('.css'):
            response = send_from_directory(app.static_folder, path)
            response.headers['Content-Type'] = 'text/css'
            return response
        return send_from_directory(app.static_folder, path)
    
    return app


def main() -> None:
    if os.geteuid() != 0:
        print("API server must be run as root for OpenVPN operations.")
        sys.exit(1)

    app = create_app()
    port = int(os.environ.get("API_PORT", 5000))

    def calculate_optimal_threads() -> int:
        """Determine a sensible Waitress thread count based on CPU cores."""
        cores = os.cpu_count() or 1
        # Allow multiple concurrent connections per core but cap to avoid exhaustion
        return max(4, min(32, cores * 2))

    print(f"🚀 Starting OpenVPN Manager API Server on http://0.0.0.0:{port}")
    print(f"🔗 API Endpoints: http://YOUR_IP:{port}/api")
    print(f"📊 Health Check: http://YOUR_IP:{port}/api/health")

    from waitress import serve
    import logging

    # Suppress Waitress queue warnings
    logging.getLogger('waitress.queue').setLevel(logging.ERROR)

    serve(app, host="0.0.0.0", port=port, threads=calculate_optimal_threads())


if __name__ == "__main__":
    main()
