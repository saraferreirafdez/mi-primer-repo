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

# Tokens de verificación de propiedad publicados como TXT en la RAÍZ.
# Hallazgo de Cowork (21/09/2026), y es la señal más temprana que existe:
# el cliente publica este TXT al CONECTAR la plataforma, mientras que la
# firma DKIM solo aparece después y solo si llega a configurar envío con
# marca propia, cosa que muchos no hacen nunca. Mirar la raíz ve más.
TOKENS_RAIZ: dict[str, list[str]] = {
    "klaviyo":        ["klaviyo-site-verification"],
    "brevo":          ["brevo-code", "sendinblue-code"],
    "omnisend":       ["omnisend-site-verification", "omnisend-verification"],
    "activecampaign": ["activecampaign-site-verification"],
    "hubspot":        ["hubspot-developer-verification"],
}

# MAILCHIMP NO PUBLICA TOKEN DE RAÍZ. Confirmado por CoWork el 21/09/2026
# volcando los TXT completos de freshlycosmetics.com y twothirds.com (9 y 6
# registros, TC=false, sin truncar): en los dos está el include del SPF
# servers.mcsv.net y en ninguno hay token de Mailchimp. Su detección se
# queda en SPF + DKIM, y por eso NO aparece en la tabla de arriba.
# Brevo y Omnisend siguen por analogía: sin evidencia en ningún sentido.

# Verificado empíricamente el 21/09/2026 sobre los cinco dominios que nombró
# Cowork: los cinco publican klaviyo-site-verification en la raíz.
# Para Mailchimp, Omnisend y Brevo los prefijos de arriba están puestos por
# analogía y NO confirmados: si alguno no existe, simplemente nunca coincide
# y la detección cae en el DKIM de siempre. No hace daño.

# Otra señal útil encontrada de paso: shopify-verification-code en la raíz
# confirma tienda Shopify aunque haya un CDN ocultando la IP de origen.
TOKEN_SHOPIFY = "shopify-verification-code"

# Segunda señal de Shopify, aportada por CoWork: twothirds.com no lleva el
# token pero sí este include en el SPF. Rescata dominios que el token no cubre.
INCLUDE_SHOPIFY = "shops.shopify.com"

# Selectores DKIM típicos, para el segundo intento cuando el SPF no dice nada.
#
# Los de los ESP van primero. Detrás van los de los PROVEEDORES DE CORREO,
# que no son lo mismo: IONOS o Google alojan el buzón, no hacen campañas.
#
# Los de IONOS llevan guion («s1-ionos», no «s1») y por eso se escapaban. Me
# lo dijo CoWork por escrito el 22/09 en el doc 19 del buzón, después de que
# le pasara a él, y no lo metí. El 25/09 volví a tropezar en la misma
# piedra: di por hecho que sorasystems.es no tenía DKIM porque probé 22
# selectores y ninguno era el bueno, y monté un aviso urgente sobre eso.
# Sí lo tenía, en s1-ionos y s2-ionos, desde el día 22.
SELECTORES = ["klaviyo._domainkey", "k1._domainkey", "k2._domainkey",
              "s1._domainkey", "s2._domainkey", "dkim._domainkey",
              "s1-ionos._domainkey", "s2-ionos._domainkey",
              "google._domainkey", "selector1._domainkey",
              "selector2._domainkey", "default._domainkey"]

