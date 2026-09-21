"""Etapa 4a — puntuar la tienda y estimar el dinero que deja sobre la mesa.

La puntuación es sobre 100 y está pensada para ser defendible delante del
cliente: cada punto sale de algo que el robot ha observado, no de una opinión.

Las estimaciones económicas son ESTIMACIONES y el informe las presenta como
tales, con los supuestos impresos. Un número inflado se descubre en la primera
reunión y se lleva por delante la credibilidad de todo lo demás.
"""

from __future__ import annotations

from dataclasses import dataclass

from .modelos import Auditoria, CorreoRecibido

# --- Supuestos del sector. Se imprimen siempre en el informe. --------------
TASA_ABANDONO = 0.70          # carritos creados que no se completan
RECUPERACION_BUENA = 0.08     # lo que recupera una secuencia bien montada
RECUPERACION_MINIMA = 0.01    # lo que recupera una tienda sin nada

# --- Pesos de la puntuación ------------------------------------------------
PESOS = {
    "captura_email": 10,
    "esp_instalado": 10,
    "bienvenida": 20,
    "carrito_primero": 30,
    "carrito_secuencia": 15,
    "personalizacion": 10,
    "incentivo": 5,
}


@dataclass
class Estimacion:
    """Cuánto dinero se está dejando, y con qué cuentas se ha calculado."""

    visitas_mes: int
    tasa_conversion: float
    ticket_medio: float
    pedidos_mes: float
    carritos_abandonados: float
    recuperacion_actual: float
    euros_recuperados_hoy: float
    euros_recuperables: float
    euros_perdidos_mes: float

    @property
    def euros_perdidos_ano(self) -> float:
        return self.euros_perdidos_mes * 12


def _primer_correo(correos: list[CorreoRecibido], tipo: str) -> CorreoRecibido | None:
    candidatos = [c for c in correos if c.tipo == tipo]
    return candidatos[0] if candidatos else None


def puntuar(auditoria: Auditoria) -> tuple[int, list[str]]:
    """Devuelve (puntuación sobre 100, hallazgos en lenguaje llano)."""
    puntos = 0
    hallazgos: list[str] = []
    deteccion = auditoria.deteccion
    correos = auditoria.correos

    # --- Lo que se ve sin esperar ------------------------------------------
    if deteccion and deteccion.captura_email:
        puntos += PESOS["captura_email"]
    else:
        hallazgos.append(
            "No hay ningún formulario visible para captar el correo de quien "
            "entra. Cada visitante que se va queda perdido para siempre."
        )

    if deteccion and deteccion.esp:
        puntos += PESOS["esp_instalado"]
        if deteccion.esp == "mailchimp":
            hallazgos.append(
                "La tienda usa Mailchimp. Para una tienda online se queda corto "
                "en automatizaciones de carrito y en atribución: no permite saber "
                "cuánto dinero ha traído cada correo."
            )
    else:
        hallazgos.append(
            "No hay ninguna plataforma de email marketing instalada. Sin ella no "
            "existe forma de recuperar un carrito abandonado."
        )

    # --- Bienvenida ---------------------------------------------------------
    bienvenida = _primer_correo(correos, "bienvenida")
    if bienvenida:
        if bienvenida.horas_desde_abandono <= 1:
            puntos += PESOS["bienvenida"]
        else:
            puntos += PESOS["bienvenida"] // 2
            hallazgos.append(
                f"El correo de bienvenida tarda "
                f"{bienvenida.horas_desde_abandono:.1f} horas en llegar. El momento "
                "de máxima atención son los primeros minutos."
            )
    else:
        hallazgos.append(
            "Al suscribirse no llega ningún correo de bienvenida. Es la secuencia "
            "con más apertura de todo el email marketing, y aquí no existe."
        )

    # --- Carrito abandonado, que es el corazón del informe ------------------
    carritos = [c for c in correos if c.tipo == "carrito"]
    if carritos:
        primero = carritos[0]
        if primero.horas_desde_abandono <= 4:
            puntos += PESOS["carrito_primero"]
        elif primero.horas_desde_abandono <= 24:
            puntos += int(PESOS["carrito_primero"] * 0.6)
            hallazgos.append(
                f"El primer aviso de carrito llega a las "
                f"{primero.horas_desde_abandono:.1f} horas. La ventana buena son "
                "las primeras 1 a 4 horas, mientras la intención de compra sigue viva."
            )
        else:
            puntos += int(PESOS["carrito_primero"] * 0.3)
            hallazgos.append(
                f"El primer aviso de carrito tarda más de un día "
                f"({primero.horas_desde_abandono:.1f} horas). A esas alturas la "
                "mayoría ya ha comprado en otro sitio o ha perdido el interés."
            )

        if len(carritos) >= 2:
            puntos += PESOS["carrito_secuencia"]
        else:
            hallazgos.append(
                "Solo se envía UN correo de carrito abandonado. Las secuencias que "
                "funcionan tienen tres: recordatorio, prueba social e incentivo."
            )

        if any(c.menciona_producto for c in carritos):
            puntos += PESOS["personalizacion"]
        else:
            hallazgos.append(
                "Los correos de carrito no mencionan el producto concreto que se "
                "dejó. Un recordatorio genérico rinde mucho menos que uno con la "
                "foto y el nombre de lo que la persona estaba mirando."
            )

        if any(c.menciona_descuento for c in carritos):
            puntos += PESOS["incentivo"]
    else:
        hallazgos.append(
            "NO LLEGA NINGÚN CORREO DE CARRITO ABANDONADO. Es el hallazgo más caro "
            "del informe: siete de cada diez carritos se abandonan, y aquí no se "
            "intenta recuperar ninguno."
        )

    return min(puntos, 100), hallazgos


def estimar(
    puntuacion: int,
    visitas_mes: int = 10_000,
    tasa_conversion: float = 0.015,
    ticket_medio: float = 45.0,
) -> Estimacion:
    """Estima el dinero perdido al mes por no recuperar carritos.

    Si no se conocen las cifras reales de la tienda se usan medias del sector,
    y el informe lo dice con todas las letras. Cuando el cliente da sus números
    reales, la estimación se recalcula y gana muchísima fuerza comercial.
    """
    pedidos = visitas_mes * tasa_conversion
    carritos_creados = pedidos / (1 - TASA_ABANDONO) if TASA_ABANDONO < 1 else pedidos
    abandonados = carritos_creados - pedidos

    # La recuperación actual se deduce de la puntuación: una tienda con 0 no
    # recupera casi nada, una con 100 está cerca del máximo del sector.
    proporcion = puntuacion / 100
    recuperacion_actual = (
        RECUPERACION_MINIMA + (RECUPERACION_BUENA - RECUPERACION_MINIMA) * proporcion
    )

    recuperados_hoy = abandonados * recuperacion_actual * ticket_medio
    recuperables = abandonados * RECUPERACION_BUENA * ticket_medio

    return Estimacion(
        visitas_mes=visitas_mes,
        tasa_conversion=tasa_conversion,
        ticket_medio=ticket_medio,
        pedidos_mes=round(pedidos, 1),
        carritos_abandonados=round(abandonados, 1),
        recuperacion_actual=round(recuperacion_actual, 4),
        euros_recuperados_hoy=round(recuperados_hoy, 2),
        euros_recuperables=round(recuperables, 2),
        euros_perdidos_mes=round(max(recuperables - recuperados_hoy, 0), 2),
    )
