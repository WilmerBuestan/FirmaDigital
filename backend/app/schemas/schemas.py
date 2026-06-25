"""
Schemas Pydantic.
Cumplen el requisito DevSecOps de "validación de entradas": FastAPI + Pydantic
rechaza automáticamente payloads mal formados antes de que lleguen a la lógica
de negocio.
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


# ---------- Usuario ----------
class UsuarioCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    activo: Optional[bool] = None


class UsuarioOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    rol: str
    activo: bool
    creado_en: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Certificado ----------
class EmitirCertificadoRequest(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=100)
    passphrase: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Si se provee, la clave privada quedará cifrada con esta contraseña.",
    )


class CertificadoOut(BaseModel):
    id: int
    propietario_id: int
    nombre: Optional[str] = None
    numero_serie: str
    emisor: str
    fecha_emision: datetime
    fecha_expiracion: datetime
    estado: str

    class Config:
        from_attributes = True


class CertificadoEmitidoOut(BaseModel):
    """Respuesta especial SOLO para el momento de emisión: incluye la clave
    privada una única vez. Nunca se vuelve a exponer en otros endpoints."""
    id: int
    propietario_id: int
    nombre: Optional[str] = None
    numero_serie: str
    emisor: str
    fecha_emision: datetime
    fecha_expiracion: datetime
    estado: str
    clave_privada_pem: str
    aviso: str


# ---------- Perfil Profesional ----------
class PerfilProfesionalCreate(BaseModel):
    nombre_completo: str = Field(min_length=3, max_length=150)
    cedula: str = Field(min_length=5, max_length=20)
    celular: Optional[str] = Field(default=None, max_length=20)
    ubicacion: Optional[str] = Field(default=None, max_length=150)
    trabajo: Optional[str] = Field(default=None, max_length=150)
    titulo_profesional: Optional[str] = Field(default=None, max_length=150)
    nivel_academico: Optional[str] = Field(default=None, max_length=100)


class PerfilProfesionalOut(BaseModel):
    id: int
    usuario_id: int
    nombre_completo: str
    cedula: str
    celular: Optional[str] = None
    ubicacion: Optional[str] = None
    trabajo: Optional[str] = None
    titulo_profesional: Optional[str] = None
    nivel_academico: Optional[str] = None
    actualizado_en: datetime

    class Config:
        from_attributes = True


# ---------- Documento ----------
class DocumentoOut(BaseModel):
    id: int
    propietario_id: int
    nombre_archivo: str
    hash_sha256: str
    cifrado: bool
    firmado: bool = False
    codigo_verificacion: Optional[str] = None
    subido_en: datetime

    class Config:
        from_attributes = True


class VerificarFirmaRequest(BaseModel):
    documento_id: int


class FirmarDocumentoRequest(BaseModel):
    certificado_id: int
    clave_privada_pem: str


class PaginaInfo(BaseModel):
    numero: int
    ancho: float
    alto: float


class DocumentoInfoPdf(BaseModel):
    documento_id: int
    num_paginas: int
    paginas: list[PaginaInfo]


class PosicionFirma(BaseModel):
    pagina: int = Field(ge=1)
    x: float  # coordenada X en puntos PDF (origen abajo-izquierda), elegida en el editor visual
    y: float  # coordenada Y en puntos PDF


# ---------- Auditoría ----------
class LogAuditoriaOut(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    evento: str
    detalle: Optional[str] = None
    ip_origen: Optional[str] = None
    modulo: Optional[str] = None
    metodo_http: Optional[str] = None
    recurso_id: Optional[int] = None
    resultado: Optional[str] = None
    user_agent: Optional[str] = None
    fecha: datetime

    class Config:
        from_attributes = True
