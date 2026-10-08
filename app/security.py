"""Protección CSRF sencilla basada en un token por sesión.

Cada formulario POST incluye un campo oculto csrf_token que debe coincidir con
el guardado en la sesión firmada. Evita que otra web envíe formularios en nombre
de un empleado que tenga la sesión abierta.
"""
import secrets

from flask import abort, request, session


def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


def init_app(app):
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.before_request
    def csrf_protect():
        if request.method != "POST" or not app.config.get("CSRF_ENABLED", True):
            return
        expected = session.get("_csrf_token")
        sent = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected, sent):
            abort(400, description="El formulario ha caducado. Recarga la página e inténtalo de nuevo.")
