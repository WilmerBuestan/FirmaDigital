"""
Servicio Criptográfico Central.

Cubre los 4 temas criptográficos obligatorios del proyecto:
1. Hash (SHA-256)            -> integridad de archivos
2. Criptografía Simétrica (AES) -> cifrado/descifrado de archivos
3. Criptografía Asimétrica (RSA) -> firma digital
4. Firma Digital              -> firmar y verificar documentos

Usamos la librería `cryptography`, estándar de la industria en Python.
"""
import hashlib
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


# =========================================================
# 1. HASH — SHA-256 (integridad)
# =========================================================
def calcular_sha256(data: bytes) -> str:
    """
    Calcula el hash SHA-256 de un contenido binario.
    Mismo archivo -> mismo hash. Archivo alterado -> hash diferente.
    """
    return hashlib.sha256(data).hexdigest()


def verificar_integridad(data: bytes, hash_esperado: str) -> bool:
    """Compara el hash actual de un archivo contra el hash guardado."""
    return calcular_sha256(data) == hash_esperado


# =========================================================
# 2. CRIPTOGRAFÍA SIMÉTRICA — AES (cifrado de archivos)
# =========================================================
def _derivar_clave_aes(password: str, salt: bytes) -> bytes:
    """Deriva una clave AES-256 a partir de una contraseña usando PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # AES-256
        salt=salt,
        iterations=200_000,
    )
    return kdf.derive(password.encode())


def cifrar_aes(data: bytes, password: str) -> bytes:
    """
    Cifra datos con AES-256 en modo CBC.
    El resultado incluye: salt (16) + iv (16) + ciphertext, todo concatenado,
    para que el descifrado pueda reconstruir todo con solo la contraseña.
    """
    salt = os.urandom(16)
    iv = os.urandom(16)
    key = _derivar_clave_aes(password, salt)

    # padding PKCS7 manual (bloques de 16 bytes)
    pad_len = 16 - (len(data) % 16)
    data_padded = data + bytes([pad_len]) * pad_len

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data_padded) + encryptor.finalize()

    return salt + iv + ciphertext


def descifrar_aes(data_cifrada: bytes, password: str) -> bytes:
    """Descifra datos cifrados con cifrar_aes(). Lanza ValueError si falla."""
    salt = data_cifrada[:16]
    iv = data_cifrada[16:32]
    ciphertext = data_cifrada[32:]
    key = _derivar_clave_aes(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    data_padded = decryptor.update(ciphertext) + decryptor.finalize()

    pad_len = data_padded[-1]
    return data_padded[:-pad_len]


# =========================================================
# 3. CRIPTOGRAFÍA ASIMÉTRICA — RSA (firma digital / intercambio de claves)
# =========================================================
def generar_par_claves_rsa(passphrase: str | None = None) -> tuple[str, str]:
    """
    Genera un par de claves RSA-2048.
    Si se provee passphrase, la clave privada queda cifrada con AES-256-CBC
    (BestAvailableEncryption) y solo puede usarse conociendo esa passphrase.
    Retorna (clave_privada_pem, clave_publica_pem).
    """
    clave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    clave_publica = clave_privada.public_key()

    encryption = (
        serialization.BestAvailableEncryption(passphrase.encode())
        if passphrase
        else serialization.NoEncryption()
    )

    privada_pem = clave_privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    ).decode()

    publica_pem = clave_publica.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return privada_pem, publica_pem


def _cargar_clave_privada(pem: str, passphrase: str | None = None):
    password = passphrase.encode() if passphrase else None
    try:
        return serialization.load_pem_private_key(pem.encode(), password=password)
    except (TypeError, ValueError) as e:
        raise ValueError(
            "No se pudo descifrar la clave privada. "
            "Verifica que la passphrase sea correcta."
        ) from e


def _cargar_clave_publica(pem: str):
    return serialization.load_pem_public_key(pem.encode())


# =========================================================
# 4. FIRMA DIGITAL (usa RSA + SHA-256)
# =========================================================
def firmar_documento(data: bytes, clave_privada_pem: str, passphrase: str | None = None) -> str:
    """
    Firma digitalmente un documento.
    Proceso: hash SHA-256 del documento -> firma RSA del hash -> base64.
    Si la clave privada está cifrada, se requiere la passphrase.
    """
    clave_privada = _cargar_clave_privada(clave_privada_pem, passphrase)
    firma = clave_privada.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(firma).decode()


def verificar_firma(data: bytes, firma_b64: str, clave_publica_pem: str) -> bool:
    """
    Verifica que una firma digital sea válida para un documento dado.
    Si el documento fue modificado tras la firma, esto retorna False.
    """
    clave_publica = _cargar_clave_publica(clave_publica_pem)
    firma = base64.b64decode(firma_b64)
    try:
        clave_publica.verify(
            firma,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
