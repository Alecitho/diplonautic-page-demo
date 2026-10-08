"""Panel de administración: gestión de usuarios (solo rol administrador)."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from .auth import (DEPARTAMENTOS, ROLES, admin_required, issue_verification_token,
                   read_user_form, render_demo_email, validate_user_form)
from .db import get_db, get_or_404, now_iso

bp = Blueprint("admin", __name__, url_prefix="/admin")

FILTROS = {
    "todos": ("Todos", "1 = 1"),
    "verificados": ("Verificados", "is_verified = 1 AND is_active = 1"),
    "no-verificados": ("No verificados", "is_verified = 0 AND is_active = 1"),
    "administradores": ("Administradores", "role = 'admin'"),
    "desactivados": ("Desactivados", "is_active = 0"),
}


def get_user_or_404(user_id):
    return get_or_404("SELECT * FROM users WHERE id = ?", (user_id,))


def back_to_list():
    """Vuelve al listado conservando el filtro activo (validado contra FILTROS)."""
    estado = request.form.get("estado")
    return redirect(url_for("admin.users", estado=estado if estado in FILTROS else None))


def forbid_self(user, accion):
    """Un administrador no puede quitarse a sí mismo el rol ni desactivarse."""
    if user["id"] == g.user["id"]:
        flash(f"No puedes {accion} tu propia cuenta.", "error")
        return True
    return False


@bp.route("/usuarios")
@admin_required
def users():
    filtro = request.args.get("estado", "todos")
    if filtro not in FILTROS:
        filtro = "todos"
    db = get_db()
    # La condición SQL sale del diccionario FILTROS (valores fijos), nunca del usuario.
    rows = db.execute(
        f"SELECT * FROM users WHERE {FILTROS[filtro][1]} ORDER BY is_active DESC, name"
    ).fetchall()
    counts = {key: db.execute(f"SELECT COUNT(*) FROM users WHERE {cond}").fetchone()[0]
              for key, (_label, cond) in FILTROS.items()}
    return render_template("admin/usuarios.html", users=rows, filtros=FILTROS,
                           filtro=filtro, counts=counts)


@bp.route("/usuarios/nuevo", methods=("GET", "POST"))
@admin_required
def new_user():
    form = {"name": "", "email": "", "department": "", "role": "empleado", "verified": True}
    if request.method == "POST":
        form = {
            **read_user_form(),
            "role": request.form.get("role", "empleado"),
            "verified": request.form.get("verified") == "on",
        }
        password = request.form.get("password", "")
        error = validate_user_form(form, password)
        if error is None and form["role"] not in ROLES:
            error = "Rol no válido."

        if error:
            flash(error, "error")
        else:
            now = now_iso()
            db = get_db()
            db.execute(
                "INSERT INTO users (name, email, password_hash, role, department,"
                " is_verified, verified_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (form["name"], form["email"], generate_password_hash(password), form["role"],
                 form["department"], int(form["verified"]), now if form["verified"] else None, now),
            )
            db.commit()
            flash(f"Usuario {form['email']} creado.", "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/nuevo_usuario.html", form=form, roles=ROLES,
                           departamentos=DEPARTAMENTOS)


@bp.route("/usuarios/<int:user_id>/verificar", methods=("POST",))
@admin_required
def verify_user(user_id):
    user = get_user_or_404(user_id)
    db = get_db()
    db.execute(
        "UPDATE users SET is_verified = 1, verified_at = ?, verification_token = NULL WHERE id = ?",
        (now_iso(), user_id),
    )
    db.commit()
    flash(f"{user['name']} ya está verificado.", "success")
    return back_to_list()


@bp.route("/usuarios/<int:user_id>/enviar-verificacion", methods=("POST",))
@admin_required
def send_verification(user_id):
    user = get_user_or_404(user_id)
    if user["is_verified"]:
        flash("Ese usuario ya está verificado.", "info")
        return redirect(url_for("admin.users"))
    return render_demo_email(user, issue_verification_token(user_id))


@bp.route("/usuarios/<int:user_id>/rol", methods=("POST",))
@admin_required
def change_role(user_id):
    user = get_user_or_404(user_id)
    role = request.form.get("role")
    if role not in ROLES:
        abort(400)
    if not forbid_self(user, "cambiar el rol de"):
        db = get_db()
        db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        db.commit()
        flash(f"{user['name']} ahora es {role}.", "success")
    return back_to_list()


@bp.route("/usuarios/<int:user_id>/activo", methods=("POST",))
@admin_required
def toggle_active(user_id):
    user = get_user_or_404(user_id)
    if not forbid_self(user, "desactivar"):
        nuevo = 0 if user["is_active"] else 1
        db = get_db()
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (nuevo, user_id))
        db.commit()
        flash(f"Cuenta de {user['name']} {'activada' if nuevo else 'desactivada'}.", "success")
    return back_to_list()
