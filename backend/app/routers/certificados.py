"""
Gestión de Certificados (requisito obligatorio: Emitir, Consultar, Revocar).
Aquí se conecta el servicio de criptografía RSA con la CA simulada.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import Usuario, Certificado, LogAuditoria
from app.schemas.schemas import CertificadoOut, CertificadoEmitidoOut, EmitirCertificadoRequest
from app.services import crypto_service, ca_service

router = APIRouter(prefix="/certificados", tags=["Certificados"])

_CERT_NOT_FOUND = "Certificado no encontrado"


@router.post("/emitir", response_model=CertificadoEmitidoOut, status_code=status.HTTP_201_CREATED)
def emitir_certificado(
    payload: EmitirCertificadoRequest | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Emitir un certificado digital para el usuario autenticado:
    1. Genera un par de claves RSA para el usuario.
    2. La CA simulada firma un certificado X.509 con la clave pública.
    3. Se guarda el certificado (solo la clave PÚBLICA queda en el servidor).

    DECISIÓN DE DISEÑO (documentar en el artículo técnico):
    La clave PRIVADA se devuelve UNA SOLA VEZ en esta respuesta y nunca se
    persiste en la base de datos ni en disco del servidor. Es responsabilidad
    del usuario guardarla de forma segura; deberá volver a enviarla cada vez
    que quiera firmar un documento (igual que un certificado .p12 real que
    el usuario protege con su propia contraseña).
    """
    nombre = payload.nombre if payload else None

    passphrase = payload.passphrase if payload else None
    clave_privada_pem, clave_publica_pem = crypto_service.generar_par_claves_rsa(passphrase=passphrase)

    numero_serie, certificado_pem, expiracion = ca_service.emitir_certificado(
        usuario_id=current_user.id,
        username=current_user.username,
        clave_publica_pem=clave_publica_pem,
    )

    nuevo_cert = Certificado(
        propietario_id=current_user.id,
        nombre=nombre,
        numero_serie=numero_serie,
        clave_publica_pem=clave_publica_pem,
        certificado_pem=certificado_pem,
        fecha_expiracion=expiracion,
    )
    db.add(nuevo_cert)
    db.commit()
    db.refresh(nuevo_cert)

    db.add(LogAuditoria(
        usuario_id=current_user.id,
        evento="CERTIFICADO_EMITIDO",
        detalle=f"Certificado serie={numero_serie} emitido",
    ))
    db.commit()

    return CertificadoEmitidoOut(
        id=nuevo_cert.id,
        propietario_id=nuevo_cert.propietario_id,
        nombre=nuevo_cert.nombre,
        numero_serie=nuevo_cert.numero_serie,
        emisor=nuevo_cert.emisor,
        fecha_emision=nuevo_cert.fecha_emision,
        fecha_expiracion=nuevo_cert.fecha_expiracion,
        estado=nuevo_cert.estado,
        clave_privada_pem=clave_privada_pem,
        aviso="GUARDA esta clave privada ahora. No se mostrará de nuevo ni se almacena en el servidor.",
    )


@router.get("/{certificado_id}/descargar")
def descargar_certificado(
    certificado_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Descarga el certificado público X.509 (.pem) como archivo.
    NOTA: esto NO incluye la clave privada — esa solo se entrega una vez,
    en el momento de /emitir, por seguridad.
    """
    cert = db.query(Certificado).filter(
        Certificado.id == certificado_id, Certificado.propietario_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail=_CERT_NOT_FOUND)

    nombre_archivo = f"certificado_{cert.nombre or cert.numero_serie[:10]}.pem"
    return Response(
        content=cert.certificado_pem,
        media_type="application/x-pem-file",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/", response_model=List[CertificadoOut])
def listar_certificados(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Consultar todos los certificados del usuario autenticado."""
    return db.query(Certificado).filter(Certificado.propietario_id == current_user.id).all()


@router.get("/{certificado_id}", response_model=CertificadoOut)
def obtener_certificado(
    certificado_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cert = db.query(Certificado).filter(Certificado.id == certificado_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail=_CERT_NOT_FOUND)
    return cert


@router.get("/{certificado_id}/validar")
def validar_certificado(
    certificado_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Valida un certificado: firma de la CA, vigencia y estado (revocado/expirado)."""
    cert = db.query(Certificado).filter(Certificado.id == certificado_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail=_CERT_NOT_FOUND)

    if cert.estado == "revocado":
        return {"valido": False, "estado": "revocado", "motivo": "Certificado revocado manualmente"}

    resultado = ca_service.validar_certificado(cert.certificado_pem)
    return resultado


@router.delete("/{certificado_id}/revocar", response_model=CertificadoOut)
def revocar_certificado(
    certificado_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Revocar un certificado (no se borra, se marca como revocado para trazabilidad)."""
    cert = db.query(Certificado).filter(Certificado.id == certificado_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail=_CERT_NOT_FOUND)

    cert.estado = "revocado"
    db.commit()
    db.refresh(cert)

    db.add(LogAuditoria(
        usuario_id=current_user.id,
        evento="CERTIFICADO_REVOCADO",
        detalle=f"Certificado serie={cert.numero_serie} revocado",
    ))
    db.commit()

    return cert
