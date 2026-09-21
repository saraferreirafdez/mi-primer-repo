"""Etapa 3 — escuchar el buzon y atribuir cada correo a su sonda.

Funciona con cualquier buzon IMAP que admita direcciones con subetiqueta
(alias+algo@dominio). Gmail, Fastmail, Zoho y la mayoria lo hacen.

El alias es la clave de todo: cada tienda recibe uno distinto, asi que
cuando llega un correo se sabe exactamente quien lo manda y cuanto ha
tardado desde el abandono.
"""

from __future__ import annotations

import email
import imaplib
import os
import re
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from .modelos import CorreoRecibido

PALABRAS_CARRITO = [
    "carrito", "cesta", "olvidaste", "te dejaste", "sigue ahi", "sigue ahí",
    "cart", "abandoned", "forgot", "left something", "completa tu compra",
    "finaliza tu compra", "vuelve a por",
]
PALABRAS_BIENVENIDA = [
    "bienvenid", "welcome", "gracias por suscribirte", "ya eres parte",
    "tu descuento", "aqui tienes tu", "aquí tienes tu", "confirma tu",
]
PALABRAS_DESCUENTO = [
    "descuento", "% off", "cupon", "cupón", "code", "codigo", "código",
    "rebaja", "oferta", "gratis", "envio gratis", "envío gratis",
]


def _texto(cabecera: str | None) -> str:
    if not cabecera:
        return ""
    try:
        return str(make_header(decode_header(cabecera)))
    except Exception:
        return cabecera


def _cuerpo(mensaje: email.message.Message) -> str:
    partes: list[str] = []
    if mensaje.is_multipart():
        for parte in mensaje.walk():
            if parte.get_content_type() in ("text/plain", "text/html"):
                try:
                    carga = parte.get_payload(decode=True) or b""
                    partes.append(carga.decode("utf-8", errors="ignore"))
                except Exception:
                    continue
    else:
        try:
            carga = mensaje.get_payload(decode=True) or b""
            partes.append(carga.decode("utf-8", errors="ignore"))
        except Exception:
            pass
    return " ".join(partes).lower()


def _clasificar(asunto: str, cuerpo: str) -> str:
    texto = f"{asunto} {cuerpo}".lower()
    if any(p in texto for p in PALABRAS_CARRITO):
        return "carrito"
    if any(p in texto for p in PALABRAS_BIENVENIDA):
        return "bienvenida"
    return "promocional"


def recoger(
    alias: str,
    abandonado_en: datetime,
    servidor: str | None = None,
    usuario: str | None = None,
    clave: str | None = None,
    carpeta: str | None = None,
) -> list[CorreoRecibido]:
    """Devuelve todos los correos recibidos en ese alias desde el abandono.

    Las credenciales se leen del entorno si no se pasan:
      RADAR_IMAP_SERVIDOR, RADAR_IMAP_USUARIO, RADAR_IMAP_CLAVE
    Nunca las escribas en el codigo ni las subas al repositorio.
    """
    # La carpeta importa: info@ es la direccion real del negocio, asi que los
    # correos del robot deben caer en una carpeta aparte y no en la bandeja de
    # entrada, donde taparian el correo de clientes de verdad.
    carpeta = carpeta or os.environ.get("RADAR_IMAP_CARPETA", "Auditorias")
    servidor = servidor or os.environ.get("RADAR_IMAP_SERVIDOR", "")
    usuario = usuario or os.environ.get("RADAR_IMAP_USUARIO", "")
    clave = clave or os.environ.get("RADAR_IMAP_CLAVE", "")
    if not all((servidor, usuario, clave)):
        raise RuntimeError(
            "Faltan credenciales IMAP. Define RADAR_IMAP_SERVIDOR, "
            "RADAR_IMAP_USUARIO y RADAR_IMAP_CLAVE en el entorno."
        )

    recogidos: list[CorreoRecibido] = []
    conexion = imaplib.IMAP4_SSL(servidor)
    try:
        conexion.login(usuario, clave)
        conexion.select(carpeta)
        # Se busca por destinatario: el alias identifica la tienda.
        estado, datos = conexion.search(None, f'(TO "{alias}")')
        if estado != "OK":
            return recogidos

        for numero in datos[0].split():
            estado, crudo = conexion.fetch(numero, "(RFC822)")
            if estado != "OK" or not crudo or not crudo[0]:
                continue
            mensaje = email.message_from_bytes(crudo[0][1])

            try:
                fecha = parsedate_to_datetime(mensaje.get("Date"))
            except Exception:
                continue
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)
            if fecha < abandonado_en:
                continue

            asunto = _texto(mensaje.get("Subject"))
            cuerpo = _cuerpo(mensaje)
            horas = (fecha - abandonado_en).total_seconds() / 3600

            recogidos.append(
                CorreoRecibido(
                    recibido_en=fecha.isoformat(timespec="seconds"),
                    asunto=asunto[:200],
                    remitente=_texto(mensaje.get("From"))[:160],
                    horas_desde_abandono=round(horas, 2),
                    menciona_descuento=any(p in cuerpo or p in asunto.lower()
                                           for p in PALABRAS_DESCUENTO),
                    tipo=_clasificar(asunto, cuerpo),
                )
            )
    finally:
        try:
            conexion.logout()
        except Exception:
            pass

    recogidos.sort(key=lambda c: c.horas_desde_abandono)
    return recogidos


def marcar_producto(correos: list[CorreoRecibido], producto: str) -> None:
    """Marca que correos mencionan el producto abandonado (personalizacion)."""
    if not producto:
        return
    # Se queda con las palabras significativas del nombre del producto.
    claves = [p for p in re.split(r"[^\wáéíóúñ]+", producto.lower()) if len(p) > 3]
    if not claves:
        return
    for correo in correos:
        if any(c in correo.asunto.lower() for c in claves):
            correo.menciona_producto = True
