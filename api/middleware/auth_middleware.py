import os
import hmac
from functools import wraps
from flask import request, jsonify, current_app

class AuthMiddleware:
    """
    Simple API key authentication middleware for OpenVPN Manager API.
    """
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize authentication middleware with Flask app.

        The middleware requires an ``OPENVPN_API_KEY`` environment variable
        to be present.  During application setup the key is read once and
        stored in the Flask configuration so subsequent requests do not need
        to access the environment repeatedly.
        """
        api_key = os.environ.get('OPENVPN_API_KEY')
        if not api_key:
            raise RuntimeError('OPENVPN_API_KEY environment variable is required')

        app.config['OPENVPN_API_KEY'] = api_key
    
    @staticmethod
    def require_auth(f):
        """Decorator to require API key authentication for protected endpoints."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                return jsonify({
                    'error': 'API key required',
                    'message': 'Please provide X-API-Key header'
                }), 401
            
            expected_key = current_app.config.get('OPENVPN_API_KEY')
            if not expected_key:
                return jsonify({
                    'error': 'API not configured',
                    'message': 'API key not configured on server'
                }), 500
            
            if not AuthMiddleware._verify_api_key(api_key, expected_key):
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid'
                }), 401
            
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def _verify_api_key(provided_key: str, expected_key: str) -> bool:
        """Securely verify API key using constant-time comparison."""
        return hmac.compare_digest(provided_key.encode(), expected_key.encode())
