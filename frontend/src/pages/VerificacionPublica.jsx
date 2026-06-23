import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { verificarDocumentoPublico } from "../api/verificacionPublica";

export default function VerificacionPublica() {
  const { codigo } = useParams();
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    verificarDocumentoPublico(codigo)
      .then(setResultado)
      .catch(() => setError("No se encontró información para este código de verificación."))
      .finally(() => setCargando(false));
  }, [codigo]);

  if (cargando) {
    return (
      <div className="verificacion-page">
        <div className="spinner-cargando-pdf">
          <div className="spinner-ring" />
          Verificando documento...
        </div>
      </div>
    );
  }

  if (error || !resultado) {
    return (
      <div className="verificacion-page">
        <div className="verificacion-card">
          <div className="verificacion-icono verificacion-icono-error">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <h2>Código no válido</h2>
          <p className="mensaje-verificacion">{error}</p>
        </div>
      </div>
    );
  }

  const { autentico, documento, firmante, certificado, verificacion } = resultado;

  return (
    <div className="verificacion-page">
      <div className="verificacion-card">
        <div className={`verificacion-icono ${autentico ? "verificacion-icono-ok" : "verificacion-icono-error"}`}>
          {autentico ? (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="12" cy="12" r="10" />
            </svg>
          ) : (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          )}
        </div>

        <h2>{autentico ? "Documento auténtico" : "No se pudo verificar"}</h2>
        <p className="mensaje-verificacion">{verificacion.mensaje}</p>

        <div className="verificacion-datos">
          <div className="verificacion-fila">
            <span>Documento</span>
            <span>{documento.nombre_archivo}</span>
          </div>
          <div className="verificacion-fila">
            <span>Firmado por</span>
            <span>{firmante.nombre_completo}</span>
          </div>
          {firmante.titulo_profesional && (
            <div className="verificacion-fila">
              <span>Título</span>
              <span>{firmante.titulo_profesional}</span>
            </div>
          )}
          {firmante.trabajo && (
            <div className="verificacion-fila">
              <span>Cargo</span>
              <span>{firmante.trabajo}</span>
            </div>
          )}
          <div className="verificacion-fila">
            <span>Fecha de firma</span>
            <span>{new Date(documento.fecha_firma).toLocaleString()}</span>
          </div>
          <div className="verificacion-fila">
            <span>Certificado</span>
            <span>{certificado.numero_serie.slice(0, 14)}...</span>
          </div>
          <div className="verificacion-fila">
            <span>Estado certificado</span>
            <span>{certificado.estado}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
