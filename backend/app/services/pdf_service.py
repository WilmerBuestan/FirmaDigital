"""
Servicio de Firma Visual sobre PDF + Código QR.

Esto es la capa "estética/verificable" del proyecto: convierte una firma
digital matemática (RSA, invisible) en un sello visual sobre el documento,
similar a lo que hacen plataformas como DocuSign o Firmadigital.gob.ec.

El QR codifica una URL de verificación pública: cualquiera que lo escanee
puede ver si el documento es auténtico, quién lo firmó y cuándo — sin
necesitar cuenta ni acceso al sistema.
"""
import io
import qrcode
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def generar_qr_bytes(data_url: str) -> bytes:
    """Genera una imagen PNG (en bytes) de un código QR para la URL dada."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def obtener_info_paginas(ruta_pdf: str) -> list[dict]:
    """Devuelve ancho/alto (en puntos PDF) de cada página, para que el
    editor visual del frontend pueda dibujar el PDF a escala correcta."""
    reader = PdfReader(ruta_pdf)
    paginas = []
    for i, page in enumerate(reader.pages):
        box = page.mediabox
        paginas.append({
            "numero": i + 1,
            "ancho": float(box.width),
            "alto": float(box.height),
        })
    return paginas


def estampar_firma_visual(
    ruta_pdf_original: str,
    ruta_pdf_salida: str,
    pagina: int,
    x: float,
    y: float,
    nombre_firmante: str,
    fecha_firma_str: str,
    numero_serie_certificado: str,
    url_verificacion: str,
) -> None:
    """
    Crea una nueva versión del PDF con un sello de firma visual estampado
    en la página/coordenadas elegidas por el usuario en el editor visual.

    El sello incluye: nombre del firmante, fecha, serie del certificado,
    y un código QR que enlaza a la verificación pública del documento.

    `x`, `y` llegan en puntos PDF con origen abajo-izquierda (estándar PDF),
    que es lo que el frontend debe calcular a partir del clic del usuario.
    """
    reader = PdfReader(ruta_pdf_original)
    writer = PdfWriter()

    ancho_sello = 200
    alto_sello = 70
    qr_size = 60

    qr_bytes = generar_qr_bytes(url_verificacion)
    qr_image = ImageReader(io.BytesIO(qr_bytes))

    for i, page in enumerate(reader.pages):
        numero_pagina_actual = i + 1
        if numero_pagina_actual == pagina:
            box = page.mediabox
            overlay_buffer = io.BytesIO()
            c = canvas.Canvas(overlay_buffer, pagesize=(float(box.width), float(box.height)))

            # Fondo del sello: rectángulo con borde, estilo "sello notarial"
            c.setFillColorRGB(0.93, 0.96, 1.0)
            c.setStrokeColorRGB(0.16, 0.42, 0.86)
            c.setLineWidth(1.2)
            c.roundRect(x, y, ancho_sello, alto_sello, 6, fill=1, stroke=1)

            # QR a la izquierda del sello
            c.drawImage(qr_image, x + 6, y + 5, width=qr_size, height=qr_size)

            # Texto a la derecha del QR
            texto_x = x + qr_size + 12
            c.setFillColorRGB(0.07, 0.09, 0.15)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(texto_x, y + alto_sello - 14, "FIRMADO DIGITALMENTE")
            c.setFont("Helvetica", 7)
            c.drawString(texto_x, y + alto_sello - 26, nombre_firmante[:26])
            c.drawString(texto_x, y + alto_sello - 36, fecha_firma_str)
            c.drawString(texto_x, y + alto_sello - 46, f"Cert: {numero_serie_certificado[:14]}...")
            c.setFont("Helvetica-Oblique", 6)
            c.drawString(texto_x, y + 6, "Escanee el QR para verificar")

            c.save()
            overlay_buffer.seek(0)

            overlay_reader = PdfReader(overlay_buffer)
            page.merge_page(overlay_reader.pages[0])

        writer.add_page(page)

    with open(ruta_pdf_salida, "wb") as f:
        writer.write(f)
