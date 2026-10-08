"""Configuración común de pytest: app con BD temporal y datos de prueba."""
import os
import re

import pytest

from app import create_app
from app.db import reset_with_seed
from app.seed import ADMIN_PASSWORD, EMPLEADO_PASSWORD

ADMIN = ("admin@diplonautic.com", ADMIN_PASSWORD)
EMPLEADO = ("ana.garcia@diplonautic.com", EMPLEADO_PASSWORD)
OTRO_EMPLEADO = ("carlos.ruiz@diplonautic.com", EMPLEADO_PASSWORD)
NO_VERIFICADO = ("lucia.martin@diplonautic.com", EMPLEADO_PASSWORD)
DESACTIVADO = ("pedro.sanz@diplonautic.com", EMPLEADO_PASSWORD)


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": os.path.join(tmp_path, "test.db"),
        "CSRF_ENABLED": False,
    })
    with app.app_context():
        reset_with_seed()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, credentials=EMPLEADO, follow=True):
        email, password = credentials
        return self._client.post("/acceso", data={"email": email, "password": password},
                                 follow_redirects=follow)

    def logout(self):
        return self._client.post("/salir", follow_redirects=True)


@pytest.fixture
def auth(client):
    return AuthActions(client)


def extract_verification_path(html):
    """Obtiene la ruta del enlace de verificación del correo simulado."""
    match = re.search(r'href="(?:https?://[^/"]+)?(/verificar/[^"]+)"', html)
    assert match, "No se encontró el enlace de verificación"
    return match.group(1)
