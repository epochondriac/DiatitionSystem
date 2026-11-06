"""Auth routes: login, change-password, and current user info."""

import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models import db, User

auth_bp = Blueprint('auth', __name__)

# A known fallback secret would let anyone forge tokens, so it is refused on Vercel
JWT_SECRET = os.environ.get('JWT_SECRET') or ''
if not JWT_SECRET:
    if os.environ.get('VERCEL'):
        raise RuntimeError('JWT_SECRET must be set in the Vercel environment variables')
    JWT_SECRET = 'dev-secret-change-in-production'
JWT_EXPIRY_HOURS = 720


def _make_token(user: User) -> str:
    """Generate a signed JWT for the given user."""
    payload = {
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'must_change_password': user.must_change_password,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def verify_token(req) -> dict | None:
    """Decode and return JWT payload from Authorization header, or None if invalid."""
    auth_header = req.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    try:
        return jwt.decode(auth_header[7:], JWT_SECRET, algorithms=['HS256'])
    except jwt.PyJWTError:
        return None


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and return a JWT + user info."""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({'error': 'שם משתמש או סיסמה שגויים'}), 401

    return jsonify({
        'token': _make_token(user),
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'must_change_password': user.must_change_password,
        },
    })


@auth_bp.route('/api/auth/change-password', methods=['POST'])
def change_password():
    """Change the authenticated user's password and issue a refreshed token."""
    payload = verify_token(request)
    if not payload:
        return jsonify({'error': 'לא מורשה'}), 401

    data = request.get_json() or {}
    current_password = data.get('currentPassword', '')
    new_password = data.get('newPassword', '')

    user = db.session.get(User, payload['id'])
    if not user or not bcrypt.checkpw(current_password.encode(), user.password_hash.encode()):
        return jsonify({'error': 'סיסמה נוכחית שגויה'}), 400

    user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    user.must_change_password = False
    db.session.commit()

    return jsonify({
        'token': _make_token(user),
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'must_change_password': user.must_change_password,
        },
    })


@auth_bp.route('/api/auth/me', methods=['GET'])
def me():
    """Return current user info based on JWT."""
    payload = verify_token(request)
    if not payload:
        return jsonify({'error': 'לא מורשה'}), 401

    user = db.session.get(User, payload['id'])
    if not user:
        return jsonify({'error': 'משתמש לא נמצא'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'must_change_password': user.must_change_password,
    })
