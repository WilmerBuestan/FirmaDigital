"""
Gestión de Documentos (requisito obligatorio: Subir, Firmar, Consultar, Eliminar).
Incluye verificación de integridad (hash), verificación de firma, y el flujo
de firma VISUAL sobre PDF con sello + código QR de verificación pública.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import FRONTEND_URL
from app.models.models import Usuario, Documento, Certificado, PerfilProfesional, LogAuditoria
from app.schemas.schemas import DocumentoOut, DocumentoInfoPdf
from app.services import crypto_service, pdf_service

router = APIRouter(prefix="/documentos", tags=["Documentos"])

UPLOAD_DIR = "uploads"
FIRMADOS_DIR = "firmados"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FIRMADOS_DIR, exist_ok=True)


def _a_documento_out(doc: Documento) -> dict:
    """Construye la respuesta incluyendo el campo calculado 'firmado'."""
    return {
        "id": doc.id,
        "propietario_id": doc.propietario_id,
        "nombre_archivo": doc.nombre_archivo,
        "hash_sha256": doc.hash_sha256,
        "cifrado": doc.cifrado,
        "firmado": bool(doc.firma_digital),
        "codigo_verificacion": doc.codigo_verificacion,
        "subido_en": doc.subido_en,
    }


@router.post("/subir", response_model=DocumentoOut, status_code=status.HTTP_201_CREATED)
async def subir_documento(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Sube un documento, calcula su hash SHA-256 y lo guarda en disco."""
    contenido = await file.read()

    if len(contenido) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo no puede superar 10 MB")

    # Path traversal fix: Path().name extrae solo el nombre, descarta cualquier
    # componente de directorio que pueda venir en file.filename (ej: "../../etc/passwd")
    safe_name = Path(file.filename).name
    hash_archivo = crypto_service.calcular_sha256(contenido)

    ruta = os.path.join(UPLOAD_DIR, f"{current_user.id}_{uuid.uuid4().hex[:8]}_{safe_name}")
    with open(ruta, "wb") as f:
        f.write(contenido)

    nuevo_doc = Documento(
        propietario_id=current_user.id,
        nombre_archivo=file.filename,
        ruta_archivo=ruta,
        hash_sha256=hash_archivo,
    )
    db.add(nuevo_doc)
    db.commit()
    db.refresh(nuevo_doc)

    db.add(LogAuditoria(
        usuario_id=current_user.id,
        evento="DOCUMENTO_SUBIDO",
        detalle=f"Documento '{file.filename}' subido, hash={hash_archivo[:16]}...",
    ))
    db.commit()

    return _a_documento_out(nuevo_doc)


