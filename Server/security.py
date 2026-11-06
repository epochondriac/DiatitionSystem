"""Global request guard: every API call needs a valid JWT; writes need staff roles."""

import os
from flask import request, jsonify
from flask_cors import CORS
from routes.auth import verify_token

# Endpoints reachable without logging in
PUBLIC_PATHS = {'/api/status', '/api/auth/login'}

# Admin-only areas (the system routes also check this themselves)
ADMIN_PREFIXES = ('/api/system/', '/api/run-migrations')

# Resources whose create/update/delete is limited to dietitians and admins
STAFF_WRITE_PREFIXES = (
    '/api/products', '/api/upload', '/api/categories',
    '/api/sensitivities', '/api/texture', '/api/diets',
)

# POST endpoints under /api/products that only read data (search/analysis)
READ_ONLY_POSTS = {
    '/api/products/semantic-search',
    '/api/products/balance-suggest',
    '/api/products/check-outlier',
}

STAFF_ROLES = {'admin', 'dietitian'}


def _deny(status: int, message: str):
    return jsonify({'error': message}), status


def _check_request():
    """Runs before every request; returns an error response to block it, or None."""
    path = request.path
    if request.method == 'OPTIONS' or path in PUBLIC_PATHS:
        return None
    if not (path.startswith('/api/') or path.startswith('/uploads/')):
        return None

    payload = verify_token(request)
    if not payload:
        return _deny(401, 'לא מורשה')
    role = payload.get('role')

    if path.startswith(ADMIN_PREFIXES) and role != 'admin':
        return _deny(403, 'גישה אסורה — נדרשות הרשאות מנהל')

    is_write = request.method in ('POST', 'PUT', 'PATCH', 'DELETE')
    if (is_write and path.startswith(STAFF_WRITE_PREFIXES)
            and path not in READ_ONLY_POSTS and role not in STAFF_ROLES):
        return _deny(403, 'גישה נדחתה')
    return None


def init_security(app):
    """Configures CORS from ALLOWED_ORIGINS and installs the auth guard."""
    origins = [o.strip().rstrip('/') for o in os.environ.get('ALLOWED_ORIGINS', '').split(',') if o.strip()]
    CORS(app, origins=origins or '*')
    app.before_request(_check_request)
