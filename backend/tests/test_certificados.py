"""
Tests de integración para el ciclo de vida de certificados digitales.
"""


def test_emitir_certificado(usuario_autenticado):
    client, headers = usuario_autenticado
    resp = client.post("/certificados/emitir", headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "clave_privada_pem" in data
    assert "BEGIN PRIVATE KEY" in data["clave_privada_pem"]
    assert data["estado"] == "vigente"
    assert "aviso" in data


def test_clave_privada_no_aparece_en_listado(usuario_autenticado):
    client, headers = usuario_autenticado
    client.post("/certificados/emitir", headers=headers)
    resp = client.get("/certificados/", headers=headers)
    assert resp.status_code == 200
    for cert in resp.json():
        assert "clave_privada_pem" not in cert


def test_listar_certificados_solo_propios(usuario_autenticado, client):
    c, headers = usuario_autenticado
    c.post("/certificados/emitir", headers=headers)

    # Segundo usuario
    client.post("/usuarios/", json={"username": "otro", "email": "otro@x.com", "password": "password123"})
    token2 = client.post("/auth/login", json={"username": "otro", "password": "password123"}).json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    client.post("/certificados/emitir", headers=headers2)

    resp1 = c.get("/certificados/", headers=headers)
    resp2 = client.get("/certificados/", headers=headers2)
    assert len(resp1.json()) == 1
    assert len(resp2.json()) == 1


def test_validar_certificado_vigente(usuario_autenticado):
    client, headers = usuario_autenticado
    cert_id = client.post("/certificados/emitir", headers=headers).json()["id"]
    resp = client.get(f"/certificados/{cert_id}/validar", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["valido"] is True


def test_revocar_certificado(usuario_autenticado):
    client, headers = usuario_autenticado
    cert_id = client.post("/certificados/emitir", headers=headers).json()["id"]
    resp = client.delete(f"/certificados/{cert_id}/revocar", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["estado"] == "revocado"


def test_certificado_revocado_no_es_valido(usuario_autenticado):
    client, headers = usuario_autenticado
    cert_id = client.post("/certificados/emitir", headers=headers).json()["id"]
    client.delete(f"/certificados/{cert_id}/revocar", headers=headers)
    resp = client.get(f"/certificados/{cert_id}/validar", headers=headers)
    assert resp.json()["valido"] is False


def test_descargar_certificado_pem(usuario_autenticado):
    client, headers = usuario_autenticado
    cert_id = client.post("/certificados/emitir", headers=headers).json()["id"]
    resp = client.get(f"/certificados/{cert_id}/descargar", headers=headers)
    assert resp.status_code == 200
    assert b"BEGIN CERTIFICATE" in resp.content