@router.get("/{documento_id}/info-pdf", response_model=DocumentoInfoPdf)
def obtener_info_pdf(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Devuelve número de páginas y dimensiones del PDF.
    El frontend usa esto para renderizar el editor visual a la escala correcta
    y traducir el clic del usuario a coordenadas reales del PDF.
    """
    doc = db.query(Documento).filter(
        Documento.id == documento_id, Documento.propietario_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if not doc.nombre_archivo.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El editor visual de firma solo admite archivos PDF")

    try:
        paginas = pdf_service.obtener_info_paginas(doc.ruta_archivo)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el PDF (¿está corrupto?)")

    return DocumentoInfoPdf(documento_id=doc.id, num_paginas=len(paginas), paginas=paginas)


@router.get("/{documento_id}/archivo")
def descargar_archivo_original(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Sirve el PDF original para que el frontend lo muestre en el editor visual."""
    doc = db.query(Documento).filter(
        Documento.id == documento_id, Documento.propietario_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return FileResponse(doc.ruta_archivo, media_type="application/pdf")


@router.post("/{documento_id}/firmar", response_model=DocumentoOut)
async def firmar_documento(
    documento_id: int,
    certificado_id: int,
    pagina: int,
    pos_x: float,
    pos_y: float,
    archivo_clave: UploadFile = File(...),
    passphrase: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Firma digitalmente un documento PDF ya subido, en dos capas:

    1. FIRMA CRIPTOGRÁFICA (lo que realmente importa legal/técnicamente):
       hash SHA-256 del archivo + firma RSA con la clave privada del usuario.
    2. SELLO VISUAL (lo que se ve): se estampa un recuadro con QR en las
       coordenadas (pagina, pos_x, pos_y) que el usuario eligió en el editor
       visual del frontend. El QR enlaza a una página pública de verificación.

    El usuario sube su clave privada como ARCHIVO .pem (no la pega como texto)
    para evitar corrupción del PEM por copiar/pegar. El servidor la usa solo
    en memoria, nunca la guarda.
    """
    doc = db.query(Documento).filter(
        Documento.id == documento_id, Documento.propietario_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    cert = db.query(Certificado).filter(
        Certificado.id == certificado_id, Certificado.propietario_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    if cert.estado != "vigente":
        raise HTTPException(status_code=400, detail=f"Certificado en estado '{cert.estado}', no se puede firmar")

    clave_privada_bytes = await archivo_clave.read()
    clave_privada_pem = clave_privada_bytes.decode("utf-8", errors="strict").strip()

    # Detección específica de un error muy común: el usuario carga por
    # accidente el certificado público (.pem que empieza con "BEGIN
    # CERTIFICATE") en vez de su clave privada ("BEGIN PRIVATE KEY").
    # Damos un mensaje accionable en vez del genérico "PEM inválido".
    if "BEGIN CERTIFICATE" in clave_privada_pem and "BEGIN PRIVATE KEY" not in clave_privada_pem:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cargaste el certificado público (CERTIFICATE), no tu clave privada. "
                "Necesitas el archivo que descargaste al EMITIR el certificado "
                "(empieza con 'BEGIN PRIVATE KEY'), no el que descargas con el "
                "botón 'Descargar' de la tabla de certificados."
            ),
        )

    with open(doc.ruta_archivo, "rb") as f:
        contenido = f.read()

    # --- 1. Firma criptográfica (sobre el contenido ORIGINAL, sin sello) ---
    try:
        firma_b64 = crypto_service.firmar_documento(contenido, clave_privada_pem, passphrase=passphrase)
    except ValueError as e:
        # Passphrase incorrecta o clave cifrada sin passphrase
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="El archivo cargado no es una clave privada .pem válida (debe empezar con 'BEGIN PRIVATE KEY').",
        )

    firma_valida = crypto_service.verificar_firma(contenido, firma_b64, cert.clave_publica_pem)
    if not firma_valida:
        raise HTTPException(status_code=400, detail="Esta clave privada no corresponde al certificado seleccionado")

    codigo_verificacion = uuid.uuid4().hex[:12]

    # --- 2. Datos del firmante para el sello visual ---
    perfil = db.query(PerfilProfesional).filter(PerfilProfesional.usuario_id == current_user.id).first()
    nombre_firmante = perfil.nombre_completo if perfil else current_user.username
    fecha_firma_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    url_verificacion = f"{FRONTEND_URL}/verificar/{codigo_verificacion}"

    ruta_pdf_firmado = os.path.join(FIRMADOS_DIR, f"{current_user.id}_{codigo_verificacion}.pdf")

    if doc.nombre_archivo.lower().endswith(".pdf"):
        try:
            pdf_service.estampar_firma_visual(
                ruta_pdf_original=doc.ruta_archivo,
                ruta_pdf_salida=ruta_pdf_firmado,
                pagina=pagina,
                x=pos_x,
                y=pos_y,
                nombre_firmante=nombre_firmante,
                fecha_firma_str=fecha_firma_str,
                numero_serie_certificado=cert.numero_serie,
                url_verificacion=url_verificacion,
            )
        except Exception:
            raise HTTPException(status_code=400, detail="No se pudo estampar la firma visual en el PDF")
    else:
        ruta_pdf_firmado = None  # archivos no-PDF solo llevan firma criptográfica

    # Guardar hash del PDF firmado para que verificar/por-archivo funcione
    # con el PDF descargado (que tiene bytes adicionales del sello QR)
    hash_firmado = None
    if ruta_pdf_firmado and os.path.exists(ruta_pdf_firmado):
        with open(ruta_pdf_firmado, "rb") as f_signed:
            hash_firmado = crypto_service.calcular_sha256(f_signed.read())

    doc.firma_digital = firma_b64
    doc.certificado_id = cert.id
    doc.pagina_firma = pagina
    doc.pos_x_firma = int(pos_x)
    doc.pos_y_firma = int(pos_y)
    doc.ruta_pdf_firmado = ruta_pdf_firmado
    doc.hash_firmado = hash_firmado
    doc.codigo_verificacion = codigo_verificacion
    db.commit()
    db.refresh(doc)

    db.add(LogAuditoria(
        usuario_id=current_user.id,
        evento="DOCUMENTO_FIRMADO",
        detalle=f"Documento '{doc.nombre_archivo}' firmado con certificado serie={cert.numero_serie}, codigo={codigo_verificacion}",
    ))
    db.commit()

    return _a_documento_out(doc)


@router.get("/{documento_id}/descargar-firmado")
def descargar_pdf_firmado(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Descarga el PDF final con el sello visual + QR ya estampados."""
    doc = db.query(Documento).filter(
        Documento.id == documento_id, Documento.propietario_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not doc.ruta_pdf_firmado or not os.path.exists(doc.ruta_pdf_firmado):
        raise HTTPException(status_code=400, detail="Este documento no tiene un PDF firmado disponible")

    return FileResponse(
        doc.ruta_pdf_firmado,
        media_type="application/pdf",
        filename=f"firmado_{doc.nombre_archivo}",
    )


@router.get("/{documento_id}/verificar-firma")
def verificar_firma_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Verifica la firma digital usando el hash SHA-256 guardado en la BD.
    No lee el archivo de disco, lo que lo hace robusto ante reinicios del servidor
    (Render free tier borra archivos efímeros).
    """
    doc = db.query(Documento).filter(Documento.id == documento_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not doc.firma_digital or not doc.certificado_id:
        raise HTTPException(status_code=400, detail="Este documento no ha sido firmado aún")

    cert = db.query(Certificado).filter(Certificado.id == doc.certificado_id).first()

    firma_valida = crypto_service.verificar_firma_por_hash(
        doc.hash_sha256, doc.firma_digital, cert.clave_publica_pem
    )

    return {
        "documento_id": documento_id,
        "firma_valida": firma_valida,
        "certificado_serie": cert.numero_serie,
        "mensaje": "Firma válida — el documento no fue alterado tras la firma"
                   if firma_valida else
                   "Firma inválida: el documento fue modificado o la firma no corresponde al certificado",
    }


@router.get("/", response_model=List[DocumentoOut])
def listar_documentos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    docs = db.query(Documento).filter(Documento.propietario_id == current_user.id).all()
    return [_a_documento_out(d) for d in docs]


@router.get("/{documento_id}", response_model=DocumentoOut)
def obtener_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    doc = db.query(Documento).filter(
        Documento.id == documento_id, Documento.propietario_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return _a_documento_out(doc)


@router.get("/{documento_id}/verificar-integridad")
def verificar_integridad_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Recalcula el hash del archivo en disco y lo compara con el guardado en la BD."""
    doc = db.query(Documento).filter(Documento.id == documento_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if not os.path.exists(doc.ruta_archivo):
        return {
            "documento_id": documento_id,
            "integro": None,
            "hash_guardado": doc.hash_sha256,
            "mensaje": (
                "El archivo original no está en el servidor (almacenamiento efímero — "
                "se borra al reiniciar). La firma criptográfica sigue siendo verificable."
            ),
        }

    with open(doc.ruta_archivo, "rb") as f:
        contenido_actual = f.read()

    integro = crypto_service.verificar_integridad(contenido_actual, doc.hash_sha256)
    return {
        "documento_id": documento_id,
        "integro": integro,
        "hash_guardado": doc.hash_sha256,
        "mensaje": "Integridad OK: el archivo no ha sido alterado" if integro
                   else "¡Alerta! El hash no coincide — el archivo fue modificado",
    }


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    doc = db.query(Documento).filter(
        Documento.id == documento_id, Documento.propietario_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if os.path.exists(doc.ruta_archivo):
        os.remove(doc.ruta_archivo)
    if doc.ruta_pdf_firmado and os.path.exists(doc.ruta_pdf_firmado):
        os.remove(doc.ruta_pdf_firmado)

    db.delete(doc)
    db.commit()

    db.add(LogAuditoria(
        usuario_id=current_user.id,
        evento="DOCUMENTO_ELIMINADO",
        detalle=f"Documento '{doc.nombre_archivo}' eliminado",
    ))
    db.commit()

    return None
