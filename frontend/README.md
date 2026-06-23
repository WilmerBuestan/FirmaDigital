# Frontend — Plataforma Segura de Firma Digital

SPA en React + Vite. Consume la API del backend FastAPI.

## Cómo correrlo

```bash
cd frontend
npm install
cp .env.example .env      # ajusta VITE_API_URL si el backend no está en localhost:8000
npm run dev
```

Abre `http://localhost:5173`.

## Estructura

```
src/
├── api/            # clientes Axios: auth, certificados, documentos
├── context/        # AuthContext (sesión global, token JWT en localStorage)
├── components/      # RutaProtegida (guard de rutas privadas)
├── pages/          # Login, Register, Dashboard
└── App.jsx         # router principal
```

## Flujo de uso

1. Registrarse en `/register`
2. Iniciar sesión en `/login`
3. En el Dashboard:
   - Emitir un certificado (¡guarda la clave privada que se muestra una sola vez!)
   - Subir un documento
   - Pegar la clave privada en el campo junto al documento y presionar "Firmar"
   - Usar "Verificar firma" y "Verificar integridad" para comprobar que el
     documento sigue intacto (o detectar si fue alterado)

## Build de producción

```bash
npm run build
```

Genera `dist/`, listo para servir desde Ubuntu Server (ej. con Nginx) o cualquier
servidor estático.
