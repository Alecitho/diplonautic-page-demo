"""Autenticación de empleados: registro, verificación de correo, acceso y roles.

Decisión de diseño (alta de usuarios):
  Modelo mixto. Cualquier empleado puede registrarse con su correo corporativo
  (@diplonautic.com), pero la cuenta queda "no verificada" y no puede entrar al
  foro hasta confirmar el correo. Además, un administrador puede dar de alta,
  verificar, cambiar el rol o desactivar cuentas desde el panel de administración.
  Así no se depende de que el administrador cree cada cuenta y se mantiene el
  control sobre quién accede al área privada.
"""
import functools
import hashlib
import re
import secrets
from datetime import datetime, timedelta

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db, now_iso

bp = Blueprint("auth", __name__)

ROLES = ("empleado", "admin")
DEPARTAMENTOS = ("Dirección", "Refrigeración", "Climatización", "Electricidad",
                 "Electrónica", "Fontanería", "Taller", "Administración")
VERIFICATION_HOURS = 48
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def hash_token(token):
    """Los tokens de verificación se guardan con hash: si se filtra la BD no sirven."""
    return hashlib.sha256(token.encode()).hexdigest()


def validate_password(password):
    """Devuelve un mensaje de error o None si la contraseña es válida."""
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "La contraseña debe combinar letras y números."
    return None


def validate_email(email):
    if not EMAIL_RE.match(email):
        return "Introduce un correo electrónico válido."
    domain = current_app.config["ALLOWED_EMAIL_DOMAIN"]
    if domain and not email.endswith("@" + domain):
        return f"Usa tu correo corporativo (@{domain})."
    return None


def read_user_form():
    """Campos comunes del formulario de usuario (registro y alta por el administrador)."""
    return {
        "name": request.form.get("name", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
        "department": request.form.get("department", ""),
    }


def validate_user_form(form, password):
    """Validación común del registro y del alta por el administrador.

    Devuelve un mensaje de error o None si los datos son válidos.
    """
    if len(form["name"]) < 3:
        return "Indica el nombre completo."
    if form["department"] not in DEPARTAMENTOS:
        return "Selecciona un departamento."
    error = validate_email(form["email"]) or validate_password(password)
    if error is None and get_db().execute(
            "SELECT 1 FROM users WHERE email = ?", (form["email"],)).fetchone():
        error = "Ya existe una cuenta con ese correo."
    return error


def issue_verification_token(user_id):
    """Genera un token nuevo, guarda su hash y devuelve el token en claro para el correo."""
    token = secrets.token_urlsafe(32)
    db = get_db()
    db.execute(
        "UPDATE users SET verification_token = ?, verification_sent_at = ? WHERE id = ?",
        (hash_token(token), now_iso(), user_id),
    )
    db.commit()
    return token


def render_demo_email(user, token):
    """En la DEMO no hay servidor SMTP: se muestra en pantalla el correo que se enviaría."""
    path = url_for("auth.verify", token=token)
    link = url_for("auth.verify", token=token, _external=True)
    current_app.logger.info("Correo de verificación para %s: %s", user["email"], link)
    # El botón usa la ruta relativa para funcionar tras cualquier dominio o proxy;
    # el enlace completo se muestra como lo vería el empleado en el correo.
    return render_template("auth/correo_demo.html", user=user, link=link, path=path,
                           horas=VERIFICATION_HOURS)


def safe_next(target):
    """Solo se permite redirigir a rutas internas (evita redirecciones abiertas)."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


# --------------------------------------------------------------------------
# Sesión y decoradores de permisos
# --------------------------------------------------------------------------
@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None or not user["is_active"]:
            session.clear()  # cuenta borrada o desactivada: se cierra la sesión
        else:
            g.user = user


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Inicia sesión para acceder al área privada.", "info")
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(**kwargs)
    return wrapped


def verified_required(view):
    @functools.wraps(view)
    @login_required
    def wrapped(**kwargs):
        if not g.user["is_verified"]:
            flash("Tu cuenta aún no está verificada. Confirma tu correo para acceder al foro.", "warning")
            return redirect(url_for("auth.area"))
        return view(**kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    @verified_required
    def wrapped(**kwargs):
        if g.user["role"] != "admin":
            abort(403)
        return view(**kwargs)
    return wrapped


# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
@bp.route("/registro", methods=("GET", "POST"))
def register():
    if g.user:
        return redirect(url_for("auth.area"))

    form = {"name": "", "email": "", "department": ""}
    if request.method == "POST":
        form = read_user_form()
        password = request.form.get("password", "")
        error = validate_user_form(form, password)
        if error is None and password != request.form.get("password2", ""):
            error = "Las contraseñas no coinciden."

        if error:
            flash(error, "error")
        else:
            db = get_db()
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash, role, department, created_at)"
                " VALUES (?, ?, ?, 'empleado', ?, ?)",
                (form["name"], form["email"], generate_password_hash(password),
                 form["department"], now_iso()),
            )
            db.commit()
            user = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
            token = issue_verification_token(user["id"])
            flash("Cuenta creada. Revisa tu correo para verificarla.", "success")
            return render_demo_email(user, token)

    return render_template("auth/registro.html", form=form, departamentos=DEPARTAMENTOS)


@bp.route("/verificar/<token>")
def verify(token):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE verification_token = ?",
                      (hash_token(token),)).fetchone()
    if user is None:
        flash("El enlace de verificación no es válido o ya se ha utilizado.", "error")
        return redirect(url_for("auth.login"))

    sent_at = datetime.fromisoformat(user["verification_sent_at"])
    if datetime.now() - sent_at > timedelta(hours=VERIFICATION_HOURS):
        flash("El enlace ha caducado. Inicia sesión y solicita uno nuevo.", "error")
        return redirect(url_for("auth.login"))

    db.execute(
        "UPDATE users SET is_verified = 1, verified_at = ?, verification_token = NULL WHERE id = ?",
        (now_iso(), user["id"]),
    )
    db.commit()
    flash("Correo verificado. Ya puedes acceder al foro interno.", "success")
    if g.user and g.user["id"] == user["id"]:
        return redirect(url_for("auth.area"))
    return redirect(url_for("auth.login"))


@bp.route("/verificacion/reenviar", methods=("POST",))
@login_required
def resend_verification():
    if g.user["is_verified"]:
        flash("Tu cuenta ya está verificada.", "info")
        return redirect(url_for("auth.area"))
    token = issue_verification_token(g.user["id"])
    return render_demo_email(g.user, token)


@bp.route("/acceso", methods=("GET", "POST"))
def login():
    if g.user:
        return redirect(url_for("auth.area"))

    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        # Mensaje genérico: no revela si el correo existe.
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Correo o contraseña incorrectos.", "error")
        elif not user["is_active"]:
            flash("Tu cuenta está desactivada. Contacta con un administrador.", "error")
        else:
            session.clear()  # evita fijación de sesión
            session["user_id"] = user["id"]
            db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_iso(), user["id"]))
            db.commit()
            flash(f"Hola, {user['name'].split()[0]}.", "success")
            if not user["is_verified"]:
                return redirect(url_for("auth.area"))
            return redirect(safe_next(request.args.get("next")) or url_for("auth.area"))

    return render_template("auth/login.html", email=email)


@bp.route("/salir", methods=("POST",))
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("public.index"))


@bp.route("/area-privada")
@login_required
def area():
    return render_template("auth/area.html")
