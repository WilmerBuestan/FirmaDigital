import { useState, useEffect, useCallback, useRef } from "react";
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

function ToastContainer({ toasts, onRemove }) {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.tipo}`}>
          <span className="toast-text">{t.texto}</span>
          <button className="toast-close" onClick={() => onRemove(t.id)}>×</button>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState("documentos");
  const [certificados, setCertificados] = useState([]);
  const [documentos, setDocumentos] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [claveDescargada, setClaveDescargada] = useState(null);
  const [archivoSeleccionado, setArchivoSeleccionado] = useState(null);
  const [nombreCertificado, setNombreCertificado] = useState("");
  const [mostrarFormCert, setMostrarFormCert] = useState(false);

  const [editorAbierto, setEditorAbierto] = useState(false);
  const [documentoEditando, setDocumentoEditando] = useState(null);
  const [infoPdfEditor, setInfoPdfEditor] = useState(null);
  const [bytesPdfEditor, setBytesPdfEditor] = useState(null);
  const [archivoClavePendiente, setArchivoClavePendiente] = useState(null);
  const [passphrasePendiente, setPassphrasePendiente] = useState(null);
  const [certificadoIdPendiente, setCertificadoIdPendiente] = useState(null);
  const [certificadoElegidoPorDocumento, setCertificadoElegidoPorDocumento] = useState({});
  const [passphrasePorDocumento, setPassphrasePorDocumento] = useState({});

  const [passphraseNuevoCert, setPassphraseNuevoCert] = useState("");
  const [mostrarPassphraseCert, setMostrarPassphraseCert] = useState(false);

  const [archivoVerificar, setArchivoVerificar] = useState(null);
  const [resultadoVerificacion, setResultadoVerificacion] = useState(null);
  const [verificando, setVerificando] = useState(false);

  const timers = useRef({});

  const removeToast = useCallback((id) => {
    clearTimeout(timers.current[id]);
    delete timers.current[id];
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((tipo, texto) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, tipo, texto }]);
    timers.current[id] = setTimeout(() => removeToast(id), 5500);
  }, [removeToast]);

  const cargarDatos = useCallback(async () => {
    try {
      const [certs, docs] = await Promise.all([listarCertificados(), listarDocumentos()]);
      setCertificados(certs);
      setDocumentos(docs);
    } catch {
      toast("error", "No se pudieron cargar los datos del servidor.");
    }
  }, [toast]);

  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const [certs, docs] = await Promise.all([listarCertificados(), listarDocumentos()]);
        if (activo) { setCertificados(certs); setDocumentos(docs); }
      } catch {
        if (activo) toast("error", "No se pudieron cargar los datos.");
      }
    })();
    return () => { activo = false; };
  }, [toast]);

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
      setMostrarFormCert(false);
      toast(
        "exito",
        passphraseNuevoCert.trim()
          ? `Certificado emitido. La clave privada está protegida — descárgala ahora.`
          : `Certificado "${cert.nombre || cert.numero_serie.slice(0, 10)}" emitido. Descarga tu clave privada.`,
      );
      cargarDatos();
    } catch (err) {
      toast("error", err.response?.data?.detail || "Error al emitir certificado");
    }
  }

  function handleDescargarClavePrivada() {
    descargarClavePrivada(
      claveDescargada.clave_privada_pem,
      claveDescargada.nombre || `clave_${claveDescargada.numero_serie.slice(0, 8)}`,
    );
    toast("exito", "Clave privada descargada. Guárdala en lugar seguro y no la compartas.");
    setClaveDescargada(null);
  }

  async function handleDescargarCertificado(cert) {
    try {
      await descargarCertificado(cert.id, cert.nombre || `certificado_${cert.numero_serie.slice(0, 8)}`);
    } catch {
      toast("error", "Error al descargar el certificado");
    }
  }

  async function handleValidarCertificado(id) {
    try {
      const r = await validarCertificado(id);
      toast(r.valido ? "exito" : "warn", `Certificado #${id}: ${r.estado} — ${r.motivo}`);
    } catch {
      toast("error", "Error al validar certificado");
    }
  }

  async function handleRevocarCertificado(id) {
    if (!window.confirm(`¿Revocar certificado #${id}? Esta acción no se puede deshacer.`)) return;
    try {
      await revocarCertificado(id);
      toast("exito", `Certificado #${id} revocado`);
      cargarDatos();
    } catch {
      toast("error", "Error al revocar certificado");
    }
  }

  async function handleSubirDocumento(e) {
    e.preventDefault();
    if (!archivoSeleccionado) return;
    try {
      await subirDocumento(archivoSeleccionado);
      toast("exito", `"${archivoSeleccionado.name}" subido correctamente`);
      setArchivoSeleccionado(null);
      cargarDatos();
    } catch (err) {
      toast("error", err.response?.data?.detail || "Error al subir documento");
    }
  }

  async function handleArchivoClaveParaFirmar(documento, certificadoIdStr, archivoClave, passphrase) {
    const certificadoId = certificadoIdStr ? Number(certificadoIdStr) : null;
    if (!certificadoId) {
      toast("error", "Selecciona un certificado antes de cargar la clave privada");
      return;
    }
    if (!documento.nombre_archivo.toLowerCase().endsWith(".pdf")) {
      toast("error", "El editor visual de firma solo funciona con archivos PDF");
      return;
    }
    const textoArchivo = await archivoClave.text();
    if (textoArchivo.includes("BEGIN CERTIFICATE") && !textoArchivo.includes("BEGIN PRIVATE KEY")) {
      toast("error", "Ese archivo es el certificado público, no la clave privada. Carga el archivo que dice 'BEGIN PRIVATE KEY'.");
      return;
    }
    if (!textoArchivo.includes("BEGIN PRIVATE KEY")) {
      toast("error", "Ese archivo no parece ser una clave privada .pem válida.");
      return;
    }
    try {
      const info = await obtenerInfoPdf(documento.id);
      const bytes = await obtenerBytesDocumento(documento.id);
      if (!bytes || !info) { toast("error", "No se pudo cargar el PDF. Intenta de nuevo."); return; }
      setInfoPdfEditor(info);
      setBytesPdfEditor(bytes);
      setDocumentoEditando(documento);
      setArchivoClavePendiente(archivoClave);
      setPassphrasePendiente(passphrase || null);
      setCertificadoIdPendiente(certificadoId);
      setEditorAbierto(true);
    } catch (err) {
      toast("error", err.message || err.response?.data?.detail || "No se pudo abrir el editor de firma");
    }
  }

  async function handleConfirmarPosicionFirma({ pagina, x, y }) {
    try {
      await firmarDocumento(documentoEditando.id, certificadoIdPendiente, archivoClavePendiente, pagina, x, y, passphrasePendiente);
      toast("exito", `"${documentoEditando.nombre_archivo}" firmado y sellado con QR`);
      cerrarEditor();
      cargarDatos();
    } catch (err) {
      toast("error", err.response?.data?.detail || "Error al firmar el documento");
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
      const r = await verificarPorArchivo(archivoVerificar);
      setResultadoVerificacion(r);
    } catch (err) {
      toast("error", err.response?.data?.detail || "Error al verificar el archivo");
    } finally {
      setVerificando(false);
    }
  }

  async function handleVerificarFirma(documentoId) {
    try {
      const r = await verificarFirma(documentoId);
      toast(r.firma_valida ? "exito" : "warn", r.mensaje);
    } catch (err) {
      toast("warn", err.response?.data?.detail || "Este documento no ha sido firmado aún");
    }
  }

  async function handleVerificarIntegridad(documentoId) {
    try {
      const r = await verificarIntegridad(documentoId);
      if (r.integro === null || r.integro === undefined) {
        toast("warn", r.mensaje || "El archivo original no está en el servidor (almacenamiento temporal). La firma criptográfica sigue siendo válida.");
      } else if (r.integro) {
        toast("exito", "Integridad OK — el archivo no fue alterado desde que se subió");
      } else {
        toast("error", "¡Alerta! El hash no coincide — el contenido del archivo fue modificado");
      }
    } catch {
      toast("error", "Error al verificar integridad");
    }
  }

  async function handleDescargarFirmado(documento) {
    try {
      await descargarPdfFirmado(documento.id, documento.nombre_archivo);
    } catch {
      toast("warn", "El PDF firmado no está disponible en el servidor. En Render (plan gratuito) los archivos se borran al reiniciar. Vuelve a firmar el documento para regenerarlo.");
    }
  }

  async function handleEliminarDocumento(documentoId, nombre) {
    if (!window.confirm(`¿Eliminar "${nombre}"? Esta acción no se puede deshacer.`)) return;
    try {
      await eliminarDocumento(documentoId);
      toast("exito", `Documento eliminado`);
      cargarDatos();
    } catch {
      toast("error", "Error al eliminar documento");
    }
  }

  const certVigentes = certificados.filter((c) => c.estado === "vigente").length;
  const docsFirmados = documentos.filter((d) => d.firmado).length;

  const TABS = [
    { key: "documentos", label: "Documentos", count: documentos.length },
    { key: "certificados", label: "Certificados", count: certificados.length },
    { key: "verificar", label: "Verificar" },
  ];

  return (
    <div className="app-shell">
      <TopBar />
      <ToastContainer toasts={toasts} onRemove={removeToast} />

      <div className="dashboard">
        <div className="dash-header">
          <div>
            <h1 className="dash-title">Panel de control</h1>
            <p className="dash-subtitle">Firma documentos, gestiona certificados y verifica autenticidad.</p>
          </div>
        </div>

        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-icon-wrap stat-blue">
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div className="stat-value">{documentos.length}</div>
              <div className="stat-label">Documentos</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon-wrap stat-green">
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div className="stat-value stat-green-text">{docsFirmados}</div>
              <div className="stat-label">Firmados</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon-wrap stat-purple">
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div className="stat-value">{certificados.length}</div>
              <div className="stat-label">Certificados</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon-wrap stat-green">
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div className="stat-value stat-green-text">{certVigentes}</div>
              <div className="stat-label">Vigentes</div>
            </div>
          </div>
        </div>

        <div className="tabs-bar">
          {TABS.map(({ key, label, count }) => (
            <button
              key={key}
              className={`tab-btn ${tab === key ? "tab-btn-active" : ""}`}
              onClick={() => setTab(key)}
            >
              {label}
              {count > 0 && <span className="tab-count">{count}</span>}
            </button>
          ))}
        </div>

        {/* ── DOCUMENTOS ── */}
        {tab === "documentos" && (
          <div className="tab-content">
            <div className="panel">
              <div className="panel-header">
                <h2 className="panel-title">Subir documento</h2>
              </div>
              <form className="upload-row" onSubmit={handleSubirDocumento}>
                <div className="upload-row-file">
                  <SelectorArchivo
                    etiqueta="Seleccionar PDF"
                    archivoActual={archivoSeleccionado}
                    onFileSelected={setArchivoSeleccionado}
                  />
                </div>
                <button type="submit" className="btn-primary" disabled={!archivoSeleccionado}>
                  Subir
                </button>
              </form>
            </div>

            {documentos.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon-wrap">
                  <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <p className="empty-title">No has subido documentos aún</p>
                <p className="empty-sub">Sube un PDF para poder firmarlo digitalmente.</p>
              </div>
            ) : (
              <div className="doc-list">
                {documentos.map((d) => (
                  <div key={d.id} className={`doc-card ${d.firmado ? "doc-card-signed" : ""}`}>
                    <div className="doc-card-head">
                      <div className="doc-card-icon-wrap">
                        <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </div>
                      <div className="doc-card-meta">
                        <span className="doc-card-name">{d.nombre_archivo}</span>
                        <span className="doc-card-hash">SHA-256: {d.hash_sha256.slice(0, 24)}…</span>
                      </div>
                      <div className="doc-card-status">
                        {d.firmado
                          ? <span className="badge badge-vigente">Firmado</span>
                          : <span className="badge badge-pendiente">Sin firma</span>
                        }
                      </div>
                    </div>

                    {!d.firmado && (
                      <div className="signing-section">
                        <div className="signing-title">
                          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          Firmar este documento
                        </div>
                        <div className="signing-fields">
                          <select
                            className="form-select"
                            value={certificadoElegidoPorDocumento[d.id] || ""}
                            onChange={(e) =>
                              setCertificadoElegidoPorDocumento((prev) => ({ ...prev, [d.id]: e.target.value }))
                            }
                          >
                            <option value="">Selecciona un certificado…</option>
                            {certificados.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.nombre || c.numero_serie.slice(0, 12)} — {c.estado}
                              </option>
                            ))}
                          </select>
                          <input
                            type="password"
                            placeholder="Passphrase (solo si la clave está protegida)"
                            value={passphrasePorDocumento[d.id] || ""}
                            onChange={(e) =>
                              setPassphrasePorDocumento((prev) => ({ ...prev, [d.id]: e.target.value }))
                            }
                            className="form-input"
                          />
                          <SelectorArchivo
                            etiqueta="Cargar clave privada (.pem)"
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
                        </div>
                      </div>
                    )}

                    <div className="doc-card-actions">
                      {d.firmado && (
                        <button className="btn-action btn-action-primary" onClick={() => handleDescargarFirmado(d)}>
                          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          PDF firmado
                        </button>
                      )}
                      <button className="btn-action" onClick={() => handleVerificarFirma(d.id)}>
                        Verificar firma
                      </button>
                      <button className="btn-action" onClick={() => handleVerificarIntegridad(d.id)}>
                        Integridad
                      </button>
                      <button className="btn-action btn-action-danger" onClick={() => handleEliminarDocumento(d.id, d.nombre_archivo)}>
                        Eliminar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── CERTIFICADOS ── */}
        {tab === "certificados" && (
          <div className="tab-content">
            {claveDescargada && (
              <div className="alert-key">
                <div className="alert-key-icon">
                  <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <div className="alert-key-body">
                  <strong>Descarga tu clave privada ahora</strong>
                  <p>Esta es la única vez que puedes descargarla. Sin ella no podrás firmar documentos.</p>
                  <button className="btn-warning" onClick={handleDescargarClavePrivada}>
                    Descargar clave privada (.pem)
                  </button>
                </div>
              </div>
            )}

            <div className="panel">
              <div className="panel-header">
                <h2 className="panel-title">Mis certificados</h2>
                <button
                  className={mostrarFormCert ? "btn-secondary-sm" : "btn-primary-sm"}
                  onClick={() => setMostrarFormCert((v) => !v)}
                >
                  {mostrarFormCert ? "Cancelar" : "+ Nuevo certificado"}
                </button>
              </div>

              {mostrarFormCert && (
                <div className="form-panel">
                  <div className="form-group">
                    <label className="form-label">Nombre del certificado</label>
                    <input
                      type="text"
                      placeholder="Ej. Firma personal, Trabajo académico…"
                      value={nombreCertificado}
                      onChange={(e) => setNombreCertificado(e.target.value)}
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <div className="form-label-row">
                      <label className="form-label">Passphrase de seguridad</label>
                      <button
                        type="button"
                        className={`toggle-switch ${mostrarPassphraseCert ? "toggle-on" : ""}`}
                        onClick={() => setMostrarPassphraseCert((v) => !v)}
                      >
                        <span className="toggle-thumb" />
                      </button>
                    </div>
                    {mostrarPassphraseCert ? (
                      <>
                        <input
                          type="password"
                          placeholder="Mínimo 8 caracteres"
                          value={passphraseNuevoCert}
                          onChange={(e) => setPassphraseNuevoCert(e.target.value)}
                          className="form-input"
                          minLength={8}
                        />
                        <p className="form-hint">La passphrase cifra tu clave privada. La necesitarás cada vez que firmes.</p>
                      </>
                    ) : (
                      <p className="form-hint">Sin passphrase, cualquiera con el archivo .pem puede firmar en tu nombre.</p>
                    )}
                  </div>
                  <button className="btn-primary" onClick={handleEmitirCertificado}>
                    Emitir certificado
                  </button>
                </div>
              )}

              {certificados.length === 0 && !mostrarFormCert ? (
                <div className="empty-state">
                  <div className="empty-icon-wrap">
                    <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                      <path d="M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <p className="empty-title">No tienes certificados</p>
                  <p className="empty-sub">Emite tu primer certificado digital para poder firmar documentos.</p>
                  <button className="btn-primary" onClick={() => setMostrarFormCert(true)}>
                    Emitir primer certificado
                  </button>
                </div>
              ) : (
                <div className="cert-grid">
                  {certificados.map((c) => (
                    <div key={c.id} className={`cert-card cert-${c.estado}`}>
                      <div className="cert-card-head">
                        <div className="cert-card-icon">
                          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                        <span className={`badge badge-${c.estado}`}>{c.estado}</span>
                      </div>
                      <div className="cert-card-name">{c.nombre || "Sin nombre"}</div>
                      <div className="cert-card-detail">Serie: {c.numero_serie.slice(0, 16)}…</div>
                      <div className="cert-card-detail">Expira: {new Date(c.fecha_expiracion).toLocaleDateString()}</div>
                      <div className="cert-card-actions">
                        <button className="btn-action" onClick={() => handleDescargarCertificado(c)}>Descargar</button>
                        <button className="btn-action" onClick={() => handleValidarCertificado(c.id)}>Validar</button>
                        <button className="btn-action btn-action-danger" onClick={() => handleRevocarCertificado(c.id)}>Revocar</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── VERIFICAR ── */}
        {tab === "verificar" && (
          <div className="tab-content">
            <div className="panel">
              <div className="panel-header">
                <h2 className="panel-title">Verificar autenticidad</h2>
              </div>
              <p className="panel-desc">
                Sube cualquier PDF firmado en esta plataforma para comprobar su autenticidad y ver quién lo firmó — sin necesidad de iniciar sesión.
              </p>
              <form onSubmit={handleVerificarPorArchivo}>
                <div className="verify-zone">
                  <SelectorArchivo
                    etiqueta="Selecciona el documento a verificar"
                    archivoActual={archivoVerificar}
                    onFileSelected={setArchivoVerificar}
                  />
                  <button type="submit" className="btn-primary" disabled={!archivoVerificar || verificando}>
                    {verificando ? (
                      <><span className="spinner-sm" /> Verificando…</>
                    ) : "Verificar"}
                  </button>
                </div>
              </form>

              {resultadoVerificacion && (
                <div className={`vr-result ${
                  resultadoVerificacion.autentico ? "vr-ok"
                  : resultadoVerificacion.encontrado ? "vr-warn"
                  : "vr-error"
                }`}>
                  <div className="vr-header">
                    {!resultadoVerificacion.encontrado && (
                      <>
                        <div className="vr-icon vr-icon-error">✗</div>
                        <div>
                          <div className="vr-title">Documento no encontrado</div>
                          <div className="vr-msg">{resultadoVerificacion.mensaje}</div>
                        </div>
                      </>
                    )}
                    {resultadoVerificacion.encontrado && !resultadoVerificacion.firmado && (
                      <>
                        <div className="vr-icon vr-icon-warn">!</div>
                        <div>
                          <div className="vr-title">Documento sin firma</div>
                          <div className="vr-msg">{resultadoVerificacion.mensaje}</div>
                        </div>
                      </>
                    )}
                    {resultadoVerificacion.firmado && (
                      <>
                        <div className={`vr-icon ${resultadoVerificacion.autentico ? "vr-icon-ok" : "vr-icon-warn"}`}>
                          {resultadoVerificacion.autentico ? "✓" : "!"}
                        </div>
                        <div>
                          <div className="vr-title">
                            {resultadoVerificacion.autentico ? "Documento auténtico y válido" : "No se pudo verificar la autenticidad"}
                          </div>
                          <div className="vr-msg">{resultadoVerificacion.verificacion?.mensaje}</div>
                        </div>
                      </>
                    )}
                  </div>

                  {resultadoVerificacion.firmado && (
                    <div className="vr-grid">
                      <div className="vr-col">
                        <div className="vr-col-title">Documento</div>
                        <div className="vr-row"><span>Nombre</span><span>{resultadoVerificacion.documento?.nombre_archivo}</span></div>
                        <div className="vr-row"><span>Fecha</span><span>{new Date(resultadoVerificacion.documento?.subido_en).toLocaleString()}</span></div>
                      </div>
                      <div className="vr-col">
                        <div className="vr-col-title">Firmante</div>
                        <div className="vr-row">
                          <span>Nombre</span>
                          <span>{resultadoVerificacion.firmante?.nombre_completo || resultadoVerificacion.firmante?.username}</span>
                        </div>
                        {resultadoVerificacion.firmante?.cedula && (
                          <div className="vr-row"><span>C.I.</span><span>{resultadoVerificacion.firmante.cedula}</span></div>
                        )}
                        {resultadoVerificacion.firmante?.titulo_profesional && (
                          <div className="vr-row"><span>Título</span><span>{resultadoVerificacion.firmante.titulo_profesional}</span></div>
                        )}
                        {resultadoVerificacion.firmante?.trabajo && (
                          <div className="vr-row"><span>Institución</span><span>{resultadoVerificacion.firmante.trabajo}</span></div>
                        )}
                      </div>
                      <div className="vr-col">
                        <div className="vr-col-title">Certificado</div>
                        <div className="vr-row"><span>Serie</span><span>{resultadoVerificacion.certificado?.numero_serie?.slice(0, 16)}…</span></div>
                        <div className="vr-row">
                          <span>Estado</span>
                          <span className={`badge badge-${resultadoVerificacion.certificado?.estado}`}>
                            {resultadoVerificacion.certificado?.estado}
                          </span>
                        </div>
                        <div className="vr-row">
                          <span>Expira</span>
                          <span>{new Date(resultadoVerificacion.certificado?.fecha_expiracion).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
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
