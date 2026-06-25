"""
Punto de entrada de la API.
Plataforma Web Segura de Firma Digital y Validación Criptográfica.
Proyecto Final - Ingeniería de Seguridad del Software.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import engine, Base
from app.core.config import FRONTEND_URL
from app.routers import auth, usuarios, certificados, documentos, perfil, verificacion_publica, auditoria

Base.metadata.create_all(bind=engine)

# Migración segura: agrega columnas nuevas sin borrar datos existentes.
# create_all() no añade columnas en tablas ya creadas, así que lo hacemos manualmente.
def _run_migrations():
    with engine.connect() as conn:
        dialect = engine.dialect.name
        _migrations = [
            ("documentos", "hash_firmado", "VARCHAR"),
        ]
        for table, column, col_type in _migrations:
            try:
                if dialect == "sqlite":
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                else:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"))
                conn.commit()
            except Exception:
                pass  # La columna ya existe

_run_migrations()

app = FastAPI(
    title="Plataforma Segura de Firma Digital",
    description=(
        "API para gestión de usuarios, certificados digitales y documentos, "
        "con funciones criptográficas de hash (SHA-256), cifrado simétrico "
        "(AES-256) y firma digital (RSA + CA simulada)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(certificados.router)
app.include_router(documentos.router)
app.include_router(perfil.router)
app.include_router(verificacion_publica.router)
app.include_router(auditoria.router)


@app.get("/")
def root():
    return {
        "mensaje": "Plataforma Segura de Firma Digital - API activa",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Endpoint simple para monitoreo/CI (verifica que el servicio responde)."""
    return {"status": "ok"}
