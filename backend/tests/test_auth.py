"""
Tests de integración para los endpoints de autenticación y usuarios.
"""


def test_registro_exitoso(client):
    resp = client.post("/usuarios/", json={
        "username": "wilmer",
        "email": "wilmer@example.com",
        "password": "password123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "wilmer"
    assert "password_hash" not in data


def test_registro_username_duplicado(client):
    payload = {"username": "dup", "email": "a@example.com", "password": "password123"}
    client.post("/usuarios/", json=payload)
    resp = client.post("/usuarios/", json={**payload, "email": "b@example.com"})
    assert resp.status_code == 400


def test_registro_email_duplicado(client):
    client.post("/usuarios/", json={"username": "u1", "email": "same@x.com", "password": "password123"})
    resp = client.post("/usuarios/", json={"username": "u2", "email": "same@x.com", "password": "password123"})
    assert resp.status_code == 400


def test_login_exitoso(client):
    client.post("/usuarios/", json={"username": "u", "email": "u@x.com", "password": "password123"})
    resp = client.post("/auth/login", json={"username": "u", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


def test_login_password_incorrecta(client):
    client.post("/usuarios/", json={"username": "u", "email": "u@x.com", "password": "password123"})
    resp = client.post("/auth/login", json={"username": "u", "password": "incorrecta"})
    assert resp.status_code == 401


def test_login_usuario_inexistente(client):
    resp = client.post("/auth/login", json={"username": "noexiste", "password": "cualquiera"})
    assert resp.status_code == 401


def test_endpoint_protegido_sin_token(client):
    resp = client.get("/certificados/")
    assert resp.status_code == 401


def test_endpoint_protegido_con_token_valido(usuario_autenticado):
    client, headers = usuario_autenticado
    resp = client.get("/certificados/", headers=headers)
    assert resp.status_code == 200


def test_password_corta_rechazada(client):
    resp = client.post("/usuarios/", json={
        "username": "u",
        "email": "u@x.com",
        "password": "corta",
    })
    assert resp.status_code == 422
