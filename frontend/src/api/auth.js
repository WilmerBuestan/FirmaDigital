import apiClient from "./client";

export async function login(username, password) {
  const { data } = await apiClient.post("/auth/login", { username, password });
  return data; // { access_token, token_type }
}

export async function registrarUsuario(username, email, password) {
  const { data } = await apiClient.post("/usuarios/", { username, email, password });
  return data;
}
