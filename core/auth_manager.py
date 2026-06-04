# core/auth_manager.py
# -*- coding: utf-8 -*-

from functools import wraps

from flask import abort, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db.mysql_client import execute, fetch_all, fetch_one


DEFAULT_USERS = [
    ("root", "root@6688", "root"),
    ("admin", "admin@123", "admin"),
    ("vanhanh", "vanhanh@123", "vanhanh"),
]

PUBLIC_ENDPOINTS = {
    "auth.login",
    "auth.logout",
    "static",
}

ROLE_PERMISSIONS = {
    "root": {"*"},
    "admin": {
        "dashboard",
        "orders",
        "video_view",
        "video_download",
        "reports",
        "user_passwords",
    },
    "vanhanh": {
        "dashboard",
        "orders",
        "video_view",
        "video_download",
    },
}


def ensure_default_users():
    for username, password, role in DEFAULT_USERS:
        existing = fetch_one(
            """
            SELECT id
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            [username],
        )
        if existing:
            continue

        execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                employee_code,
                employee_name,
                role,
                is_active,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, 1, NOW(), NOW())
            """,
            [
                username,
                generate_password_hash(password),
                username,
                username,
                role,
            ],
        )


def authenticate(username, password):
    user = fetch_one(
        """
        SELECT id, username, password_hash, employee_code, employee_name, role, is_active
        FROM users
        WHERE username = %s
        LIMIT 1
        """,
        [username],
    )

    if not user or not user.get("is_active"):
        return None

    stored_password = user.get("password_hash") or ""
    password_ok = check_password_hash(stored_password, password)
    if not password_ok and stored_password == password:
        password_ok = True

    if not password_ok:
        return None

    execute(
        """
        UPDATE users
        SET last_login_at = NOW()
        WHERE id = %s
        """,
        [user.get("id")],
    )

    return user


def login_user(user):
    session.clear()
    session["user_id"] = user.get("id")
    session["username"] = user.get("username")
    session["role"] = user.get("role") or "vanhanh"
    session["employee_name"] = user.get("employee_name") or user.get("username")


def logout_user():
    session.clear()


def current_user():
    if not session.get("user_id"):
        return None

    return {
        "id": session.get("user_id"),
        "username": session.get("username"),
        "role": session.get("role") or "vanhanh",
        "employee_name": session.get("employee_name") or session.get("username"),
    }


def list_users_for_password_change():
    return fetch_all(
        """
        SELECT
            id,
            username,
            employee_code,
            employee_name,
            role,
            is_active,
            last_login_at,
            created_at,
            updated_at
        FROM users
        ORDER BY
            CASE role
                WHEN 'root' THEN 1
                WHEN 'admin' THEN 2
                WHEN 'vanhanh' THEN 3
                ELSE 9
            END,
            username ASC
        """
    )


def get_user_by_id(user_id):
    return fetch_one(
        """
        SELECT id, username, employee_code, employee_name, role, is_active
        FROM users
        WHERE id = %s
        LIMIT 1
        """,
        [user_id],
    )


def update_user_password(user_id, new_password):
    return execute(
        """
        UPDATE users
        SET password_hash = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        [generate_password_hash(new_password), user_id],
    )


def has_permission(permission):
    user = current_user()
    if not user:
        return False

    permissions = ROLE_PERMISSIONS.get(user.get("role"), set())
    return "*" in permissions or permission in permissions


def require_permission(permission):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user():
                return redirect(url_for("auth.login", next=request.full_path))
            if not has_permission(permission):
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def permission_for_endpoint(endpoint):
    if not endpoint or endpoint in PUBLIC_ENDPOINTS:
        return None

    if endpoint == "dashboard.index":
        return "dashboard"

    if endpoint.startswith("orders."):
        return "orders"

    if endpoint in {"video_ecom.index", "video_wholesale.index", "video.play_video", "video.get_video_link"}:
        return "video_view"

    if endpoint == "video.download_video":
        return "video_download"

    if endpoint == "auth.password_users":
        return "user_passwords"

    if endpoint.startswith("reports."):
        return "reports"

    if endpoint.startswith("settings.") or endpoint.startswith("shipping."):
        return "*"

    return "*"


def register_auth_guards(app):
    @app.before_request
    def enforce_permissions():
        permission = permission_for_endpoint(request.endpoint)
        if permission is None:
            return None

        if not current_user():
            return redirect(url_for("auth.login", next=request.full_path))

        if permission == "*":
            if not has_permission("*"):
                abort(403)
            return None

        if not has_permission(permission):
            abort(403)

        return None

    @app.context_processor
    def inject_auth_context():
        return {
            "current_user": current_user(),
            "can_access": has_permission,
        }
