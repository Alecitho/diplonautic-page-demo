"""Acceso a la base de datos SQLite y comandos de inicialización."""
import os
import sqlite3
from datetime import datetime

import click
from flask import current_app, g


def now_iso():
    """Fecha y hora local actual en formato ISO (sin microsegundos)."""
    return datetime.now().isoformat(timespec="seconds")


def get_db():
    """Devuelve la conexión de la petición actual (se abre una sola vez por petición)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea (o recrea) todas las tablas a partir de schema.sql."""
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


def reset_with_seed():
    from .seed import seed_database

    init_db()
    seed_database(get_db())


@click.command("init-db")
def init_db_command():
    """Borra la base de datos y la vuelve a crear con los datos de prueba."""
    reset_with_seed()
    click.echo("Base de datos inicializada con datos de prueba.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    # Primera ejecución: si no existe la base de datos, se crea con datos de prueba
    # para que la DEMO funcione sin pasos adicionales.
    if not app.config.get("TESTING") and not os.path.exists(app.config["DATABASE"]):
        with app.app_context():
            reset_with_seed()
