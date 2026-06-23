"""
Autoridad Certificadora (CA) Simulada.

Requisito obligatorio del proyecto: generación, firma y validación básica
de confianza de certificados digitales.

Usamos certificados X.509 reales (vía `cryptography.x509`), pero firmados
por una CA propia generada para este proyecto académico, no por una CA
pública real. Por eso se llama "simulada".
"""
import datetime
import uuid
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# --- Clave de la CA (en un proyecto real esto se genera UNA vez y se guarda
# de forma segura; aquí se genera al iniciar el módulo por simplicidad) ---
_ca_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

_ca_name = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "EC"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ESPE-ProyectoFinal-CA-Simulada"),
    x509.NameAttribute(NameOID.COMMON_NAME, "CA Simulada Seguridad del Software"),
])


def emitir_certificado(usuario_id: int, username: str, clave_publica_pem: str,
                        dias_validez: int = 365):
    """
    La CA simulada firma un certificado X.509 para la clave pública del usuario.
    Retorna (numero_serie, certificado_pem, fecha_expiracion).
    """
    clave_publica = serialization.load_pem_public_key(clave_publica_pem.encode())

    sujeto = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, username),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Usuarios-Plataforma"),
    ])

    numero_serie = uuid.uuid4().int >> 64  # entero grande único
    ahora = datetime.datetime.now(datetime.timezone.utc)
    expiracion = ahora + datetime.timedelta(days=dias_validez)

    certificado = (
        x509.CertificateBuilder()
        .subject_name(sujeto)
        .issuer_name(_ca_name)
        .public_key(clave_publica)
        .serial_number(numero_serie)
        .not_valid_before(ahora)
        .not_valid_after(expiracion)
        .sign(_ca_private_key, hashes.SHA256())
    )

    certificado_pem = certificado.public_bytes(serialization.Encoding.PEM).decode()

    return str(numero_serie), certificado_pem, expiracion


def validar_certificado(certificado_pem: str) -> dict:
    """
    Valida un certificado: verifica firma de la CA, vigencia y devuelve estado.
    Estados posibles: vigente, expirado, invalido.
    """
    try:
        cert = x509.load_pem_x509_certificate(certificado_pem.encode())
    except Exception:
        return {"valido": False, "estado": "invalido", "motivo": "PEM mal formado"}

    # Verificar que la firma fue hecha por nuestra CA
    try:
        _ca_private_key.public_key().verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            __import__("cryptography.hazmat.primitives.asymmetric.padding",
                        fromlist=["PKCS1v15"]).PKCS1v15(),
            cert.signature_hash_algorithm,
        )
    except Exception:
        return {"valido": False, "estado": "invalido", "motivo": "Firma de CA no válida"}

    ahora = datetime.datetime.now(datetime.timezone.utc)
    if ahora > cert.not_valid_after_utc:
        return {"valido": False, "estado": "expirado", "motivo": "Certificado expirado"}
    if ahora < cert.not_valid_before_utc:
        return {"valido": False, "estado": "invalido", "motivo": "Certificado aún no vigente"}

    return {"valido": True, "estado": "vigente", "motivo": "OK"}
