"""
Router de Autenticación.
Login seguro: verifica contraseña hasheada y emite JWT.
También registra eventos en logs de auditoría (requisito del proyecto).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.models import Usuario, LogAuditoria
from app.schemas.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.username == payload.username).first()

    ip_origen = request.client.host if request.client else "desconocida"

    if not usuario or not verify_password(payload.password, usuario.password_hash):
        # Log de intento fallido (auditoría de seguridad)
        log = LogAuditoria(
            usuario_id=usuario.id if usuario else None,
            evento="LOGIN_FALLIDO",
            detalle=f"Intento de login fallido para username='{payload.username}'",
            ip_origen=ip_origen,
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    token = create_access_token(data={"sub": usuario.username, "id": usuario.id})

    log = LogAuditoria(
        usuario_id=usuario.id,
        evento="LOGIN_OK",
        detalle=f"Login exitoso para '{usuario.username}'",
        ip_origen=ip_origen,
    )
    db.add(log)
    db.commit()

    return TokenResponse(access_token=token)
