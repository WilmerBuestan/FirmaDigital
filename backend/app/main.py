"""
Punto de entrada de la API.
Plataforma Web Segura de Firma Digital y Validación Criptográfica.
Proyecto Final - Ingeniería de Seguridad del Software.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.core.config import FRONTEND_URL
from app.routers import auth, usuarios, certificados, documentos, perfil, verificacion_publica, auditoria

# Crea las tablas en SQLite si no existen
Base.metadata.create_all(bind=engine)

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
