import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function verificarDocumentoPublico(codigo) {
  const { data } = await axios.get(`${API_URL}/verificar/${codigo}`);
  return data;
}

export async function verificarPorArchivo(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await axios.post(`${API_URL}/verificar/por-archivo`, formData);
  return data;
}
