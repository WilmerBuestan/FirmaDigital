"""
Configuración general de la aplicación.
Todas las variables sensibles vienen de variables de entorno.
"""
import os
import secrets

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# En producción DEBE venir de la variable de entorno SECRET_KEY.
# El fallback aleatorio es solo para desarrollo local; no persiste entre reinicios.
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
