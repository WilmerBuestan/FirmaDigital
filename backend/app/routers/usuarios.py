"""
CRUD de Usuarios (requisito obligatorio: Crear, Consultar, Actualizar, Eliminar).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import hash_password
from app.core.dependencies import get_current_user
from app.models.models import Usuario, LogAuditoria
from app.schemas.schemas import UsuarioCreate, UsuarioUpdate, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(payload: UsuarioCreate, db: Session = Depends(get_db)):
    """Crear (registro de nuevo usuario)."""
    existe = db.query(Usuario).filter(
        (Usuario.username == payload.username) | (Usuario.email == payload.email)
    ).first()
    if existe:
        raise HTTPException(status_code=400, detail="Username o email ya registrado")

    nuevo_usuario = Usuario(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    db.add(LogAuditoria(
        usuario_id=nuevo_usuario.id,
        evento="USUARIO_CREADO",
        detalle=f"Usuario '{nuevo_usuario.username}' registrado",
    ))
    db.commit()

    return nuevo_usuario


@router.get("/", response_model=List[UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Consultar (listar todos los usuarios). Requiere autenticación."""
    return db.query(Usuario).all()


@router.get("/{usuario_id}", response_model=UsuarioOut)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Consultar un usuario específico."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.put("/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Actualizar datos de un usuario."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if payload.email is not None:
        usuario.email = payload.email
    if payload.activo is not None:
        usuario.activo = payload.activo

    db.commit()
    db.refresh(usuario)

    db.add(LogAuditoria(
        usuario_id=usuario.id,
        evento="USUARIO_ACTUALIZADO",
        detalle=f"Usuario '{usuario.username}' actualizado",
    ))
    db.commit()

    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Eliminar (lógica): se marca como inactivo en lugar de borrar físicamente,
    para no perder trazabilidad de certificados/documentos asociados."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.activo = False
    db.commit()

    db.add(LogAuditoria(
        usuario_id=usuario.id,
        evento="USUARIO_ELIMINADO",
        detalle=f"Usuario '{usuario.username}' eliminado (lógico)",
    ))
    db.commit()

    return None
