"""
Profile management routes for VPN user profile tokens and public access.
"""

from flask import Blueprint, request, jsonify, render_template_string, g, make_response
from api.middleware.jwt_middleware import JWTMiddleware
from data.db import Database
from data.user_repository import UserRepository
from data.blacklist_repository import BlacklistRepository
from service.security_service import SecurityService
from core.exceptions import AuthenticationError, ValidationError
import time

profile_bp = Blueprint('profile', __name__)

def get_security_service() -> SecurityService:
    """Factory function to create SecurityService with dependencies."""
    db = Database()
    user_repo = UserRepository(db)
    blacklist_repo = BlacklistRepository(db)
    
    return SecurityService(user_repo, blacklist_repo)

def check_ip_rate_limit(client_ip: str, max_requests: int = 60, window_minutes: int = 1) -> bool:
    """Simple IP-based rate limiting for public endpoints."""
    security_service = get_security_service()
    return security_service.check_profile_rate_limit(client_ip, max_requests, window_minutes)

@profile_bp.route('/users/<int:user_id>/profile-link', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('profile:generate')
def generate_profile_link(user_id):
    """
    Generate or get existing profile link for VPN user.
    """
    try:
        current_admin = g.current_admin
        security_service = get_security_service()
        
        result = security_service.generate_profile_token(
            user_id, 
            current_admin['admin_id'], 
            current_admin['role']
        )
        
        base_url = request.host_url.rstrip('/')
        result['profile_url'] = f"{base_url}/profile/{result['profile_token']}"
        
        return jsonify(result), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except AuthenticationError as e:
        return jsonify({
            'error': 'Access denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Profile link generation error',
            'message': 'Unable to generate profile link'
        }), 500

@profile_bp.route('/users/<int:user_id>/profile-link', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('profile:generate')
def get_profile_link(user_id):
    """
    Get existing profile link for VPN user.
    """
    try:
        current_admin = g.current_admin
        security_service = get_security_service()
        
        # Check if user exists and admin has access
        db = Database()
        user_repo = UserRepository(db)
        user = user_repo.find_user_by_username(str(user_id))
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': f'User ID {user_id} not found'
            }), 404
        
        if current_admin['role'] != 'admin' and user.get('created_by') != current_admin['admin_id']:
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this user'
            }), 403
        
        if not user.get('profile_token'):
            return jsonify({
                'has_profile_link': False,
                'message': 'No profile link generated for this user'
            }), 200
        
        base_url = request.host_url.rstrip('/')
        profile_url = f"{base_url}/profile/{user['profile_token']}"
        
        return jsonify({
            'has_profile_link': True,
            'profile_token': user['profile_token'],
            'profile_url': profile_url
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Error retrieving profile link',
            'message': 'Unable to get profile link'
        }), 500

