# routes/auth_routes.py
# -*- coding: utf-8 -*-

from flask import Blueprint, abort, redirect, render_template, request, url_for

from core.auth_manager import (
    authenticate,
    current_user,
    get_user_by_id,
    list_users_for_password_change,
    login_user,
    logout_user,
    update_user_password,
)


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    next_url = request.args.get("next") or request.form.get("next") or url_for("dashboard.index")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = authenticate(username, password)
        if user:
            login_user(user)
            return redirect(next_url or url_for("dashboard.index"))

        error = "Sai tài khoản hoặc mật khẩu."

    return render_template("auth/login.html", error=error, next_url=next_url)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/users/passwords", methods=["GET", "POST"])
def password_users():
    actor = current_user()
    if not actor or actor.get("role") not in {"root", "admin"}:
        abort(403)

    error = ""
    message = ""

    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        target_user = get_user_by_id(user_id) if user_id else None

        if not target_user:
            error = "Không tìm thấy tài khoản cần đổi mật khẩu."
        elif target_user.get("role") == "root" and actor.get("role") != "root":
            error = "Chỉ tài khoản root mới được đổi mật khẩu root."
        elif len(new_password) < 6:
            error = "Mật khẩu mới cần tối thiểu 6 ký tự."
        elif new_password != confirm_password:
            error = "Mật khẩu xác nhận không khớp."
        else:
            update_user_password(target_user.get("id"), new_password)
            message = f"Đã đổi mật khẩu cho tài khoản {target_user.get('username')}."

    users = list_users_for_password_change()

    if actor.get("role") != "root":
        users = [user for user in users if user.get("role") != "root"]

    return render_template(
        "auth/password_users.html",
        users=users,
        error=error,
        message=message,
    )
