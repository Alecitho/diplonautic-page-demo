from app.db import get_db
from conftest import ADMIN, EMPLEADO, NO_VERIFICADO, OTRO_EMPLEADO

HILO = {"title": "Bomba de achique con ruido", "category": "incidencia",
        "body": "La bomba del pantoque hace un ruido metálico al arrancar."}


def create_thread(client, data=HILO):
    response = client.post("/foro/nuevo", data=data)
    assert response.status_code == 302
    return int(response.headers["Location"].rstrip("/").split("/")[-1])


def test_anonimo_no_puede_leer_ni_escribir(client):
    for response in (client.get("/foro/"), client.get("/foro/1"),
                     client.post("/foro/nuevo", data=HILO),
                     client.post("/foro/1/responder", data={"body": "Hola a todos"})):
        assert response.status_code == 302
        assert "/acceso" in response.headers["Location"]


def test_no_verificado_no_puede_acceder(client, auth):
    auth.login(NO_VERIFICADO)
    response = client.get("/foro/", follow_redirects=True)
    assert "no está verificada" in response.get_data(as_text=True)
    assert client.post("/foro/nuevo", data=HILO).headers["Location"] == "/area-privada"


def test_listado_muestra_titulo_autor_y_fecha(client, auth):
    auth.login(EMPLEADO)
    html = client.get("/foro/").get_data(as_text=True)
    assert "Bienvenidos al foro interno de Diplonautic" in html
    assert "Laura Méndez" in html
    assert "/20" in html  # fecha en formato dd/mm/aaaa


def test_hilos_fijados_aparecen_primero(client, auth):
    auth.login(EMPLEADO)
    html = client.get("/foro/").get_data(as_text=True)
    assert html.index("Nuevo procedimiento de recarga") < html.index("Compresor Danfoss")


def test_crear_hilo_y_responder(client, auth):
    auth.login(EMPLEADO)
    thread_id = create_thread(client)
    html = client.get(f"/foro/{thread_id}").get_data(as_text=True)
    assert HILO["title"] in html and "Ana García" in html

    client.post(f"/foro/{thread_id}/responder", data={"body": "Revisa el rodete, suele ser eso."})
    html = client.get(f"/foro/{thread_id}").get_data(as_text=True)
    assert "Revisa el rodete" in html
    assert "1 respuesta" in html


def test_validacion_de_hilo(client, auth):
    auth.login(EMPLEADO)
    response = client.post("/foro/nuevo", data=dict(HILO, title="Hey"))
    assert "El título debe tener" in response.get_data(as_text=True)
    response = client.post("/foro/nuevo", data=dict(HILO, category="spam"))
    assert "categoría válida" in response.get_data(as_text=True)


def test_hilo_cerrado_no_admite_respuestas(client, auth, app):
    auth.login(EMPLEADO)
    with app.app_context():
        closed = get_db().execute("SELECT id FROM threads WHERE is_closed = 1").fetchone()["id"]
        before = get_db().execute("SELECT COUNT(*) FROM posts WHERE thread_id = ?", (closed,)).fetchone()[0]
    client.post(f"/foro/{closed}/responder", data={"body": "Intento responder igualmente"})
    with app.app_context():
        after = get_db().execute("SELECT COUNT(*) FROM posts WHERE thread_id = ?", (closed,)).fetchone()[0]
    assert before == after


def test_busqueda_y_filtro_por_categoria(client, auth):
    auth.login(EMPLEADO)
    html = client.get("/foro/?q=Danfoss").get_data(as_text=True)
    assert "Compresor Danfoss" in html and "Plotter Garmin" not in html
    html = client.get("/foro/?categoria=duda").get_data(as_text=True)
    assert "cargador de puerto" in html and "Compresor Danfoss" not in html


def test_contenido_html_se_escapa(client, auth):
    auth.login(EMPLEADO)
    thread_id = create_thread(client, dict(HILO, body="<script>alert('xss')</script> texto"))
    html = client.get(f"/foro/{thread_id}").get_data(as_text=True)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_empleado_no_modera_contenido_ajeno(client, auth):
    auth.login(EMPLEADO)
    thread_id = create_thread(client)
    auth.logout()
    auth.login(OTRO_EMPLEADO)
    assert client.post(f"/foro/{thread_id}/eliminar").status_code == 403
    assert client.post(f"/foro/{thread_id}/cerrar").status_code == 403
    assert client.post(f"/foro/{thread_id}/fijar").status_code == 403


def test_autor_puede_cerrar_y_eliminar_su_hilo(client, auth):
    auth.login(EMPLEADO)
    thread_id = create_thread(client)
    client.post(f"/foro/{thread_id}/cerrar")
    assert "Cerrado" in client.get(f"/foro/{thread_id}").get_data(as_text=True)
    client.post(f"/foro/{thread_id}/eliminar")
    assert client.get(f"/foro/{thread_id}").status_code == 404


def test_admin_fija_y_elimina_cualquier_hilo(client, auth, app):
    auth.login(EMPLEADO)
    thread_id = create_thread(client)
    client.post(f"/foro/{thread_id}/responder", data={"body": "Respuesta que se borrará"})
    auth.logout()

    auth.login(ADMIN)
    client.post(f"/foro/{thread_id}/fijar")
    with app.app_context():
        assert get_db().execute("SELECT is_pinned FROM threads WHERE id = ?",
                                (thread_id,)).fetchone()[0] == 1
    client.post(f"/foro/{thread_id}/eliminar")
    with app.app_context():
        # Las respuestas se borran en cascada con el hilo
        assert get_db().execute("SELECT COUNT(*) FROM posts WHERE thread_id = ?",
                                (thread_id,)).fetchone()[0] == 0
