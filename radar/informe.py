"""Etapa 4b — el informe en PDF que se le manda a la tienda.

Dos páginas, marca Sora Systems (colores vivos, fondo claro, tono directo
y de tú). Es el documento que abre la conversación de venta, así que:

  - el número grande va arriba y es el dinero, no la puntuación
  - los supuestos del cálculo se imprimen siempre, sin letra pequeña
  - no se promete nada que el robot no haya observado
"""

from __future__ import annotations

from datetime import date

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas as rl_canvas

from .modelos import Auditoria
from .rubrica import Estimacion, RECUPERACION_BUENA, TASA_ABANDONO

# --- Paleta Sora Systems: viva, cálida, fondo claro ------------------------
CORAL = HexColor("#FF6B4A")
TURQUESA = HexColor("#2EC4B6")
AMARILLO = HexColor("#FFD23F")
TINTA = HexColor("#1A2634")
GRIS = HexColor("#6B7A88")
FONDO = HexColor("#FFFDF9")
CREMA = HexColor("#FFF4EE")
HUESO = HexColor("#F4F1EC")

ANCHO, ALTO = A4
MARGEN = 45
ANCHO_UTIL = ANCHO - 2 * MARGEN

# Las tres secuencias que vende Sora. Se imprimen en la página 2 como
# "lo que deberías tener", que es lo que convierte el diagnóstico en oferta.
SECUENCIAS = [
    ("Carrito abandonado",
     "Tres correos escalonados a las 1, 24 y 72 horas, con la foto y el nombre "
     "de lo que se dejó. Es la secuencia que más dinero recupera, con diferencia."),
    ("Bienvenida",
     "Se dispara en cuanto alguien deja su correo. Es la que más se abre de "
     "todas, y es donde se convierte a un curioso en primer pedido."),
    ("Clientes que no vuelven",
     "Detecta a quien compró y lleva meses sin aparecer, y le da una razón "
     "concreta para volver. Vender a quien ya te compró cuesta mucho menos."),
]


def _parrafo(c, texto, x, y, ancho, tamano=10, interlineado=14,
             fuente="Helvetica", color=TINTA):
    """Escribe texto ajustado al ancho. Devuelve la y después del bloque."""
    c.setFont(fuente, tamano)
    c.setFillColor(color)
    for linea in simpleSplit(texto, fuente, tamano, ancho):
        c.drawString(x, y, linea)
        y -= interlineado
    return y


