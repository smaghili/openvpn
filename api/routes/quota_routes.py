from flask import Blueprint, request, jsonify
from api.middleware.jwt_middleware import JWTMiddleware
from service.user_service import UserService
from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from data.db import Database
from data.user_repository import UserRepository

quota_bp = Blueprint('quota', __name__)

def get_user_service() -> UserService:
    """Factory function to create UserService with all dependencies."""
    db = Database()
    user_repo = UserRepository(db)
    login_manager = LoginUserManager()
    openvpn_manager = OpenVPNManager()
    return UserService(user_repo, openvpn_manager, login_manager)

def bytes_to_human(byte_count: int) -> str:
    """Converts a byte count to a human-readable format (KB, MB, GB)."""
    if byte_count is None or not isinstance(byte_count, (int, float)):
        return "N/A"
    if byte_count == 0:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while byte_count >= power and n < len(power_labels) - 1:
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}"

@quota_bp.route('/<username>', methods=['PUT'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('quota:manage')
def set_user_quota(username: str):
    """
    Set data quota for a specific user.
    
    Request body:
    {
        "quota_gb": float (0 for unlimited)
    }
    """
    data = request.get_json()
    
    if not data or 'quota_gb' not in data:
        return jsonify({
            'error': 'Missing required field',
            'message': 'quota_gb is required'
        }), 400
    
    try:
        quota_gb = float(data['quota_gb'])
        if quota_gb < 0:
            return jsonify({
                'error': 'Invalid quota',
                'message': 'Quota cannot be negative'
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            'error': 'Invalid quota format',
            'message': 'quota_gb must be a valid number'
        }), 400
    
    user_service = get_user_service()
    user_service.set_quota_for_user(username, quota_gb)
    
    quota_bytes = int(quota_gb * 1024 * 1024 * 1024) if quota_gb > 0 else 0
    
    return jsonify({
        'message': f'Quota set successfully for user "{username}"',
        'username': username,
        'quota_gb': quota_gb,
        'quota_bytes': quota_bytes,
        'quota_human': bytes_to_human(quota_bytes) if quota_bytes > 0 else 'Unlimited'
    }), 200

@quota_bp.route('/<username>', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('quota:manage')
def get_user_status(username: str):
    """Get detailed traffic status and quota information for a specific user."""
    user_service = get_user_service()
    status = user_service.get_user_status(username)
    
    if not status:
        return jsonify({
            'error': 'Status not available',
            'message': f'Could not retrieve status for user "{username}"'
        }), 404
    
    quota = status.get('quota_bytes', 0)
    used = status.get('bytes_used', 0)
    
    response_data = {
        'username': status['username'],
        'quota_bytes': quota,
        'quota_human': bytes_to_human(quota) if quota > 0 else 'Unlimited',
        'bytes_used': used,
        'bytes_used_human': bytes_to_human(used),
        'usage_percentage': round((used / quota) * 100, 2) if quota > 0 else None,
        'remaining_bytes': quota - used if quota > 0 else None,
        'remaining_human': bytes_to_human(quota - used) if quota > 0 else None,
        'is_over_quota': used > quota if quota > 0 else False
    }
    
    return jsonify({
        'message': f'Status retrieved for user "{username}"',
        'status': response_data
    }), 200