"""
Tests unitarios del servicio criptográfico.
No usan base de datos ni HTTP — prueban la lógica pura.
"""
import pytest
from app.services.crypto_service import (
    calcular_sha256,
    verificar_integridad,
    cifrar_aes,
    descifrar_aes,
    generar_par_claves_rsa,
    firmar_documento,
    verificar_firma,
)

DATA = b"documento de prueba para tests"


# ── SHA-256 ───────────────────────────────────────────────────────────────────

def test_sha256_es_determinista():
    assert calcular_sha256(DATA) == calcular_sha256(DATA)

def test_sha256_longitud_hex():
    assert len(calcular_sha256(DATA)) == 64

def test_sha256_diferente_si_dato_cambia():
    assert calcular_sha256(DATA) != calcular_sha256(b"dato diferente")

def test_integridad_ok():
    h = calcular_sha256(DATA)
    assert verificar_integridad(DATA, h) is True

def test_integridad_falla_si_dato_modificado():
    h = calcular_sha256(DATA)
    assert verificar_integridad(b"dato alterado", h) is False


# ── AES-256 ───────────────────────────────────────────────────────────────────

def test_aes_cifrado_no_es_igual_al_original():
    cifrado = cifrar_aes(DATA, "clave_test")
    assert cifrado != DATA

def test_aes_cifrar_descifrar_roundtrip():
    password = "mi_clave_segura_123"
    assert descifrar_aes(cifrar_aes(DATA, password), password) == DATA

def test_aes_salt_aleatorio_produce_ciphertext_distinto():
    # Mismo dato + misma clave → distinto ciphertext (salt aleatorio)
    c1 = cifrar_aes(DATA, "clave")
    c2 = cifrar_aes(DATA, "clave")
    assert c1 != c2

def test_aes_password_incorrecta_lanza_excepcion():
    cifrado = cifrar_aes(DATA, "clave_correcta")
    with pytest.raises(Exception):
        descifrar_aes(cifrado, "clave_incorrecta")


# ── RSA + Firma Digital ───────────────────────────────────────────────────────

def test_generar_par_claves_contiene_headers_pem():
    priv, pub = generar_par_claves_rsa()
    assert "BEGIN PRIVATE KEY" in priv
    assert "BEGIN PUBLIC KEY" in pub

def test_firma_valida():
    priv, pub = generar_par_claves_rsa()
    firma = firmar_documento(DATA, priv)
    assert verificar_firma(DATA, firma, pub) is True

def test_firma_invalida_si_documento_alterado():
    priv, pub = generar_par_claves_rsa()
    firma = firmar_documento(DATA, priv)
    assert verificar_firma(b"documento modificado", firma, pub) is False

def test_firma_invalida_con_clave_publica_distinta():
    priv, _ = generar_par_claves_rsa()
    _, pub_otra = generar_par_claves_rsa()
    firma = firmar_documento(DATA, priv)
    assert verificar_firma(DATA, firma, pub_otra) is False