def _euros(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def _cabecera(c, derecha: str):
    c.setFillColor(FONDO)
    c.rect(0, 0, ANCHO, ALTO, fill=1, stroke=0)
    c.setFillColor(CORAL)
    c.rect(0, ALTO - 8, ANCHO, 8, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(TINTA)
    c.drawString(MARGEN, ALTO - 48, "SORA SYSTEMS")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(GRIS)
    c.drawRightString(ANCHO - MARGEN, ALTO - 48, derecha)


def _pie(c, pagina: int):
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS)
    c.drawString(MARGEN, 30, "sorasystems.es")
    c.drawRightString(ANCHO - MARGEN, 30, f"Página {pagina} de 2")


def _semaforo(puntuacion: int):
    if puntuacion >= 70:
        return TURQUESA, "BIEN MONTADO"
    if puntuacion >= 40:
        return AMARILLO, "A MEDIAS"
    return CORAL, "SIN MONTAR"


def generar(
    auditoria: Auditoria,
    estimacion: Estimacion,
    ruta: str,
    cifras_reales: bool = False,
    mencionar_black_friday: bool = True,
) -> str:
    """Escribe el PDF de dos páginas y devuelve la ruta."""
    tienda = auditoria.tienda
    nombre = tienda.nombre or tienda.dominio()
    c = rl_canvas.Canvas(ruta, pagesize=A4)
    c.setTitle(f"Revisión de recuperación de ventas — {nombre}")
    c.setAuthor("Sora Systems")

    # ══════════════════════ PÁGINA 1 ══════════════════════
    _cabecera(c, date.today().strftime("%d/%m/%Y"))
    y = ALTO - 92

    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(TINTA)
    c.drawString(MARGEN, y, "Qué le pasa a tu carrito")
    y -= 26
    c.setFont("Helvetica", 11.5)
    c.setFillColor(GRIS)
    c.drawString(MARGEN, y, f"Revisión de {nombre}")
    y -= 30

    # --- El número grande: el dinero ---------------------------------------
    alto_caja = 106
    c.setFillColor(CREMA)
    c.roundRect(MARGEN, y - alto_caja, ANCHO_UTIL, alto_caja, 10, fill=1, stroke=0)
    c.setFillColor(CORAL)
    c.rect(MARGEN, y - alto_caja, 6, alto_caja, fill=1, stroke=0)
    c.setFont("Helvetica", 10.5)
    c.setFillColor(GRIS)
    c.drawString(MARGEN + 26, y - 28, "Te estás dejando cada mes, aproximadamente")
    c.setFont("Helvetica-Bold", 38)
    c.setFillColor(CORAL)
    c.drawString(MARGEN + 26, y - 70, f"{_euros(estimacion.euros_perdidos_mes)} €")
    c.setFont("Helvetica", 10.5)
    c.setFillColor(TINTA)
    c.drawString(MARGEN + 26, y - 91,
                 f"Son unos {_euros(estimacion.euros_perdidos_ano)} € al año.")
    y -= alto_caja + 26

    # --- Puntuación ---------------------------------------------------------
    color, etiqueta = _semaforo(auditoria.puntuacion)
    c.setFont("Helvetica-Bold", 11.5)
    c.setFillColor(TINTA)
    c.drawString(MARGEN, y, "Tu sistema de recuperación")
    c.setFont("Helvetica-Bold", 11.5)
    c.setFillColor(color)
    c.drawRightString(ANCHO - MARGEN, y, f"{auditoria.puntuacion}/100 · {etiqueta}")
    y -= 18
    c.setFillColor(HexColor("#EFE9E4"))
    c.roundRect(MARGEN, y - 14, ANCHO_UTIL, 14, 7, fill=1, stroke=0)
    if auditoria.puntuacion > 0:
        c.setFillColor(color)
        c.roundRect(MARGEN, y - 14,
                    max(ANCHO_UTIL * auditoria.puntuacion / 100, 14), 14, 7,
                    fill=1, stroke=0)
    y -= 40

    # --- Qué llegó y qué no -------------------------------------------------
    c.setFont("Helvetica-Bold", 12.5)
    c.setFillColor(TINTA)
    c.drawString(MARGEN, y, "Qué nos llegó tras dejar el carrito")
    y -= 21

    if auditoria.correos:
        for correo in auditoria.correos[:5]:
            c.setFillColor(TURQUESA)
            c.circle(MARGEN + 5, y + 3, 3.5, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 9.5)
            c.setFillColor(TINTA)
            c.drawString(MARGEN + 18, y, f"+{correo.horas_desde_abandono:.1f} h")
            c.setFont("Helvetica", 9.5)
            c.setFillColor(GRIS)
            asunto = correo.asunto[:58] + ("…" if len(correo.asunto) > 58 else "")
            c.drawString(MARGEN + 78, y, f"{asunto}  [{correo.tipo}]")
            y -= 17
        y -= 6
    else:
        c.setFillColor(CORAL)
        c.circle(MARGEN + 5, y + 3, 3.5, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(CORAL)
        c.drawString(MARGEN + 18, y, "Nada. Ni un solo correo en 72 horas.")
        y -= 19
        y = _parrafo(
            c,
            "Dejamos un producto en el carrito con un correo válido y esperamos "
            "tres días. No llegó ningún aviso. Cada persona que hace eso en tu "
            "tienda se va sin que nadie la llame de vuelta.",
            MARGEN + 18, y, ANCHO_UTIL - 18, tamano=10, interlineado=13.5,
        )
        y -= 12

    # --- Hallazgos, ya en la página 1 para que no quede hueco ---------------
    c.setFont("Helvetica-Bold", 12.5)
    c.setFillColor(TINTA)
    c.drawString(MARGEN, y, "Lo que hemos encontrado")
    y -= 22
    for hallazgo in auditoria.hallazgos[:5]:
        if y < 90:
            break
        c.setFillColor(CORAL)
        c.circle(MARGEN + 5, y + 3, 3.5, fill=1, stroke=0)
        y = _parrafo(c, hallazgo, MARGEN + 18, y, ANCHO_UTIL - 18,
                     tamano=10, interlineado=13.5)
        y -= 9

    _pie(c, 1)
    c.showPage()

    # ══════════════════════ PÁGINA 2 ══════════════════════
    _cabecera(c, nombre)
    y = ALTO - 92

    c.setFont("Helvetica-Bold", 21)
    c.setFillColor(TINTA)
    c.drawString(MARGEN, y, "Lo que deberías tener")
    y -= 24
    y = _parrafo(
        c,
        "Son tres secuencias automáticas. Se montan una vez y trabajan solas "
        "cada día, con cada persona que entra en tu tienda.",
        MARGEN, y, ANCHO_UTIL, tamano=10.5, interlineado=14, color=GRIS,
    )
    y -= 16

    for i, (titulo, descripcion) in enumerate(SECUENCIAS, start=1):
        alto_bloque = 66
        c.setFillColor(HUESO)
        c.roundRect(MARGEN, y - alto_bloque, ANCHO_UTIL, alto_bloque, 8,
                    fill=1, stroke=0)
        c.setFillColor(TURQUESA)
        c.rect(MARGEN, y - alto_bloque, 5, alto_bloque, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 11.5)
        c.setFillColor(TINTA)
        c.drawString(MARGEN + 20, y - 22, f"{i}.  {titulo}")
        _parrafo(c, descripcion, MARGEN + 20, y - 39, ANCHO_UTIL - 40,
                 tamano=9.5, interlineado=12.5, color=GRIS)
        y -= alto_bloque + 12

    y -= 6

    # --- Supuestos: honestidad por delante ---------------------------------
    alto_sup = 78
    c.setFillColor(HUESO)
    c.roundRect(MARGEN, y - alto_sup, ANCHO_UTIL, alto_sup, 8, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(GRIS)
    c.drawString(MARGEN + 16, y - 18, "CÓMO HEMOS CALCULADO LA CIFRA")

    if cifras_reales:
        origen = "Hemos usado las cifras reales que nos has dado."
    else:
        origen = (
            f"Aún no tenemos tus cifras, así que hemos usado medias del sector: "
            f"{_euros(estimacion.visitas_mes)} visitas al mes, "
            f"{estimacion.tasa_conversion * 100:.1f} % de conversión y "
            f"{estimacion.ticket_medio:.0f} € de ticket medio."
        )
    _parrafo(
        c,
        f"{origen} Partimos de que se abandonan {TASA_ABANDONO * 100:.0f} de cada "
        f"100 carritos y de que una secuencia bien montada recupera en torno al "
        f"{RECUPERACION_BUENA * 100:.0f} %. Es una estimación, no una promesa: "
        "con tus números reales la afinamos en diez minutos.",
        MARGEN + 16, y - 34, ANCHO_UTIL - 32, tamano=8.5, interlineado=11,
        color=GRIS,
    )
    y -= alto_sup + 20

    # --- Cierre -------------------------------------------------------------
    alto_cierre = 112 if mencionar_black_friday else 90
    base = max(y - alto_cierre, 52)
    c.setFillColor(TINTA)
    c.roundRect(MARGEN, base, ANCHO_UTIL, alto_cierre, 10, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 13.5)
    c.setFillColor(AMARILLO)
    c.drawString(MARGEN + 22, base + alto_cierre - 28, "Esto se arregla en una semana")
    yy = _parrafo(
        c,
        "Montamos las tres secuencias, las dejamos funcionando y te pasamos cada "
        "mes lo que han recuperado, en euros. Sin permanencia.",
        MARGEN + 22, base + alto_cierre - 50, ANCHO_UTIL - 44,
        tamano=10, interlineado=13.5, color=white,
    )
    if mencionar_black_friday:
        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(AMARILLO)
        c.drawString(
            MARGEN + 22, yy - 4,
            "El Black Friday es el 27 de noviembre. Lo que montes ahora lo cobras ahí.",
        )

    _pie(c, 2)
    c.save()
    return ruta
