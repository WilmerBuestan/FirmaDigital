"""
Verificación Pública de Documentos.

Este es el endpoint al que apunta el código QR estampado en el PDF firmado.
NO requiere autenticación: cualquier persona (un profesor, un cliente, un
funcionario) que escanee el QR debe poder confirmar la autenticidad del
documento sin tener cuenta en la plataforma.

Solo expone información NO sensible: nombre del firmante (de su perfil
profesional), fecha de firma, estado del certificado y resultado de la
verificación de integridad. Nunca expone claves, hashes completos sin
contexto, ni datos del archivo en sí.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Documento, Certificado, PerfilProfesional, Usuario
from app.services import crypto_service, ca_service

router = APIRouter(prefix="/verificar", tags=["Verificación Pública"])

_MAX_VERIFY_SIZE = 10 * 1024 * 1024  # 10 MB


def _info_firmante(firmante: Usuario, perfil: PerfilProfesional | None) -> dict:
    return {
        "username": firmante.username,
        "nombre_completo": perfil.nombre_completo if perfil else None,
        "cedula": perfil.cedula if perfil else None,
        "titulo_profesional": perfil.titulo_profesional if perfil else None,
        "trabajo": perfil.trabajo if perfil else None,
        "ubicacion": perfil.ubicacion if perfil else None,
    }


@router.post("/por-archivo")
async def verificar_por_archivo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Sube cualquier archivo y la plataforma busca si fue registrado y/o firmado.
    Acepta TANTO el PDF original como el PDF firmado (con sello QR):
      - Original  → busca por hash_sha256
      - Firmado   → busca por hash_firmado (guardado al estampar el sello)
    No requiere autenticación.
    """
    contenido = await file.read()
    if len(contenido) > _MAX_VERIFY_SIZE:
        raise HTTPException(status_code=413, detail="El archivo no puede superar 10 MB")

    hash_archivo = crypto_service.calcular_sha256(contenido)

    # Buscar primero por el hash del original, luego por el del PDF firmado
    doc = db.query(Documento).filter(Documento.hash_sha256 == hash_archivo).first()
    es_pdf_firmado = False
    if not doc:
        doc = db.query(Documento).filter(Documento.hash_firmado == hash_archivo).first()
        es_pdf_firmado = doc is not None

    if not doc:
        return {
            "encontrado": False,
            "mensaje": (
                "Este archivo no está registrado en la plataforma. "
                "Sube el PDF original o el PDF firmado descargado desde la plataforma."
            ),
        }

    if not doc.firma_digital or not doc.certificado_id:
        return {
            "encontrado": True,
            "firmado": False,
            "documento": {"nombre_archivo": doc.nombre_archivo, "subido_en": doc.subido_en.isoformat()},
            "mensaje": "El archivo está registrado pero todavía no tiene firma digital.",
        }

    cert = db.query(Certificado).filter(Certificado.id == doc.certificado_id).first()
    firmante = db.query(Usuario).filter(Usuario.id == doc.propietario_id).first()
    perfil = db.query(PerfilProfesional).filter(PerfilProfesional.usuario_id == doc.propietario_id).first()

    # Si el usuario subió el PDF firmado (con QR), verificar usando el hash del ORIGINAL
    # guardado en BD, porque la firma RSA fue calculada sobre el contenido original.
    if es_pdf_firmado:
        firma_valida = crypto_service.verificar_firma_por_hash(
            doc.hash_sha256, doc.firma_digital, cert.clave_publica_pem
        )
    else:
        firma_valida = crypto_service.verificar_firma(contenido, doc.firma_digital, cert.clave_publica_pem)

    estado_cert = ca_service.validar_certificado(cert.certificado_pem)
    autentico = firma_valida and estado_cert["valido"] and cert.estado == "vigente"

    return {
        "encontrado": True,
        "firmado": True,
        "autentico": autentico,
        "documento": {
            "nombre_archivo": doc.nombre_archivo,
            "hash_sha256": doc.hash_sha256,
            "codigo_verificacion": doc.codigo_verificacion,
            "subido_en": doc.subido_en.isoformat(),
        },
        "firmante": _info_firmante(firmante, perfil),
        "certificado": {
            "numero_serie": cert.numero_serie,
            "emisor": cert.emisor,
            "estado": cert.estado,
            "fecha_expiracion": cert.fecha_expiracion.isoformat(),
        },
        "verificacion": {
            "firma_valida": firma_valida,
            "certificado_valido": estado_cert["valido"],
            "mensaje": (
                "Documento auténtico: firma válida y certificado vigente."
                if autentico else
                "Atención: el documento no pudo verificarse como auténtico. "
                "Puede haber sido alterado, o el certificado fue revocado/expiró."
            ),
        },
    }


@router.get("/{codigo_verificacion}")
def verificar_documento_publico(codigo_verificacion: str, db: Session = Depends(get_db)):
    """
    Endpoint público (sin auth) consultado al escanear el QR de un documento.
    Devuelve si el documento es auténtico y quién lo firmó.
    """
    doc = db.query(Documento).filter(Documento.codigo_verificacion == codigo_verificacion).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Código de verificación no encontrado")

    cert = db.query(Certificado).filter(Certificado.id == doc.certificado_id).first()
    firmante = db.query(Usuario).filter(Usuario.id == doc.propietario_id).first()
    perfil = db.query(PerfilProfesional).filter(PerfilProfesional.usuario_id == doc.propietario_id).first()

    # Verificar usando el hash guardado en BD (no leer del disco, que es efímero en Render)
    firma_valida = crypto_service.verificar_firma_por_hash(
        doc.hash_sha256, doc.firma_digital, cert.clave_publica_pem
    )
    estado_certificado = ca_service.validar_certificado(cert.certificado_pem)

    autentico = firma_valida and estado_certificado["valido"] and cert.estado == "vigente"

    return {
        "autentico": autentico,
        "documento": {
            "nombre_archivo": doc.nombre_archivo,
            "fecha_firma": doc.subido_en.isoformat(),
            "codigo_verificacion": codigo_verificacion,
        },
        "firmante": {
            "nombre_completo": perfil.nombre_completo if perfil else firmante.username,
            "cedula": perfil.cedula if perfil else None,
            "trabajo": perfil.trabajo if perfil else None,
            "titulo_profesional": perfil.titulo_profesional if perfil else None,
            "nivel_academico": perfil.nivel_academico if perfil else None,
            "ubicacion": perfil.ubicacion if perfil else None,
        },
        "certificado": {
            "numero_serie": cert.numero_serie,
            "emisor": cert.emisor,
            "estado": cert.estado,
            "fecha_expiracion": cert.fecha_expiracion.isoformat(),
        },
        "verificacion": {
            "firma_valida": firma_valida,
            "certificado_valido": estado_certificado["valido"],
            "mensaje": (
                "Documento auténtico: la firma digital es válida y el certificado está vigente."
                if autentico else
                "Atención: este documento no pudo ser verificado como auténtico. "
                "Puede haber sido alterado, o su certificado fue revocado/expiró."
            ),
        },
    }
