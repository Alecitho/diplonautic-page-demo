import pytest


@pytest.mark.parametrize("path", ["/", "/servicios", "/contacto"])
def test_paginas_publicas_accesibles_sin_sesion(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "Diplonautic" in response.get_data(as_text=True)


def test_formulario_contacto_es_solo_visual(client):
    response = client.post("/contacto", data={"nombre": "Ana", "email": "a@b.com", "mensaje": "Hola"},
                           follow_redirects=True)
    assert "no envía datos" in response.get_data(as_text=True)


def test_pagina_inexistente_devuelve_404(client):
    response = client.get("/no-existe")
    assert response.status_code == 404
    assert "Página no encontrada" in response.get_data(as_text=True)
