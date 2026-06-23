"""
Perfil Profesional del usuario: datos que se mostrarán en la verificación
pública del documento firmado (nombre completo, cédula, cargo, título, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import Usuario, PerfilProfesional, LogAuditoria
from app.schemas.schemas import PerfilProfesionalCreate, PerfilProfesionalOut

router = APIRouter(prefix="/perfil", tags=["Perfil Profesional"])


@router.get("/", response_model=PerfilProfesionalOut)
def obtener_mi_perfil(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    perfil = db.query(PerfilProfesional).filter(
        PerfilProfesional.usuario_id == current_user.id
    ).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Aún no has creado tu perfil profesional")
    return perfil


@router.put("/", response_model=PerfilProfesionalOut)
def crear_o_actualizar_perfil(
    payload: PerfilProfesionalCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Crea el perfil si no existe, o lo actualiza si ya existe (upsert)."""
    perfil = db.query(PerfilProfesional).filter(
        PerfilProfesional.usuario_id == current_user.id
    ).first()

    if perfil:
        perfil.nombre_completo = payload.nombre_completo
        perfil.cedula = payload.cedula
        perfil.celular = payload.celular
        perfil.ubicacion = payload.ubicacion
        perfil.trabajo = payload.trabajo
        perfil.titulo_profesional = payload.titulo_profesional
        perfil.nivel_academico = payload.nivel_academico
    else:
        perfil = PerfilProfesional(
            usuario_id=current_user.id,
            nombre_completo=payload.nombre_completo,
            cedula=payload.cedula,
            celular=payload.celular,
            ubicacion=payload.ubicacion,
            trabajo=payload.trabajo,
            titulo_profesional=payload.titulo_profesional,
            nivel_academico=payload.nivel_academico,
        )
        db.add(perfil)

    db.commit()
    db.refresh(perfil)

    db.add(LogAuditoria(
        usuario_id=current_user.id,
        evento="PERFIL_ACTUALIZADO",
        detalle=f"Perfil profesional de '{current_user.username}' creado/actualizado",
    ))
    db.commit()

    return perfil
