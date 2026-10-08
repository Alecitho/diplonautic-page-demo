from datetime import datetime, timedelta

from app.db import get_db
from conftest import (ADMIN, DESACTIVADO, EMPLEADO, NO_VERIFICADO, extract_verification_path)

NUEVO = {
    "name": "Nuria Prueba",
    "email": "nuria.prueba@diplonautic.com",
    "department": "Taller",
    "password": "Segura123",
    "password2": "Segura123",
}


def test_login_correcto_y_logout(client, auth):
    response = auth.login(EMPLEADO)
    assert "Hola, Ana" in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert session.get("user_id") is not None

    response = auth.logout()
    assert "Has cerrado sesión" in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_login_con_contrasena_incorrecta(auth):
    response = auth.login((EMPLEADO[0], "incorrecta1"))
    assert "Correo o contraseña incorrectos" in response.get_data(as_text=True)


def test_login_con_correo_inexistente_da_el_mismo_mensaje(auth):
    response = auth.login(("nadie@diplonautic.com", "Loquesea1"))
    assert "Correo o contraseña incorrectos" in response.get_data(as_text=True)


def test_cuenta_desactivada_no_puede_entrar(client, auth):
    response = auth.login(DESACTIVADO)
    assert "desactivada" in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_area_privada_exige_sesion(client):
    response = client.get("/area-privada")
    assert response.status_code == 302
    assert "/acceso" in response.headers["Location"]


def test_redireccion_next_solo_a_rutas_internas(auth, client):
    response = client.post("/acceso?next=//evil.example/x",
                           data={"email": EMPLEADO[0], "password": EMPLEADO[1]})
    assert response.headers["Location"] == "/area-privada"


def test_registro_crea_cuenta_no_verificada(client, app):
    response = client.post("/registro", data=NUEVO)
    assert "Verificar mi cuenta" in response.get_data(as_text=True)
    with app.app_context():
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (NUEVO["email"],)).fetchone()
        assert user["is_verified"] == 0
        assert user["role"] == "empleado"
        assert user["password_hash"] != NUEVO["password"]
        assert user["verification_token"] is not None


def test_registro_rechaza_dominio_externo(client):
    datos = dict(NUEVO, email="nuria@gmail.com")
    response = client.post("/registro", data=datos)
    assert "correo corporativo" in response.get_data(as_text=True)


def test_registro_rechaza_contrasena_debil(client):
    datos = dict(NUEVO, password="corta", password2="corta")
    response = client.post("/registro", data=datos)
    assert "al menos 8 caracteres" in response.get_data(as_text=True)


def test_registro_rechaza_correo_duplicado(client):
    datos = dict(NUEVO, email=EMPLEADO[0])
    response = client.post("/registro", data=datos)
    assert "Ya existe una cuenta" in response.get_data(as_text=True)


def test_flujo_completo_registro_verificacion_y_foro(client, auth):
    html = client.post("/registro", data=NUEVO).get_data(as_text=True)
    path = extract_verification_path(html)

    auth.login((NUEVO["email"], NUEVO["password"]))
    assert client.get("/foro/").status_code == 302  # sin verificar: fuera del foro

    response = client.get(path, follow_redirects=True)
    assert "Correo verificado" in response.get_data(as_text=True)
    assert client.get("/foro/").status_code == 200

    # El enlace es de un solo uso
    response = client.get(path, follow_redirects=True)
    assert "no es válido" in response.get_data(as_text=True)


def test_enlace_de_verificacion_caducado(client, app):
    html = client.post("/registro", data=NUEVO).get_data(as_text=True)
    path = extract_verification_path(html)
    with app.app_context():
        antiguo = (datetime.now() - timedelta(hours=49)).isoformat(timespec="seconds")
        get_db().execute("UPDATE users SET verification_sent_at = ? WHERE email = ?",
                         (antiguo, NUEVO["email"]))
        get_db().commit()
    response = client.get(path, follow_redirects=True)
    assert "ha caducado" in response.get_data(as_text=True)


def test_no_verificado_puede_reenviar_el_correo(client, auth):
    auth.login(NO_VERIFICADO)
    response = client.post("/verificacion/reenviar")
    path = extract_verification_path(response.get_data(as_text=True))
    client.get(path)
    assert client.get("/foro/").status_code == 200


def test_usuario_no_verificado_ve_aviso_en_area_privada(auth):
    response = auth.login(NO_VERIFICADO)
    assert "pendiente de verificación" in response.get_data(as_text=True)


def test_sesion_se_cierra_si_la_cuenta_se_desactiva(client, auth, app):
    auth.login(EMPLEADO)
    with app.app_context():
        get_db().execute("UPDATE users SET is_active = 0 WHERE email = ?", (EMPLEADO[0],))
        get_db().commit()
    response = client.get("/area-privada")
    assert response.status_code == 302


def test_admin_entra_con_su_rol(auth):
    response = auth.login(ADMIN)
    assert "Gestión de usuarios" in response.get_data(as_text=True)


def test_boton_de_verificacion_usa_ruta_relativa(client):
    html = client.post("/registro", data=NUEVO).get_data(as_text=True)
    assert 'href="/verificar/' in html


def test_enlace_completo_usa_el_dominio_del_proxy(monkeypatch, tmp_path):
    """En Codespaces (TRUST_PROXY=1) el enlace mostrado apunta al dominio público."""
    import os

    from app import create_app
    from app.db import reset_with_seed

    monkeypatch.setenv("TRUST_PROXY", "1")
    app = create_app({"TESTING": True, "CSRF_ENABLED": False,
                      "DATABASE": os.path.join(tmp_path, "proxy.db")})
    with app.app_context():
        reset_with_seed()
    html = app.test_client().post("/registro", data=NUEVO, headers={
        "X-Forwarded-Host": "demo-5000.app.github.dev",
        "X-Forwarded-Proto": "https",
    }).get_data(as_text=True)
    assert "https://demo-5000.app.github.dev/verificar/" in html
