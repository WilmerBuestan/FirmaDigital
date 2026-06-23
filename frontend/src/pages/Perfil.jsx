import { useState, useEffect } from "react";
import TopBar from "../components/TopBar";
import { obtenerMiPerfil, guardarPerfil } from "../api/perfil";

const NIVELES_ACADEMICOS = [
  "Bachillerato",
  "Tercer Nivel (en curso)",
  "Tercer Nivel",
  "Cuarto Nivel - Especialización",
  "Cuarto Nivel - Maestría",
  "Cuarto Nivel - PhD",
];

export default function Perfil() {
  const [form, setForm] = useState({
    nombre_completo: "",
    cedula: "",
    celular: "",
    ubicacion: "",
    trabajo: "",
    titulo_profesional: "",
    nivel_academico: "",
  });
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [mensaje, setMensaje] = useState(null);

  useEffect(() => {
    obtenerMiPerfil()
      .then((data) => setForm((prev) => ({ ...prev, ...data })))
      .catch(() => {}) // si no existe perfil aún, se queda el formulario vacío
      .finally(() => setCargando(false));
  }, []);

  function actualizarCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setGuardando(true);
    setMensaje(null);
    try {
      await guardarPerfil(form);
      setMensaje({ tipo: "exito", texto: "Perfil guardado. Esta información aparecerá al verificar tus documentos firmados." });
    } catch (err) {
      setMensaje({ tipo: "error", texto: err.response?.data?.detail || "Error al guardar el perfil" });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="app-shell">
      <TopBar />
      <div className="dashboard">
        <div className="page-header">
          <h1>Mi perfil profesional</h1>
          <p>Estos datos se muestran a cualquier persona que escanee el QR de tus documentos firmados.</p>
        </div>

        <div className="panel">
          {cargando ? (
            <div className="spinner-cargando-pdf">
              <div className="spinner-ring" />
              Cargando perfil...
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="perfil-grid">
                <div className="campo-perfil campo-perfil-full">
                  <label>Nombre completo *</label>
                  <input
                    type="text"
                    required
                    value={form.nombre_completo}
                    onChange={(e) => actualizarCampo("nombre_completo", e.target.value)}
                    placeholder="Ej. Wilmer Omar Buestan Guaillas"
                  />
                </div>

                <div className="campo-perfil">
                  <label>Cédula *</label>
                  <input
                    type="text"
                    required
                    value={form.cedula}
                    onChange={(e) => actualizarCampo("cedula", e.target.value)}
                    placeholder="Ej. 1750123456"
                  />
                </div>

                <div className="campo-perfil">
                  <label>Celular</label>
                  <input
                    type="text"
                    value={form.celular || ""}
                    onChange={(e) => actualizarCampo("celular", e.target.value)}
                    placeholder="Ej. 0991234567"
                  />
                </div>

                <div className="campo-perfil">
                  <label>Ubicación</label>
                  <input
                    type="text"
                    value={form.ubicacion || ""}
                    onChange={(e) => actualizarCampo("ubicacion", e.target.value)}
                    placeholder="Ej. Quito, Ecuador"
                  />
                </div>

                <div className="campo-perfil">
                  <label>Trabajo / Cargo actual</label>
                  <input
                    type="text"
                    value={form.trabajo || ""}
                    onChange={(e) => actualizarCampo("trabajo", e.target.value)}
                    placeholder="Ej. Oficial de Comunicaciones"
                  />
                </div>

                <div className="campo-perfil">
                  <label>Título profesional</label>
                  <input
                    type="text"
                    value={form.titulo_profesional || ""}
                    onChange={(e) => actualizarCampo("titulo_profesional", e.target.value)}
                    placeholder="Ej. Ingeniero de Software"
                  />
                </div>

                <div className="campo-perfil">
                  <label>Nivel académico</label>
                  <select
                    value={form.nivel_academico || ""}
                    onChange={(e) => actualizarCampo("nivel_academico", e.target.value)}
                  >
                    <option value="">Selecciona...</option>
                    {NIVELES_ACADEMICOS.map((nivel) => (
                      <option key={nivel} value={nivel}>{nivel}</option>
                    ))}
                  </select>
                </div>
              </div>

              {mensaje && (
                <p className={mensaje.tipo === "exito" ? "success-text" : "error-text"} style={{ marginTop: 16 }}>
                  {mensaje.texto}
                </p>
              )}

              <button type="submit" className="btn-guardar-perfil" disabled={guardando}>
                {guardando ? "Guardando..." : "Guardar perfil"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
