"""
Modelos de la base de datos.
Cubren las 3 entidades CRUD obligatorias: Usuarios, Certificados, Documentos.
Más una tabla de Logs para auditoría (requisito del proyecto).
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

_FK_USUARIO = "usuarios.id"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(String, default="usuario")  # usuario | admin
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    certificados = relationship("Certificado", back_populates="propietario")
    documentos = relationship("Documento", back_populates="propietario")


class Certificado(Base):
    __tablename__ = "certificados"

    id = Column(Integer, primary_key=True, index=True)
    propietario_id = Column(Integer, ForeignKey(_FK_USUARIO), nullable=False)
    nombre = Column(String, nullable=True)  # alias amigable elegido por el usuario
    numero_serie = Column(String, unique=True, index=True, nullable=False)
    clave_publica_pem = Column(Text, nullable=False)
    certificado_pem = Column(Text, nullable=False)  # certificado firmado por la CA simulada
    emisor = Column(String, default="CA-Simulada-ProyectoFinal")
    fecha_emision = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_expiracion = Column(DateTime, nullable=False)
    estado = Column(String, default="vigente")  # vigente | revocado | expirado

    propietario = relationship("Usuario", back_populates="certificados")


class Documento(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    propietario_id = Column(Integer, ForeignKey(_FK_USUARIO), nullable=False)
    nombre_archivo = Column(String, nullable=False)
    ruta_archivo = Column(String, nullable=False)
    hash_sha256 = Column(String, nullable=False)
    firma_digital = Column(Text, nullable=True)  # firma RSA en base64, si fue firmado
    certificado_id = Column(Integer, ForeignKey("certificados.id"), nullable=True)
    cifrado = Column(Boolean, default=False)
    pagina_firma = Column(Integer, nullable=True)  # página del PDF donde se estampó la firma visual
    pos_x_firma = Column(Integer, nullable=True)  # coordenada X (puntos PDF) elegida por el usuario
    pos_y_firma = Column(Integer, nullable=True)  # coordenada Y (puntos PDF) elegida por el usuario
    ruta_pdf_firmado = Column(String, nullable=True)  # PDF final con sello visual + QR estampados
    hash_firmado = Column(String, nullable=True)       # hash SHA-256 del PDF firmado (distinto al original)
    codigo_verificacion = Column(String, unique=True, nullable=True, index=True)  # UUID corto para el QR
    subido_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    propietario = relationship("Usuario", back_populates="documentos")


class PerfilProfesional(Base):
    __tablename__ = "perfiles_profesionales"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey(_FK_USUARIO), unique=True, nullable=False)
    nombre_completo = Column(String, nullable=False)
    cedula = Column(String, nullable=False)
    celular = Column(String, nullable=True)
    ubicacion = Column(String, nullable=True)
    trabajo = Column(String, nullable=True)
    titulo_profesional = Column(String, nullable=True)
    nivel_academico = Column(String, nullable=True)  # ej: Tercer Nivel, Maestría, PhD
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario", backref="perfil_profesional", uselist=False)


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey(_FK_USUARIO), nullable=True)
    evento = Column(String, nullable=False)       # LOGIN_OK, CERTIFICADO_EMITIDO, DOCUMENTO_FIRMADO, etc.
    detalle = Column(Text, nullable=True)
    ip_origen = Column(String, nullable=True)
    # Campos enriquecidos para trazabilidad completa (Fase 5 - auditoría)
    modulo = Column(String, nullable=True)        # "auth" | "certificados" | "documentos" | "perfil"
    metodo_http = Column(String, nullable=True)   # "POST" | "GET" | "PUT" | "DELETE"
    recurso_id = Column(Integer, nullable=True)   # ID del recurso afectado
    resultado = Column(String, nullable=True)     # "exito" | "error"
    user_agent = Column(String, nullable=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))
