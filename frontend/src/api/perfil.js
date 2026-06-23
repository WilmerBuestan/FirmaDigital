import apiClient from "./client";

export async function obtenerMiPerfil() {
  const { data } = await apiClient.get("/perfil/");
  return data;
}

export async function guardarPerfil(perfil) {
  const { data } = await apiClient.put("/perfil/", perfil);
  return data;
}
