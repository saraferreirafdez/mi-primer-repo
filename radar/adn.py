"""Prefiltro por DNS — plataforma y proveedor de email sin descargar nada.

Basado en el hallazgo de Cowork del 21/09/2026: el DNS dice gratis qué
plataforma de tienda y qué plataforma de email usa un dominio.

  · Shopify sirve los dominios propios de sus clientes desde 23.227.38.0/24.
    Un registro A en ese rango identifica una tienda Shopify sin margen
    de error.
  · Toda plataforma que firma correos en nombre del cliente le obliga a
    publicar su huella en el SPF de la raíz o en un CNAME de firma DKIM.

Es un PREFILTRO, no un censo: da positivos muy fiables, pero una tienda
puede usar Klaviyo sin dominio de envío propio y entonces no deja huella.
Lo que sale marcado es seguro; lo que sale vacío pasa a `detectar.py`,
que sí baja el HTML. Así solo se descarga el HTML de los que hagan falta.

Ventaja sobre la etapa 1 por HTTP: unas 20 consultas por segundo, coste
cero, y funciona en entornos donde la red HTTP está cerrada pero el DNS no.
"""

from __future__ import annotations

import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

import dns.resolver

# Rango desde el que Shopify sirve los dominios propios de sus clientes.
RANGO_SHOPIFY = ipaddress.ip_network("23.227.38.0/24")

# Huellas en SPF (raíz) y en CNAME de firma. Se buscan en minúsculas.
HUELLAS_ESP: dict[str, list[str]] = {
    "klaviyo":        ["klaviyomail.com", "_domainkey.klaviyodns.com", "klaviyo"],
    "mailchimp":      ["servers.mcsv.net", "mailchimp", "mcsv.net", "rsgsv.net"],
    "omnisend":       ["omnisend.com", "spf.omnisend.com"],
    "brevo":          ["spf.sendinblue.com", "sendinblue", "brevo"],
    "activecampaign": ["activecampaign.com", "emsmtp.us", "acemsmtp"],
    "shopify_email":  ["shopifyemail.com", "shops.shopify.com"],
    "connectif":      ["connectif.ai", "connectif"],
    "hubspot":        ["hubspotemail.net", "hs-mail"],
    "salesforce":     ["exacttarget.com", "salesforce.com"],
    "sendgrid":       ["sendgrid.net"],
    "mailgun":        ["mailgun.org"],
}

# Selectores DKIM típicos, para el segundo intento cuando el SPF no dice nada.
SELECTORES = ["klaviyo._domainkey", "k1._domainkey", "k2._domainkey",
              "s1._domainkey", "s2._domainkey", "dkim._domainkey"]

# Plataformas de MARKETING migrables: una migración genera MRR referido y
# gestionado a la vez, que es lo que pide el escalón Silver de Klaviyo.
MIGRABLES = {"mailchimp", "brevo", "activecampaign", "connectif",
             "hubspot", "shopify_email"}

# Correo TRANSACCIONAL (facturas, avisos de envío). NO es marketing: una
# tienda puede usar SendGrid para los recibos y Klaviyo para las campañas.
# Tratarlos como migrables llenaba la lista de falsos positivos — con esta
# huella sola no se sabe nada del marketing, así que van al grupo 2.
TRANSACCIONALES = {"sendgrid", "mailgun", "salesforce"}


