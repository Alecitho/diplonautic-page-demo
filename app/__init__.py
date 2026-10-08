"""Fábrica de la aplicación Flask de la DEMO corporativa de Diplonautic."""
import os
from datetime import datetime

from flask import Flask, render_template


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        # En producción SECRET_KEY debe venir de una variable de entorno.
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-diplonautic-cambiar-en-produccion"),
        DATABASE=os.path.join(app.instance_path, "diplonautic.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        COMPANY_NAME="Diplonautic",
        # Solo se admiten registros con correo corporativo. Vacío = cualquier dominio.
        ALLOWED_EMAIL_DOMAIN=os.environ.get("ALLOWED_EMAIL_DOMAIN", "diplonautic.com"),
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    # Detrás de un proxy (p. ej. GitHub Codespaces) las URL absolutas deben usar el
    # dominio público. Solo se activa con TRUST_PROXY=1 para no fiarse de cabeceras
    # X-Forwarded-* cuando no hay proxy delante.
    if os.environ.get("TRUST_PROXY") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    from . import db, security
    db.init_app(app)
    security.init_app(app)

    @app.template_filter("fecha")
    def fecha(value, formato="%d/%m/%Y %H:%M"):
        """Formatea fechas ISO guardadas en la base de datos al formato español."""
        if not value:
            return ""
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        return value.strftime(formato)

    @app.context_processor
    def inject_globals():
        return {"company": app.config["COMPANY_NAME"], "current_year": datetime.now().year}

    from . import admin, auth, forum, public
    app.register_blueprint(public.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(forum.bp)

    def error_page(code, titulo, texto):
        def handler(error):
            detalle = getattr(error, "description", None) if code == 400 else None
            return render_template("error.html", code=code, titulo=titulo,
                                   texto=detalle or texto), code
        app.register_error_handler(code, handler)

    error_page(400, "Petición no válida", "No hemos podido procesar la petición.")
    error_page(403, "Acceso restringido", "No tienes permisos para realizar esta acción.")
    error_page(404, "Página no encontrada", "La página que buscas no existe o se ha movido.")

    return app
