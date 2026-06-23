import apiClient from "./client";

export async function subirDocumento(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post("/documentos/subir", formData);
  return data;
}

export async function listarDocumentos() {
  const { data } = await apiClient.get("/documentos/");
  return data;
}

export async function obtenerInfoPdf(documentoId) {
  const { data } = await apiClient.get(`/documentos/${documentoId}/info-pdf`);
  return data;
}

/**
 * Descarga los bytes del PDF como ArrayBuffer. Le pasamos esto directo a
 * pdf.js con el parámetro `data` (no `url`), lo cual es más robusto que usar
 * Object URLs de blob: evita problemas de timing entre crear/revocar la URL
 * y el momento en que pdf.js realmente la lee.
 */
export async function obtenerBytesDocumento(documentoId) {
  try {
    const response = await apiClient.get(`/documentos/${documentoId}/archivo`, {
      responseType: "arraybuffer",
    });
    return response.data; // ArrayBuffer
  } catch (err) {
    if (err.response?.data) {
      try {
        const texto = new TextDecoder().decode(err.response.data);
        const json = JSON.parse(texto);
        throw new Error(json.detail || "Error al obtener el documento", { cause: err });
      } catch {
        throw new Error("Error al obtener el documento del servidor", { cause: err });
      }
    }
    throw err;
  }
}

export async function firmarDocumento(documentoId, certificadoId, archivoClavePrivada, pagina, x, y) {
  const formData = new FormData();
  formData.append("archivo_clave", archivoClavePrivada);
  const params = new URLSearchParams({
    certificado_id: certificadoId,
    pagina,
    pos_x: x,
    pos_y: y,
  });
  const { data } = await apiClient.post(
    `/documentos/${documentoId}/firmar?${params.toString()}`,
    formData
  );
  return data;
}

export async function descargarPdfFirmado(documentoId, nombreArchivo) {
  const response = await apiClient.get(`/documentos/${documentoId}/descargar-firmado`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `firmado_${nombreArchivo}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function verificarFirma(documentoId) {
  const { data } = await apiClient.get(`/documentos/${documentoId}/verificar-firma`);
  return data;
}

export async function verificarIntegridad(documentoId) {
  const { data } = await apiClient.get(`/documentos/${documentoId}/verificar-integridad`);
  return data;
}

export async function eliminarDocumento(documentoId) {
  await apiClient.delete(`/documentos/${documentoId}`);
}
