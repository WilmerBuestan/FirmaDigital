# Backend — Plataforma Segura de Firma Digital

API REST en FastAPI que implementa autenticación, CRUD de usuarios/certificados/documentos,
y los 4 pilares criptográficos del proyecto: SHA-256, AES, RSA y una CA simulada con
certificados X.509.

## Cómo correrlo (Zorin OS / Ubuntu)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # En bash/zsh. Si usas otra shell, ver docs de venv.
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Luego abre en el navegador: **http://localhost:8000/docs** — ahí está el Swagger
interactivo (FastAPI lo genera automáticamente) para probar cada endpoint.

## Estructura

```
app/
├── core/           # configuración: DB, seguridad (hash/JWT), dependencias de auth
├── models/         # modelos SQLAlchemy (tablas de la base de datos)
├── schemas/        # schemas Pydantic (validación de entrada/salida)
├── services/       # lógica criptográfica pura (crypto_service, ca_service)
├── routers/        # endpoints HTTP (auth, usuarios, certificados, documentos)
└── main.py         # arranque de la app, registro de routers
```

## Flujo típico de uso

1. `POST /usuarios/` → crear cuenta
2. `POST /auth/login` → obtener token JWT
3. `POST /certificados/emitir` (con token) → la CA simulada emite un certificado
   y te entrega la **clave privada UNA SOLA VEZ**. Guárdala, no se vuelve a mostrar.
4. `POST /documentos/subir` → sube un archivo, se calcula su hash SHA-256
5. `POST /documentos/{id}/firmar` → envías `certificado_id` + tu `clave_privada_pem`
   para firmar digitalmente el documento
6. `GET /documentos/{id}/verificar-firma` → comprueba si la firma sigue siendo válida
   (si el archivo se modificó después de firmarlo, esto detecta la alteración)

## Decisión de diseño importante (documentar en el artículo técnico)

La clave privada RSA **nunca se almacena en el servidor**. Se genera al emitir el
certificado, se entrega una sola vez al usuario, y debe ser reenviada por el usuario
cada vez que quiera firmar un documento. Esto refleja cómo funciona la firma digital
en el mundo real (ej. tokens criptográficos físicos o archivos .p12 protegidos).
