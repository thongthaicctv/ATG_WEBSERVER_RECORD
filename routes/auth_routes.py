# routes/auth_routes.py
# -*- coding: utf-8 -*-

from flask import Blueprint, redirect, render_template, request, url_for

from core.auth_manager import authenticate, login_user, logout_user


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