@dataclass
class Adn:
    """Lo que el DNS cuenta de un dominio."""

    dominio: str
    ip: str = ""
    plataforma: str = ""
    esp: str = ""
    evidencia: str = ""
    error: str = ""

    @property
    def grupo(self) -> int:
        """1 = migrable (máxima), 2 = sin huella de marketing, 3 = ya en Klaviyo."""
        if self.esp == "klaviyo":
            return 3
        if self.esp in MIGRABLES:
            return 1
        return 2

    @property
    def es_tienda(self) -> bool:
        """Shopify CONFIRMADO por el rango de IP. Un sí aquí es seguro."""
        return self.plataforma == "shopify"

    @property
    def necesita_html(self) -> bool:
        """El DNS no ha podido decidir: hay que bajar la portada.

        Muchas tiendas Shopify están detrás de Cloudflare u otro CDN, que
        oculta la IP de origen. Freshly Cosmetics y TwoThirds son Shopify y
        aquí salen sin confirmar. Por eso un "no confirmado" NO significa
        "no es tienda": significa "pregúntaselo al HTML", que es justo lo
        que hace radar/detectar.py.
        """
        return not self.es_tienda and not self.error

    @property
    def es_candidata(self) -> bool:
        """Sigue en carrera: o es Shopify confirmado, o está sin decidir."""
        return not self.error and (self.es_tienda or self.necesita_html)

    @property
    def estado(self) -> str:
        if self.error:
            return "error"
        if self.es_tienda:
            return "shopify confirmado"
        return "sin confirmar (pasa a HTML)"

    @property
    def nota(self) -> str:
        if self.esp in TRANSACCIONALES:
            return f"{self.esp} es transaccional, no dice nada del marketing"
        return ""


def _resolver() -> dns.resolver.Resolver:
    r = dns.resolver.Resolver()
    r.timeout, r.lifetime = 4.0, 6.0
    return r


def _plataforma(dominio: str, r: dns.resolver.Resolver) -> tuple[str, str]:
    """Devuelve (plataforma, ip) mirando el registro A."""
    for nombre in (dominio, f"www.{dominio}"):
        try:
            respuesta = r.resolve(nombre, "A")
        except Exception:
            continue
        for dato in respuesta:
            ip = str(dato)
            try:
                if ipaddress.ip_address(ip) in RANGO_SHOPIFY:
                    return "shopify", ip
            except ValueError:
                continue
        return "", str(respuesta[0]) if len(respuesta) else ""
    return "", ""


def _buscar_huella(texto: str) -> str:
    texto = texto.lower()
    for esp, senales in HUELLAS_ESP.items():
        if any(s in texto for s in senales):
            return esp
    return ""


def _esp(dominio: str, r: dns.resolver.Resolver) -> tuple[str, str]:
    """Devuelve (esp, evidencia) mirando SPF y después CNAME de firma."""
    # 1. SPF de la raíz: lo declara casi todo el mundo.
    try:
        for dato in r.resolve(dominio, "TXT"):
            texto = b" ".join(dato.strings).decode("utf-8", "ignore")
            if "v=spf1" not in texto.lower():
                continue
            esp = _buscar_huella(texto)
            if esp:
                return esp, f"SPF: {texto[:110]}"
    except Exception:
        pass

    # 2. CNAME de firma DKIM: más específico, delata al proveedor exacto.
    for selector in SELECTORES:
        try:
            for dato in r.resolve(f"{selector}.{dominio}", "CNAME"):
                destino = str(dato.target).rstrip(".")
                esp = _buscar_huella(destino)
                if esp:
                    return esp, f"DKIM {selector} -> {destino[:70]}"
        except Exception:
            continue
    return "", ""


def analizar(dominio: str) -> Adn:
    """Consulta el DNS de un dominio y devuelve lo que revela."""
    dominio = dominio.strip().lower()
    dominio = dominio.replace("https://", "").replace("http://", "")
    dominio = dominio.split("/")[0].replace("www.", "")
    adn = Adn(dominio=dominio)
    if not dominio or "." not in dominio:
        adn.error = "dominio no válido"
        return adn

    r = _resolver()
    try:
        adn.plataforma, adn.ip = _plataforma(dominio, r)
        adn.esp, adn.evidencia = _esp(dominio, r)
    except Exception as e:
        adn.error = f"{type(e).__name__}"[:60]
    if not adn.ip and not adn.esp:
        adn.error = adn.error or "sin respuesta DNS"
    return adn


def analizar_lote(dominios: Iterable[str], hilos: int = 40) -> Iterator[Adn]:
    """Analiza muchos dominios en paralelo. Unos 20 por segundo."""
    dominios = list(dominios)
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        futuros = {pool.submit(analizar, d): d for d in dominios}
        for futuro in as_completed(futuros):
            try:
                yield futuro.result()
            except Exception as e:
                yield Adn(dominio=futuros[futuro], error=str(e)[:60])
