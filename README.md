# Plataforma Web Segura de Firma Digital y Validación Criptográfica con DevSecOps

Proyecto Final — Ingeniería de Seguridad del Software
Universidad de las Fuerzas Armadas ESPE

## Resumen

Plataforma web que permite generar, firmar, validar y proteger documentos digitales
mediante hash (SHA-256), cifrado simétrico (AES), cifrado asimétrico (RSA), firma
digital y una Autoridad Certificadora (CA) simulada con certificados X.509.

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React + Vite |
| Backend | Python + FastAPI |
| Base de datos | SQLite |
| Criptografía | librería `cryptography` (Python) |
| Metodología | Kanban |
| Versionado | Git + GitHub |
| CI/CD | GitHub Actions |
| Escaneo de seguridad | Bandit (SAST) + Nmap (desde Kali) |
| Entorno de red | Ubuntu Server (backend+DB) · Ubuntu Desktop (cliente) · Kali Linux (pentesting) · Metasploitable2 (target controlado) |

## Estructura del repositorio

```
firma-digital-segura/
├── backend/        # API FastAPI (ver backend/README.md)
├── frontend/       # SPA React + Vite
├── docs/           # informe técnico, artículo técnico, diagramas
├── scripts/        # scripts de análisis estadístico, despliegue, etc.
└── .github/workflows/  # pipeline CI/CD (DevSecOps)
```

## Cómo correr el proyecto completo (desarrollo local)

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (en otra terminal):
```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173` (frontend) — el backend corre en `http://localhost:8000`
(Swagger en `/docs`).

## Estado del proyecto (actualizar conforme avancemos)

- [x] Fase 1 — Estructura del repo, esqueletos backend/frontend
- [x] Fase 2 — CRUD de Usuarios + login seguro con JWT
- [x] Fase 3 — Criptografía: SHA-256, AES, RSA, firma digital, CA simulada
- [x] Fase 4 — CRUD Certificados y Documentos + Logs de auditoría
- [ ] Fase 5 — DevSecOps: GitHub Actions, Bandit, despliegue a Ubuntu Server, escaneo desde Kali
- [ ] Fase 6 — Pruebas, análisis estadístico, artículo técnico, informe, video, defensa
# FirmaDigital