# Quién aloja el buzón. NO es un ESP: encontrar esto significa que la tienda
# no tiene herramienta de marketing, que es justo la señal que buscamos.
# Antes devolvíamos vacío y no se distinguía «no hay ESP» de «no hemos
# encontrado nada», que son cosas distintas a la hora de fiarse del dato.
HUELLAS_CORREO: dict[str, list[str]] = {
    "IONOS":     ["dkim.ionos.com", "ionos", "kundenserver", "1und1"],
    "Google":    ["google.com", "googlemail"],
    "Microsoft": ["outlook.com", "microsoft"],
    "OVH":       ["ovh.net", "ovh.com"],
    "Zoho":      ["zoho.com", "zohomail"],
}

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
    shopify_por_token: bool = False
    pendiente: bool = False   # timeout de DNS: hay que reintentar, no descartar

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
        """Shopify confirmado, por rango de IP o por el TXT de verificación.

        El token rescata a las tiendas que están tras un CDN y cuya IP de
        origen no se ve.
        """
        return self.plataforma == "shopify" or self.shopify_por_token

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
        if self.pendiente:
            return "pendiente (reintentar)"
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



def _buscar_correo(texto: str) -> str:
    """Quién aloja el buzón, si lo que aparece no es un ESP."""
    t = texto.lower()
    for proveedor, huellas in HUELLAS_CORREO.items():
        if any(h in t for h in huellas):
            return proveedor
    return ""

def _esp(dominio: str, r: dns.resolver.Resolver) -> tuple[str, str, bool]:
    """Devuelve (esp, evidencia, shopify_por_token).

    Mira, por este orden: tokens de verificación en la raíz, SPF y CNAME de
    firma DKIM. Los tokens van primero porque son la señal más temprana.
    """
    esp_spf = evidencia_spf = ""
    shopify_token = False

    # 1. Una sola consulta TXT a la raíz sirve para las dos cosas.
    try:
        for dato in r.resolve(dominio, "TXT"):
            texto = b" ".join(dato.strings).decode("utf-8", "ignore")
            bajo = texto.lower()

            if bajo.startswith(TOKEN_SHOPIFY) or INCLUDE_SHOPIFY in bajo:
                shopify_token = True
                if bajo.startswith(TOKEN_SHOPIFY):
                    continue

            for esp, prefijos in TOKENS_RAIZ.items():
                if any(bajo.startswith(p) for p in prefijos):
                    # El token es la señal más fiable: se devuelve ya.
                    return esp, f"TXT raíz: {texto[:80]}", shopify_token

            if "v=spf1" in bajo and not esp_spf:
                encontrado = _buscar_huella(texto)
                if encontrado:
                    esp_spf, evidencia_spf = encontrado, f"SPF: {texto[:100]}"
    except Exception:
        pass

    if esp_spf:
        return esp_spf, evidencia_spf, shopify_token

    # 2. CNAME de firma DKIM: más específico, delata al proveedor exacto.
    #    Si lo que aparece es el proveedor del buzón y no un ESP, se anota
    #    igualmente: «su correo está en IONOS y no hay herramienta de
    #    marketing» es un dato, y «no encontré nada» es no saber.
    correo = ""
    for selector in SELECTORES:
        try:
            for dato in r.resolve(f"{selector}.{dominio}", "CNAME"):
                destino = str(dato.target).rstrip(".")
                esp = _buscar_huella(destino)
                if esp:
                    return esp, f"DKIM {selector} -> {destino[:70]}", shopify_token
                if not correo:
                    correo = _buscar_correo(destino) or ""
        except Exception:
            continue
    if correo:
        return "", f"sin ESP; el correo lo aloja {correo}", shopify_token
    return "", "", shopify_token


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
        adn.esp, adn.evidencia, adn.shopify_por_token = _esp(dominio, r)
        if adn.shopify_por_token and not adn.plataforma:
            adn.plataforma = "shopify"
    except Exception as e:
        adn.error = f"{type(e).__name__}"[:60]
    if not adn.ip and not adn.esp:
        adn.error = adn.error or "sin respuesta DNS"
    # Un timeout NO es un descarte. Suele darse en dominios con muchos TXT,
    # que es señal de marca activa: justamente los que no hay que perder.
    # Van a un fichero de pendientes para reintentarlos por otra vía.
    adn.pendiente = "Timeout" in adn.error or "sin respuesta" in adn.error
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
