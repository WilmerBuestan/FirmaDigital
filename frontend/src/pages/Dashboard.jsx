import { useState, useEffect, useCallback } from "react";
import TopBar from "../components/TopBar";
import SelectorArchivo from "../components/SelectorArchivo";
import EditorFirmaPdf from "../components/EditorFirmaPdf";
import {
  emitirCertificado,
  listarCertificados,
  validarCertificado,
  revocarCertificado,
  descargarCertificado,
  descargarClavePrivada,
} from "../api/certificados";
import {
  subirDocumento,
  listarDocumentos,
  obtenerInfoPdf,
  obtenerBytesDocumento,
  firmarDocumento,
  descargarPdfFirmado,
  verificarFirma,
  verificarIntegridad,
  eliminarDocumento,
} from "../api/documentos";
import { verificarPorArchivo } from "../api/verificacionPublica";

export default function Dashboard() {
  const [certificados, setCertificados] = useState([]);
  const [documentos, setDocumentos] = useState([]);
  const [claveDescargada, setClaveDescargada] = useState(null);
  const [archivoSeleccionado, setArchivoSeleccionado] = useState(null);
  const [mensajes, setMensajes] = useState([]);
  const [nombreCertificado, setNombreCertificado] = useState("");

  const [editorAbierto, setEditorAbierto] = useState(false);
  const [documentoEditando, setDocumentoEditando] = useState(null);
  const [infoPdfEditor, setInfoPdfEditor] = useState(null);
  const [bytesPdfEditor, setBytesPdfEditor] = useState(null);
  const [archivoClavePendiente, setArchivoClavePendiente] = useState(null);
  const [passphrasePendiente, setPassphrasePendiente] = useState(null);
  const [certificadoIdPendiente, setCertificadoIdPendiente] = useState(null);
  const [certificadoElegidoPorDocumento, setCertificadoElegidoPorDocumento] = useState({});
  const [passphrasePorDocumento, setPassphrasePorDocumento] = useState({});

  // Emisión de certificado
  const [passphraseNuevoCert, setPassphraseNuevoCert] = useState("");
  const [mostrarPassphraseCert, setMostrarPassphraseCert] = useState(false);

  // Verificación por archivo
  const [archivoVerificar, setArchivoVerificar] = useState(null);
  const [resultadoVerificacion, setResultadoVerificacion] = useState(null);
  const [verificando, setVerificando] = useState(false);

  function agregarMensaje(tipo, texto) {
    setMensajes((prev) => [{ tipo, texto, id: Date.now() }, ...prev].slice(0, 6));
  }

  const cargarDatos = useCallback(async () => {
    try {
      const [certs, docs] = await Promise.all([listarCertificados(), listarDocumentos()]);
      setCertificados(certs);
      setDocumentos(docs);
    } catch {
      agregarMensaje("error", "No se pudieron cargar los datos del servidor.");
    }
  }, []);

  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const [certs, docs] = await Promise.all([listarCertificados(), listarDocumentos()]);
        if (activo) {
          setCertificados(certs);
          setDocumentos(docs);
        }
      } catch {
        if (activo) agregarMensaje("error", "No se pudieron cargar los datos del servidor.");
      }
    })();
    return () => { activo = false; };
  }, []);

  async function handleEmitirCertificado() {
    try {
      const cert = await emitirCertificado(
        nombreCertificado.trim(),
        passphraseNuevoCert.trim() || null,
      );
      setClaveDescargada(cert);
      setNombreCertificado("");
      setPassphraseNuevoCert("");
      setMostrarPassphraseCert(false);
      const aviso = passphraseNuevoCert.trim()
        ? "Clave privada protegida con passphrase. Descárgala ahora — necesitarás esa contraseña para firmar."
        : "Descarga tu clave privada ahora y guárdala en lugar seguro.";
      agregarMensaje("exito", `Certificado "${cert.nombre || cert.numero_serie}" emitido. ${aviso}`);
      cargarDatos();
    } catch (err) {
      agregarMensaje("error", err.response?.data?.detail || "Error al emitir certificado");
    }
  }

  function handleDescargarClavePrivada() {
    descargarClavePrivada(claveDescargada.clave_privada_pem, claveDescargada.nombre || `clave_${claveDescargada.numero_serie.slice(0, 8)}`);
    agregarMensaje("exito", "Clave privada descargada. Guárdala en un lugar seguro.");
  }

  async function handleDescargarCertificado(cert) {
    try {
      await descargarCertificado(cert.id, cert.nombre || `certificado_${cert.numero_serie.slice(0, 8)}`);
    } catch {
      agregarMensaje("error", "Error al descargar el certificado");
    }
  }

  async function handleValidarCertificado(id) {
    try {
      const resultado = await validarCertificado(id);
      agregarMensaje(resultado.valido ? "exito" : "error", `Certificado #${id}: ${resultado.estado} — ${resultado.motivo}`);
    } catch {
      agregarMensaje("error", "Error al validar certificado");
    }
  }

  async function handleRevocarCertificado(id) {
    try {
      await revocarCertificado(id);
      agregarMensaje("exito", `Certificado #${id} revocado`);
      cargarDatos();
    } catch {
      agregarMensaje("error", "Error al revocar certificado");
    }
  }

  async function handleSubirDocumento(e) {
    e.preventDefault();
    if (!archivoSeleccionado) return;
    try {
      await subirDocumento(archivoSeleccionado);
      agregarMensaje("exito", `Documento '${archivoSeleccionado.name}' subido correctamente`);
      setArchivoSeleccionado(null);
      cargarDatos();
    } catch (err) {
      agregarMensaje("error", err.response?.data?.detail || "Error al subir documento");
    }
  }

  async function handleArchivoClaveParaFirmar(documento, certificadoIdStr, archivoClave, passphrase) {
    const certificadoId = certificadoIdStr ? Number(certificadoIdStr) : null;
    if (!certificadoId) {
      agregarMensaje("error", "Selecciona un certificado antes de cargar la clave privada");
      return;
    }
    if (!documento.nombre_archivo.toLowerCase().endsWith(".pdf")) {
      agregarMensaje("error", "El editor visual de firma solo funciona con archivos PDF");
      return;
    }

    // Validación inmediata en el navegador: detectar si cargaron el
    // certificado público en vez de la clave privada, sin esperar al servidor.
    const textoArchivo = await archivoClave.text();
    if (textoArchivo.includes("BEGIN CERTIFICATE") && !textoArchivo.includes("BEGIN PRIVATE KEY")) {
      agregarMensaje(
        "error",
        "Ese archivo es el certificado público (CERTIFICATE), no tu clave privada. Carga el .pem que dice 'BEGIN PRIVATE KEY' — es el que se descargó al emitir el certificado."
      );
      return;
    }
    if (!textoArchivo.includes("BEGIN PRIVATE KEY")) {
      agregarMensaje("error", "Ese archivo no parece ser una clave privada .pem válida.");
      return;
    }

    try {
      const info = await obtenerInfoPdf(documento.id);
      const bytes = await obtenerBytesDocumento(documento.id);

      if (!bytes || !info) {
        agregarMensaje("error", "No se pudo cargar el PDF para el editor. Intenta de nuevo.");
        return;
      }

      setInfoPdfEditor(info);
      setBytesPdfEditor(bytes);
      setDocumentoEditando(documento);
      setArchivoClavePendiente(archivoClave);
      setPassphrasePendiente(passphrase || null);
      setCertificadoIdPendiente(certificadoId);
      setEditorAbierto(true);
    } catch (err) {
      agregarMensaje("error", err.message || err.response?.data?.detail || "No se pudo abrir el editor de firma");
    }
  }

  async function handleConfirmarPosicionFirma({ pagina, x, y }) {
    try {
      await firmarDocumento(documentoEditando.id, certificadoIdPendiente, archivoClavePendiente, pagina, x, y, passphrasePendiente);
      agregarMensaje("exito", `"${documentoEditando.nombre_archivo}" firmado y sellado correctamente`);
      cerrarEditor();
      cargarDatos();
    } catch (err) {
      agregarMensaje("error", err.response?.data?.detail || "Error al firmar el documento");
    }
  }

  function cerrarEditor() {
    setEditorAbierto(false);
    setDocumentoEditando(null);
    setInfoPdfEditor(null);
    setBytesPdfEditor(null);
    setArchivoClavePendiente(null);
    setPassphrasePendiente(null);
    setCertificadoIdPendiente(null);
  }

  async function handleVerificarPorArchivo(e) {
    e.preventDefault();
    if (!archivoVerificar) return;
    setVerificando(true);
    setResultadoVerificacion(null);
    try {
      const resultado = await verificarPorArchivo(archivoVerificar);
      setResultadoVerificacion(resultado);
    } catch (err) {
      agregarMensaje("error", err.response?.data?.detail || "Error al verificar el archivo");
    } finally {
      setVerificando(false);
    }
  }

  async function handleVerificarFirma(documentoId) {
    try {
      const resultado = await verificarFirma(documentoId);
      agregarMensaje(resultado.firma_valida ? "exito" : "error", resultado.mensaje);
    } catch (err) {
      agregarMensaje("error", err.response?.data?.detail || "Este documento no ha sido firmado aún");
    }
  }

  async function handleVerificarIntegridad(documentoId) {
    try {
      const resultado = await verificarIntegridad(documentoId);
      agregarMensaje(
        resultado.integro ? "exito" : "error",
        resultado.integro ? "Integridad OK: el hash coincide" : "¡Alerta! El archivo fue modificado"
      );
    } catch {
      agregarMensaje("error", "Error al verificar integridad");
    }
  }

  async function handleDescargarFirmado(documento) {
    try {
      await descargarPdfFirmado(documento.id, documento.nombre_archivo);
    } catch (err) {
      agregarMensaje("error", err.response?.data?.detail || "Este documento no tiene un PDF firmado disponible");
    }
  }

  async function handleEliminarDocumento(documentoId) {
    try {
      await eliminarDocumento(documentoId);
      agregarMensaje("exito", `Documento #${documentoId} eliminado`);
      cargarDatos();
    } catch {
      agregarMensaje("error", "Error al eliminar documento");
    }
  }

  return (
    <div className="app-shell">
      <TopBar />
      <div className="dashboard">
        <div className="page-header">
          <h1>Documentos y certificados</h1>
          <p>Emite tu certificado, sube tus documentos y fírmalos con sello visual + código QR verificable.</p>
        </div>

        {mensajes.length > 0 && (
          <div className="mensajes">
            {mensajes.map((m) => (
              <div key={m.id} className={`mensaje mensaje-${m.tipo}`}>{m.texto}</div>
            ))}
          </div>
        )}

        <section className="panel">
          <div className="panel-header">
            <h2>📜 Certificados Digitales</h2>
          </div>

          <div className="emitir-certificado-form">
            <input
              type="text"
              placeholder="Nombre para tu certificado (ej. Firma personal)"
              value={nombreCertificado}
              onChange={(e) => setNombreCertificado(e.target.value)}
              className="input-nombre-certificado"
            />
            <button
              type="button"
              className="btn-small"
              onClick={() => setMostrarPassphraseCert((v) => !v)}
            >
              🔒 {mostrarPassphraseCert ? "Sin passphrase" : "Proteger con passphrase"}
            </button>
            {mostrarPassphraseCert && (
              <input
                type="password"
                placeholder="Passphrase (mín. 8 caracteres) — la necesitarás para firmar"
                value={passphraseNuevoCert}
                onChange={(e) => setPassphraseNuevoCert(e.target.value)}
                className="input-nombre-certificado"
                minLength={8}
              />
            )}
            <button onClick={handleEmitirCertificado}>+ Emitir certificado</button>
          </div>

          {claveDescargada && (
            <div className="clave-privada-box">
              <strong>⚠ Clave privada de "{claveDescargada.nombre || claveDescargada.numero_serie}"</strong>
              <p>{claveDescargada.aviso}</p>
              <button className="btn-descargar-clave" onClick={handleDescargarClavePrivada}>
                ⬇ Descargar clave privada (.pem)
              </button>
            </div>
          )}

          <table>
            <thead>
              <tr><th>ID</th><th>Nombre</th><th>Serie</th><th>Estado</th><th>Expira</th><th>Acciones</th></tr>
            </thead>
            <tbody>
              {certificados.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>{c.nombre || <span className="texto-tenue">Sin nombre</span>}</td>
                  <td title={c.numero_serie}>{c.numero_serie.slice(0, 12)}...</td>
                  <td><span className={`badge badge-${c.estado}`}>{c.estado}</span></td>
                  <td>{new Date(c.fecha_expiracion).toLocaleDateString()}</td>
                  <td>
                    <button className="btn-small" onClick={() => handleDescargarCertificado(c)}>⬇ Descargar</button>
                    <button className="btn-small" onClick={() => handleValidarCertificado(c.id)}>Validar</button>
                    <button className="btn-small btn-danger" onClick={() => handleRevocarCertificado(c.id)}>Revocar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>📄 Documentos</h2>
          </div>

          <form className="upload-form" onSubmit={handleSubirDocumento}>
            <SelectorArchivo
              etiqueta="Elegir documento a subir"
              archivoActual={archivoSeleccionado}
              onFileSelected={setArchivoSeleccionado}
            />
            <button type="submit" disabled={!archivoSeleccionado}>Subir documento</button>
          </form>

          <table>
            <thead>
              <tr><th>ID</th><th>Nombre</th><th>Hash (SHA-256)</th><th>Acciones</th></tr>
            </thead>
            <tbody>
              {documentos.map((d) => (
                <tr key={d.id}>
                  <td>{d.id}</td>
                  <td>
                    {d.nombre_archivo}{" "}
                    {d.firmado && <span className="badge badge-vigente">Firmado</span>}
                  </td>
                  <td title={d.hash_sha256}>{d.hash_sha256.slice(0, 12)}...</td>
                  <td className="acciones-documento">
                    {!d.firmado && (
                      <>
                        <select
                          className="select-certificado-firma"
                          value={certificadoElegidoPorDocumento[d.id] || ""}
                          onChange={(e) =>
                            setCertificadoElegidoPorDocumento((prev) => ({ ...prev, [d.id]: e.target.value }))
                          }
                        >
                          <option value="">Selecciona el certificado a usar...</option>
                          {certificados.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.nombre || c.numero_serie.slice(0, 10)} ({c.estado})
                            </option>
                          ))}
                        </select>
                        <input
                          type="password"
                          placeholder="Passphrase de la clave (si la protegiste)"
                          value={passphrasePorDocumento[d.id] || ""}
                          onChange={(e) =>
                            setPassphrasePorDocumento((prev) => ({ ...prev, [d.id]: e.target.value }))
                          }
                          className="input-passphrase-firma"
                        />
                        <SelectorArchivo
                          etiqueta="Cargue su CLAVE PRIVADA (.pem que dice PRIVATE KEY)"
                          accept=".pem"
                          archivoActual={null}
                          onFileSelected={(file) =>
                            handleArchivoClaveParaFirmar(
                              d,
                              certificadoElegidoPorDocumento[d.id],
                              file,
                              passphrasePorDocumento[d.id] || null,
                            )
                          }
                        />
                      </>
                    )}
                    <div className="botones-documento">
                      {d.firmado && (
                        <button className="btn-small" onClick={() => handleDescargarFirmado(d)}>⬇ PDF firmado</button>
                      )}
                      <button className="btn-small" onClick={() => handleVerificarFirma(d.id)}>Verificar firma</button>
                      <button className="btn-small" onClick={() => handleVerificarIntegridad(d.id)}>Verificar integridad</button>
                      <button className="btn-small btn-danger" onClick={() => handleEliminarDocumento(d.id)}>Eliminar</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>🔍 Verificar documento firmado</h2>
          </div>
          <p className="texto-tenue">
            Sube cualquier PDF firmado en esta plataforma para comprobar su autenticidad y ver quién lo firmó.
          </p>
          <form className="upload-form" onSubmit={handleVerificarPorArchivo}>
            <SelectorArchivo
              etiqueta="Selecciona el documento a verificar"
              archivoActual={archivoVerificar}
              onFileSelected={setArchivoVerificar}
            />
            <button type="submit" disabled={!archivoVerificar || verificando}>
              {verificando ? "Verificando…" : "Verificar autenticidad"}
            </button>
          </form>

          {resultadoVerificacion && (
            <div className={`resultado-verificacion ${resultadoVerificacion.autentico ? "resultado-ok" : resultadoVerificacion.encontrado ? "resultado-warn" : "resultado-error"}`}>
              {!resultadoVerificacion.encontrado && (
                <p>❌ <strong>No encontrado.</strong> {resultadoVerificacion.mensaje}</p>
              )}
              {resultadoVerificacion.encontrado && !resultadoVerificacion.firmado && (
                <p>⚠ <strong>Sin firma.</strong> {resultadoVerificacion.mensaje}</p>
              )}
              {resultadoVerificacion.firmado && (
                <>
                  <p className={resultadoVerificacion.autentico ? "texto-exito" : "texto-error"}>
                    {resultadoVerificacion.autentico ? "✅ Documento auténtico" : "⚠ No se pudo verificar la autenticidad"}
                  </p>
                  <p>{resultadoVerificacion.verificacion?.mensaje}</p>
                  <div className="verificacion-detalle">
                    <div>
                      <strong>Documento</strong>
                      <p>{resultadoVerificacion.documento?.nombre_archivo}</p>
                      <p>Firmado el {new Date(resultadoVerificacion.documento?.subido_en).toLocaleString()}</p>
                    </div>
                    <div>
                      <strong>Firmante</strong>
                      <p>{resultadoVerificacion.firmante?.nombre_completo || resultadoVerificacion.firmante?.username}</p>
                      {resultadoVerificacion.firmante?.cedula && <p>C.I. {resultadoVerificacion.firmante.cedula}</p>}
                      {resultadoVerificacion.firmante?.titulo_profesional && <p>{resultadoVerificacion.firmante.titulo_profesional}</p>}
                      {resultadoVerificacion.firmante?.trabajo && <p>{resultadoVerificacion.firmante.trabajo}</p>}
                    </div>
                    <div>
                      <strong>Certificado</strong>
                      <p>Serie: {resultadoVerificacion.certificado?.numero_serie?.slice(0, 16)}…</p>
                      <p>Estado: <span className={`badge badge-${resultadoVerificacion.certificado?.estado}`}>{resultadoVerificacion.certificado?.estado}</span></p>
                      <p>Expira: {new Date(resultadoVerificacion.certificado?.fecha_expiracion).toLocaleDateString()}</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </section>
      </div>

      {editorAbierto && (
        <EditorFirmaPdf
          bytesPdf={bytesPdfEditor}
          infoPdf={infoPdfEditor}
          onConfirmar={handleConfirmarPosicionFirma}
          onCancelar={cerrarEditor}
        />
      )}
    </div>
  );
}
