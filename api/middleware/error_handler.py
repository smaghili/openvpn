from flask import jsonify
from core.exceptions import (
    VPNManagerError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ConfigurationError,
    ValidationError,
    CertificateGenerationError,
    DatabaseError,
    BackupError,
    RestoreError
)

class ErrorHandler:
    """
    Centralized error handling for OpenVPN Manager API.
    """
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize error handlers with Flask app."""
        
        @app.errorhandler(UserAlreadyExistsError)
        def handle_user_exists(e):
            return jsonify({
                'error': 'User already exists',
                'message': str(e)
            }), 409
        
        @app.errorhandler(UserNotFoundError)
        def handle_user_not_found(e):
            return jsonify({
                'error': 'User not found',
                'message': str(e)
            }), 404
        
        @app.errorhandler(ValidationError)
        def handle_validation_error(e):
            return jsonify({
                'error': 'Validation error',
                'message': str(e)
            }), 400
        
        @app.errorhandler(ConfigurationError)
        def handle_config_error(e):
            return jsonify({
                'error': 'Configuration error',
                'message': str(e)
            }), 400
        
        @app.errorhandler(CertificateGenerationError)
        def handle_cert_error(e):
            return jsonify({
                'error': 'Certificate generation error',
                'message': str(e)
            }), 500
        
        @app.errorhandler(DatabaseError)
        def handle_database_error(e):
            return jsonify({
                'error': 'Database error',
                'message': str(e)
            }), 500
        
        @app.errorhandler(BackupError)
        def handle_backup_error(e):
            return jsonify({
                'error': 'Backup error',
                'message': str(e)
            }), 500
        
        @app.errorhandler(RestoreError)
        def handle_restore_error(e):
            return jsonify({
                'error': 'Restore error',
                'message': str(e)
            }), 500
        
        @app.errorhandler(VPNManagerError)
        def handle_vpn_error(e):
            return jsonify({
                'error': 'VPN Manager error',
                'message': str(e)
            }), 500
        
        @app.errorhandler(Exception)
        def handle_generic_error(e):
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }), 500
        
        @app.errorhandler(404)
        def handle_not_found(e):
            return jsonify({
                'error': 'Not found',
                'message': 'The requested endpoint does not exist'
            }), 404
        
        @app.errorhandler(405)
        def handle_method_not_allowed(e):
            return jsonify({
                'error': 'Method not allowed',
                'message': 'The HTTP method is not allowed for this endpoint'
            }), 405