import os
import re

import pytest

from app import create_app
from app.db import reset_with_seed
from conftest import EMPLEADO


@pytest.fixture
def csrf_client(tmp_path):
    """Cliente con la protección CSRF activa, como en producción."""
    app = create_app({"TESTING": True, "DATABASE": os.path.join(tmp_path, "csrf.db")})
    with app.app_context():
        reset_with_seed()
    return app.test_client()


def test_post_sin_token_csrf_es_rechazado(csrf_client):
    response = csrf_client.post("/acceso", data={"email": EMPLEADO[0], "password": EMPLEADO[1]})
    assert response.status_code == 400


def test_post_con_token_csrf_es_aceptado(csrf_client):
    html = csrf_client.get("/acceso").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    response = csrf_client.post("/acceso", data={
        "email": EMPLEADO[0], "password": EMPLEADO[1], "csrf_token": token,
    })
    assert response.status_code == 302


def test_cookies_de_sesion_seguras(csrf_client):
    app = csrf_client.application
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_contrasenas_guardadas_con_hash(csrf_client):
    from app.db import get_db
    with csrf_client.application.app_context():
        hashes = [r[0] for r in get_db().execute("SELECT password_hash FROM users")]
    assert all(h.startswith(("scrypt:", "pbkdf2:")) for h in hashes)
