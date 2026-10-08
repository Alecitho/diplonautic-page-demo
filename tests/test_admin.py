from app.db import get_db
from conftest import ADMIN, EMPLEADO, NO_VERIFICADO


def user_by_email(app, email):
    with app.app_context():
        return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def test_empleado_no_accede_al_panel(client, auth):
    auth.login(EMPLEADO)
    assert client.get("/admin/usuarios").status_code == 403


def test_anonimo_es_enviado_al_login(client):
    response = client.get("/admin/usuarios")
    assert response.status_code == 302
    assert "/acceso" in response.headers["Location"]


def test_listado_y_filtros(client, auth):
    auth.login(ADMIN)
    html = client.get("/admin/usuarios").get_data(as_text=True)
    assert "lucia.martin@diplonautic.com" in html

    html = client.get("/admin/usuarios?estado=no-verificados").get_data(as_text=True)
    assert "lucia.martin@diplonautic.com" in html
    assert "ana.garcia@diplonautic.com" not in html

    html = client.get("/admin/usuarios?estado=desactivados").get_data(as_text=True)
    assert "pedro.sanz@diplonautic.com" in html
    assert "ana.garcia@diplonautic.com" not in html


def test_admin_verifica_usuario(client, auth, app):
    auth.login(ADMIN)
    lucia = user_by_email(app, NO_VERIFICADO[0])
    client.post(f"/admin/usuarios/{lucia['id']}/verificar")
    assert user_by_email(app, NO_VERIFICADO[0])["is_verified"] == 1


def test_admin_crea_usuario_verificado(client, auth, app):
    auth.login(ADMIN)
    client.post("/admin/usuarios/nuevo", data={
        "name": "Raúl Nuevo", "email": "raul.nuevo@diplonautic.com", "department": "Taller",
        "role": "empleado", "password": "Temporal123", "verified": "on",
    })
    raul = user_by_email(app, "raul.nuevo@diplonautic.com")
    assert raul is not None and raul["is_verified"] == 1


def test_admin_cambia_rol_y_desactiva(client, auth, app):
    auth.login(ADMIN)
    ana = user_by_email(app, EMPLEADO[0])
    client.post(f"/admin/usuarios/{ana['id']}/rol", data={"role": "admin"})
    assert user_by_email(app, EMPLEADO[0])["role"] == "admin"
    client.post(f"/admin/usuarios/{ana['id']}/activo")
    assert user_by_email(app, EMPLEADO[0])["is_active"] == 0


def test_admin_no_puede_desactivarse_a_si_mismo(client, auth, app):
    auth.login(ADMIN)
    admin = user_by_email(app, ADMIN[0])
    response = client.post(f"/admin/usuarios/{admin['id']}/activo", follow_redirects=True)
    assert "No puedes desactivar tu propia cuenta" in response.get_data(as_text=True)
    assert user_by_email(app, ADMIN[0])["is_active"] == 1


def test_rol_invalido_devuelve_400(client, auth, app):
    auth.login(ADMIN)
    ana = user_by_email(app, EMPLEADO[0])
    assert client.post(f"/admin/usuarios/{ana['id']}/rol", data={"role": "root"}).status_code == 400
