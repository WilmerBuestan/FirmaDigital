"""
Consulta de logs de auditoría.
- Usuarios normales: solo ven sus propios eventos.
- Admins: pueden ver todos los logs con filtros opcionales.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import LogAuditoria, Usuario
from app.schemas.schemas import LogAuditoriaOut

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])


@router.get("/mis-logs", response_model=List[LogAuditoriaOut])
def mis_logs(
    limite: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna los últimos N eventos del usuario autenticado."""
    return (
        db.query(LogAuditoria)
        .filter(LogAuditoria.usuario_id == current_user.id)
        .order_by(LogAuditoria.fecha.desc())
        .limit(limite)
        .all()
    )


@router.get("/todos", response_model=List[LogAuditoriaOut])
def todos_los_logs(
    limite: int = Query(default=100, le=500),
    evento: Optional[str] = Query(default=None),
    modulo: Optional[str] = Query(default=None),
    resultado: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Solo para admins: todos los logs con filtros opcionales."""
    if current_user.rol != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver todos los logs")

    q = db.query(LogAuditoria)
    if evento:
        q = q.filter(LogAuditoria.evento.ilike(f"%{evento}%"))
    if modulo:
        q = q.filter(LogAuditoria.modulo == modulo)
    if resultado:
        q = q.filter(LogAuditoria.resultado == resultado)

    return q.order_by(LogAuditoria.fecha.desc()).limit(limite).all()