@profile_bp.route('/users/<int:user_id>/profile-link', methods=['PUT'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('profile:generate')
def regenerate_profile_link(user_id):
    """
    Regenerate profile link for VPN user.
    """
    try:
        current_admin = g.current_admin
        security_service = get_security_service()
        
        result = security_service.regenerate_profile_token(
            user_id, 
            current_admin['admin_id'], 
            current_admin['role']
        )
        
        base_url = request.host_url.rstrip('/')
        result['profile_url'] = f"{base_url}/profile/{result['profile_token']}"
        
        return jsonify(result), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except AuthenticationError as e:
        return jsonify({
            'error': 'Access denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Profile link regeneration error',
            'message': 'Unable to regenerate profile link'
        }), 500

@profile_bp.route('/users/<int:user_id>/profile-link', methods=['DELETE'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('profile:revoke')
def revoke_profile_access(user_id):
    """
    Revoke profile access for VPN user.
    """
    try:
        current_admin = g.current_admin
        security_service = get_security_service()
        
        result = security_service.revoke_profile_access(
            user_id, 
            current_admin['admin_id'], 
            current_admin['role']
        )
        
        return jsonify(result), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except AuthenticationError as e:
        return jsonify({
            'error': 'Access denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Profile revocation error',
            'message': 'Unable to revoke profile access'
        }), 500

@profile_bp.route('/users/<int:user_id>/profile-stats', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('users:read')
def get_profile_stats(user_id):
    """
    Get profile access statistics for VPN user.
    """
    try:
        current_admin = g.current_admin
        security_service = get_security_service()
        
        stats = security_service.get_profile_stats(
            user_id, 
            current_admin['admin_id'], 
            current_admin['role']
        )
        
        return jsonify(stats), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except AuthenticationError as e:
        return jsonify({
            'error': 'Access denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Error retrieving stats',
            'message': 'Unable to get profile statistics'
        }), 500

# Public profile endpoints (no authentication required)

@profile_bp.route('/<profile_token>', methods=['GET'])
def public_profile_view(profile_token):
    """
    Public profile view (HTML page).
    """
    try:
        client_ip = request.remote_addr
        
        if not check_ip_rate_limit(client_ip):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429
        
        security_service = get_security_service()
        user = security_service.validate_profile_access(profile_token, client_ip)
        profile_data = security_service.get_profile_data(profile_token)
        
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VPN Profile - {{ username }}</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                .header { text-align: center; margin-bottom: 30px; }
                .card { background: #f5f5f5; padding: 20px; margin: 10px 0; border-radius: 8px; }
                .quota-bar { width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }
                .quota-fill { height: 100%; background: #4CAF50; transition: width 0.3s; }
                .quota-fill.warning { background: #FF9800; }
                .quota-fill.danger { background: #F44336; }
                .download-btn { display: inline-block; padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
                .stats { font-size: 0.9em; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>VPN Profile</h1>
                <h2>{{ username }}</h2>
                <p>Status: <strong>{{ status|title }}</strong></p>
            </div>
            
            <div class="card">
                <h3>Quota Information</h3>
                {% if quota.limit_gb > 0 %}
                <p>Used: {{ quota.used_gb }} GB / {{ quota.limit_gb }} GB</p>
                <div class="quota-bar">
                    <div class="quota-fill {% if quota.usage_percent > 90 %}danger{% elif quota.usage_percent > 75 %}warning{% endif %}" 
                         style="width: {{ quota.usage_percent }}%"></div>
                </div>
                <p>Remaining: {{ quota.remaining_gb }} GB ({{ quota.usage_percent }}% used)</p>
                {% else %}
                <p>Unlimited quota</p>
                <p>Used: {{ quota.used_gb }} GB</p>
                {% endif %}
            </div>
            
            <div class="card">
                <h3>Connection Status</h3>
                <p>Currently: <strong>{% if connection.is_online %}Online{% else %}Offline{% endif %}</strong></p>
                <p>Total Sessions: {{ connection.total_sessions }}</p>
                {% if connection.last_connection %}
                <p>Last Connection: {{ connection.last_connection }}</p>
                {% endif %}
            </div>
            
            <div class="card">
                <h3>Download Configuration</h3>
                <a href="{{ download_links.ovpn_config }}" class="download-btn">Download OpenVPN Config</a>
                <a href="{{ download_links.qr_code }}" class="download-btn">QR Code</a>
            </div>
            
            <div class="card stats">
                <h3>Statistics</h3>
                <p>Profile Access Count: {{ statistics.total_access_count }}</p>
                {% if statistics.last_accessed %}
                <p>Last Accessed: {{ statistics.last_accessed }}</p>
                {% endif %}
                <p>Profile Created: {{ statistics.profile_created }}</p>
            </div>
        </body>
        </html>
        """
        
        response = make_response(render_template_string(html_template, **profile_data))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except ValidationError as e:
        return jsonify({
            'error': 'Invalid profile',
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'error': 'Profile access error',
            'message': 'Unable to access profile'
        }), 500

@profile_bp.route('/<profile_token>/data', methods=['GET'])
def public_profile_data(profile_token):
    """
    Public profile data (JSON API).
    """
    try:
        client_ip = request.remote_addr
        
        if not check_ip_rate_limit(client_ip):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429
        
        security_service = get_security_service()
        user = security_service.validate_profile_access(profile_token, client_ip)
        profile_data = security_service.get_profile_data(profile_token)
        
        return jsonify(profile_data), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Invalid profile',
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'error': 'Profile access error',
            'message': 'Unable to access profile data'
        }), 500

@profile_bp.route('/<profile_token>/config.ovpn', methods=['GET'])
def download_ovpn_config(profile_token):
    """
    Download OpenVPN configuration file.
    """
    try:
        client_ip = request.remote_addr
        
        if not check_ip_rate_limit(client_ip):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429
        
        security_service = get_security_service()
        user = security_service.validate_profile_access(profile_token, client_ip)
        
        # Generate OpenVPN config using existing user service
        from service.user_service import UserService
        from core.openvpn_manager import OpenVPNManager
        from core.login_user_manager import LoginUserManager
        
        db = Database()
        user_repo = UserRepository(db)
        login_manager = LoginUserManager()
        openvpn_manager = OpenVPNManager()
        user_service = UserService(user_repo, openvpn_manager, login_manager)
        
        config_content = user_service._generate_user_certificate_config(user['username'])
        
        if not config_content:
            return jsonify({
                'error': 'Configuration not available',
                'message': 'VPN configuration could not be generated'
            }), 404
        
        response = make_response(config_content)
        response.headers['Content-Type'] = 'application/x-openvpn-profile'
        response.headers['Content-Disposition'] = f'attachment; filename="{user["username"]}.ovpn"'
        
        return response
        
    except ValidationError as e:
        return jsonify({
            'error': 'Invalid profile',
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'error': 'Configuration download error',
            'message': 'Unable to download configuration'
        }), 500

@profile_bp.route('/<profile_token>/qr-code', methods=['GET'])
def get_qr_code(profile_token):
    """
    Generate QR code for mobile VPN setup.
    """
    try:
        client_ip = request.remote_addr
        
        if not check_ip_rate_limit(client_ip):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429
        
        # For now, return a placeholder response
        # In production, you would generate an actual QR code image
        return jsonify({
            'message': 'QR code generation not implemented',
            'download_url': f'/api/profile/{profile_token}/config.ovpn'
        }), 501
        
    except Exception as e:
        return jsonify({
            'error': 'QR code generation error',
            'message': 'Unable to generate QR code'
        }), 500