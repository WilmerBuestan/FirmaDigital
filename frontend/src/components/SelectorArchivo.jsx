import { useRef, useState } from "react";

/**
 * Selector de archivos amigable: zona de arrastrar-y-soltar + botón,
 * en vez de un <input type="file"> plano (que se ve como texto crudo).
 */
export default function SelectorArchivo({ onFileSelected, archivoActual, etiqueta, accept }) {
  const inputRef = useRef(null);
  const [arrastrando, setArrastrando] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setArrastrando(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onFileSelected(file);
  }

  function handleChange(e) {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  }

  return (
    <div
      className={`selector-archivo ${arrastrando ? "selector-archivo-activo" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setArrastrando(true); }}
      onDragLeave={() => setArrastrando(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        style={{ display: "none" }}
      />
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 3v12m0 0l-4-4m4 4l4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="selector-archivo-texto">
        {archivoActual ? (
          <strong>{archivoActual.name}</strong>
        ) : (
          <>
            <strong>{etiqueta || "Haz clic para elegir un archivo"}</strong>
            <span>o arrástralo aquí</span>
          </>
        )}
      </div>
    </div>
  );
}
