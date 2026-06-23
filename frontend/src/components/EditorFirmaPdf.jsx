import { useState, useEffect, useRef, useCallback } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const ANCHO_SELLO_PDF = 200;
const ALTO_SELLO_PDF = 70;

/**
 * Editor visual: muestra el PDF página por página, el usuario hace clic
 * donde quiere su firma, y devolvemos las coordenadas en el sistema de
 * coordenadas PDF real (origen abajo-izquierda, en puntos), no en píxeles
 * de pantalla — por eso hay que invertir el eje Y al traducir el clic.
 *
 * Recibe `bytesPdf` como ArrayBuffer (no una blob URL) porque es más
 * robusto: pdf.js lo carga con el parámetro `data`, sin depender de timing
 * de creación/revocación de Object URLs del navegador.
 */
export default function EditorFirmaPdf({ bytesPdf, infoPdf, onConfirmar, onCancelar }) {
  const canvasRef = useRef(null);
  const [paginaActual, setPaginaActual] = useState(1);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState(null);
  const [posicion, setPosicion] = useState(null);
  const [escala, setEscala] = useState(1);
  const [dimensionesCanvas, setDimensionesCanvas] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!bytesPdf) return;

    let activo = true;
    const copiaBytes = bytesPdf.slice(0);

    (async () => {
      try {
        const doc = await pdfjsLib.getDocument({ data: copiaBytes }).promise;
        if (activo) {
          setPdfDoc(doc);
          setCargando(false);
        }
      } catch (err) {
        console.error("Error cargando el PDF en el editor:", err);
        if (activo) {
          setErrorCarga("No se pudo leer el documento PDF. Intenta subirlo de nuevo.");
          setCargando(false);
        }
      }
    })();

    return () => { activo = false; };
  }, [bytesPdf]);

  const renderizarPagina = useCallback(async (numeroPagina) => {
    if (!pdfDoc) return;
    const page = await pdfDoc.getPage(numeroPagina);
    const viewport = page.getViewport({ scale: 1 });

    const escalaCalculada = Math.min(620 / viewport.width, 1.4);
    const viewportEscalado = page.getViewport({ scale: escalaCalculada });

    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    canvas.width = viewportEscalado.width;
    canvas.height = viewportEscalado.height;

    setEscala(escalaCalculada);
    setDimensionesCanvas({ width: viewportEscalado.width, height: viewportEscalado.height });
    setPosicion(null);

    await page.render({ canvasContext: context, viewport: viewportEscalado }).promise;
  }, [pdfDoc]);

  useEffect(() => {
    if (!pdfDoc) return;
    renderizarPagina(paginaActual);
  }, [pdfDoc, paginaActual, renderizarPagina]);

  function handleClickCanvas(e) {
    const rect = canvasRef.current.getBoundingClientRect();
    const xPantalla = e.clientX - rect.left;
    const yPantalla = e.clientY - rect.top;

    const infoPagina = infoPdf.paginas.find((p) => p.numero === paginaActual);
    const xPdf = xPantalla / escala;
    const yPdf = infoPagina.alto - (yPantalla / escala) - ALTO_SELLO_PDF;

    setPosicion({ xPantalla, yPantalla, xPdf: Math.max(0, xPdf), yPdf: Math.max(0, yPdf) });
  }

  function handleConfirmar() {
    if (!posicion) return;
    onConfirmar({ pagina: paginaActual, x: posicion.xPdf, y: posicion.yPdf });
  }

  const anchoMarcadorPantalla = ANCHO_SELLO_PDF * escala;
  const altoMarcadorPantalla = ALTO_SELLO_PDF * escala;

  return (
    <div className="editor-firma-overlay">
      <div className="editor-firma-modal">
        <div className="editor-firma-header">
          <div>
            <h3>Coloca tu firma digital</h3>
            <p>Haz clic en el documento donde quieres que aparezca el sello de firma</p>
          </div>
          <button className="btn-cerrar-modal" onClick={onCancelar}>✕</button>
        </div>

        <div className="editor-firma-canvas-wrap">
          {!bytesPdf || errorCarga ? (
            <div className="spinner-cargando-pdf">
              <p className="error-text">{errorCarga || "No se recibieron los datos del documento."}</p>
            </div>
          ) : cargando ? (
            <div className="spinner-cargando-pdf">
              <div className="spinner-ring" />
              Cargando documento...
            </div>
          ) : (
            <div className="editor-firma-canvas-container" style={dimensionesCanvas}>
              <canvas ref={canvasRef} onClick={handleClickCanvas} />
              {posicion && (
                <div
                  className="marcador-firma"
                  style={{
                    left: posicion.xPantalla,
                    top: posicion.yPantalla - altoMarcadorPantalla,
                    width: anchoMarcadorPantalla,
                    height: altoMarcadorPantalla,
                  }}
                >
                  <span className="marcador-firma-etiqueta">Tu firma aquí</span>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="editor-firma-footer">
          <div className="paginador">
            <button type="button" disabled={paginaActual <= 1} onClick={() => setPaginaActual((p) => p - 1)}>
              ← Anterior
            </button>
            Página {paginaActual} de {infoPdf.num_paginas}
            <button type="button" disabled={paginaActual >= infoPdf.num_paginas} onClick={() => setPaginaActual((p) => p + 1)}>
              Siguiente →
            </button>
          </div>

          <div className="acciones-derecha">
            <button type="button" className="btn-secondary" onClick={onCancelar}>Cancelar</button>
            <button type="button" className="btn-confirmar-firma" disabled={!posicion} onClick={handleConfirmar}>
              Confirmar posición y firmar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
