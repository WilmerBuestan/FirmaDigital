import axios from "axios";

// La URL del backend. En desarrollo local, FastAPI corre en :8000.
// Cuando despliegues a Ubuntu Server, cambia esto a la IP/dominio real.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_URL,
});

// Agrega automáticamente el token JWT a cada petición si existe
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Si el token expira o es inválido, el backend responde 401.
// Limpiamos sesión y mandamos al usuario al login.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;
