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
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Documento, Certificado, PerfilProfesional, Usuario
from app.services import crypto_service, ca_service

router = APIRouter(prefix="/verificar", tags=["Verificación Pública"])


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

    with open(doc.ruta_archivo, "rb") as f:
        contenido_actual = f.read()

    firma_valida = crypto_service.verificar_firma(contenido_actual, doc.firma_digital, cert.clave_publica_pem)
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
