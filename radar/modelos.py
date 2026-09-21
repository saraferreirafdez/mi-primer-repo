"""Estructuras de datos compartidas por todas las etapas del robot."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


def ahora() -> str:
    """Marca temporal en UTC ISO-8601. Todo dato del robot lleva fecha."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Tienda:
    """Una tienda candidata, tal y como entra en el embudo."""

    url: str
    nombre: str = ""
    ciudad: str = ""
    email: str = ""
    telefono: str = ""
    instagram: str = ""

    def dominio(self) -> str:
        from urllib.parse import urlparse

        neto = self.url if "//" in self.url else f"https://{self.url}"
        return urlparse(neto).netloc.replace("www.", "")


@dataclass
class Deteccion:
    """Resultado de la etapa 1: qué tecnología lleva la tienda puesta."""

    url: str
    detectado_en: str = field(default_factory=ahora)
    plataforma: str = ""              # shopify, woocommerce, prestashop...
    esp: str = ""                     # klaviyo, mailchimp, omnisend, brevo...
    esp_secundarios: list[str] = field(default_factory=list)
    captura_email: bool = False       # ¿hay formulario de suscripción?
    error: str = ""

    @property
    def prioridad(self) -> str:
        """Prioridad comercial de esta tienda.

        Deriva del requisito de Klaviyo Silver verificado el 21/09/2026:
        hacen falta 250 $ de MRR REFERIDO *y* 250 $ de MRR GESTIONADO.
        Adoptar una cuenta que ya paga Klaviyo solo genera gestionado;
        migrar una de Mailchimp genera las dos a la vez. Por eso una
        tienda con Mailchimp vale mas que una que ya tiene Klaviyo.
        """
        if self.error:
            return "error"
        if self.esp in ("mailchimp", "brevo", "activecampaign", "drip"):
            return "maxima"       # migrable -> referido + gestionado
        if not self.esp:
            return "media"        # sin nada -> venta mas larga pero migrable
        if self.esp == "klaviyo":
            return "baja"         # ya en Klaviyo -> solo gestionado
        return "media"

    def como_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["prioridad"] = self.prioridad
        return d


@dataclass
class CorreoRecibido:
    """Un email capturado en el buzon durante la escucha."""

    recibido_en: str
    asunto: str
    remitente: str
    horas_desde_abandono: float
    menciona_producto: bool = False
    menciona_descuento: bool = False
    tipo: str = "desconocido"   # bienvenida, carrito, promocional


@dataclass
class Sonda:
    """Resultado de la etapa 2: que hizo el robot dentro de la tienda."""

    url: str
    alias: str                          # email unico usado en esta sonda
    lanzada_en: str = field(default_factory=ahora)
    producto_usado: str = ""
    suscrito: bool = False
    carrito_alcanzado: bool = False
    checkout_alcanzado: bool = False
    email_introducido: bool = False
    capturas: list[str] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def valida(self) -> bool:
        """Una sonda solo sirve si el robot llego a dejar el email."""
        return self.email_introducido and not self.error


@dataclass
class Auditoria:
    """El expediente completo de una tienda. Lo que alimenta el informe."""

    tienda: Tienda
    deteccion: Deteccion | None = None
    sonda: Sonda | None = None
    correos: list[CorreoRecibido] = field(default_factory=list)
    puntuacion: int = 0
    hallazgos: list[str] = field(default_factory=list)
    euros_perdidos_mes: float = 0.0
