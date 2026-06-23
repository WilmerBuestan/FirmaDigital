import apiClient from "./client";

export async function emitirCertificado(nombre) {
  const { data } = await apiClient.post("/certificados/emitir", { nombre: nombre || null });
  return data; // incluye clave_privada_pem UNA SOLA VEZ
}

export async function listarCertificados() {
  const { data } = await apiClient.get("/certificados/");
  return data;
}

export async function validarCertificado(certificadoId) {
  const { data } = await apiClient.get(`/certificados/${certificadoId}/validar`);
  return data;
}

export async function revocarCertificado(certificadoId) {
  const { data } = await apiClient.delete(`/certificados/${certificadoId}/revocar`);
  return data;
}

export async function descargarCertificado(certificadoId, nombreSugerido) {
  const response = await apiClient.get(`/certificados/${certificadoId}/descargar`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${nombreSugerido || "certificado"}.pem`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

/**
 * Descarga la clave privada como archivo .pem en el navegador del usuario.
 * Se llama inmediatamente después de emitir el certificado, ya que el
 * backend solo la entrega una vez en esa respuesta.
 */
export function descargarClavePrivada(clavePrivadaPem, nombreSugerido) {
  const blob = new Blob([clavePrivadaPem], { type: "application/x-pem-file" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${nombreSugerido || "clave_privada"}.pem`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
