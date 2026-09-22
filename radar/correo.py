"""Redacción del correo de hallazgo.

REGLA QUE NO SE SALTA: el correo solo afirma lo que el robot ha comprobado
DE VERDAD sobre esa tienda concreta. Por eso hay dos plantillas y no una.

  HALLAZGO   Solo se ha mirado el código de la portada. Se puede afirmar
             que no hay herramienta de recuperación instalada. NO se puede
             decir "dejé un carrito y no me llegó nada", porque no se ha
             hecho. Sale sin esperar: sirve para las 102 de hoy.

  AUDITORIA  Se ha ejecutado la sonda y se ha escuchado el buzón 72 horas.
             Ahí sí se puede contar qué llegó y qué no, con horas. Lleva
             el PDF adjunto.

Decir "abandoné un carrito" sin haberlo hecho es mentira comprobable: basta
con que el dueño mire su panel. Costaría la venta y la credibilidad.

Forma del correo, y es deliberada:
  · un hallazgo concreto sobre SU tienda, no un argumentario
  · sin precio, sin oferta y sin catálogo
  · firmado, con identidad real y web
  · con una línea de baja que se respeta a la primera
Así es como convierte, y es la forma defendible frente al artículo 21 de la
LSSI: no es una comunicación comercial masiva, es un aviso individual.
"""

from __future__ import annotations

from dataclasses import dataclass

NOMBRES_PLATAFORMA = {
    "shopify": "Shopify", "woocommerce": "WooCommerce",
    "prestashop": "PrestaShop", "magento": "Magento",
    "bigcommerce": "BigCommerce", "wix": "Wix", "squarespace": "Squarespace",
}

FIRMA = """Sara Ferreira
Sora Systems · sorasystems.es

Si prefieres que no te vuelva a escribir, respóndeme "baja" y no lo hago."""


@dataclass
class Correo:
    para: str
    asunto: str
    cuerpo: str
    dominio: str
    plantilla: str
    adjunto: str = ""


def _marca(dominio: str) -> str:
    return dominio.split(".")[0].replace("-", " ").title()


def hallazgo(dominio: str, correo: str, plataforma: str = "",
             captura_email: bool = False) -> Correo:
    """Plantilla ligera: solo afirma lo que se ve en el código. Sale hoy."""
    marca = _marca(dominio)
    tienda = NOMBRES_PLATAFORMA.get(plataforma, "")
    en_plataforma = f" En una tienda de {tienda}" if tienda else " En tu tienda"

    if captura_email:
        matiz = (
            "Tenéis formulario para recoger el correo, así que la lista la "
            "estáis construyendo. Lo que no veo es qué pasa después con quien "
            "se va sin comprar."
        )
    else:
        matiz = (
            "Tampoco veo formulario para recoger el correo de quien entra, "
            "así que ahora mismo esa persona se va sin dejar rastro."
        )

    cuerpo = f"""Hola,

Estuve mirando {dominio} y me quedé con un detalle que igual os interesa.

No encuentro instalada ninguna herramienta de recuperación de carrito. Ni
Klaviyo, ni Mailchimp, ni Connectif, ni Brevo. {matiz}

Por qué lo miro: siete de cada diez personas que llenan un carrito lo dejan
a medias. Sin una secuencia automática detrás, esas ventas no se recuperan;
simplemente se pierden.{en_plataforma} se arregla con tres correos
automáticos —uno a la hora, otro al día siguiente y otro a los tres días—
con la foto y el nombre de lo que la persona se dejó. Es de las pocas cosas
del comercio online que se montan una vez y siguen trabajando solas.

Te lo cuento por si no lo teníais visto. No hace falta que me contestes.

{FIRMA}"""

    return Correo(para=correo, asunto=f"una cosa que vi en {dominio}",
                  cuerpo=cuerpo, dominio=dominio, plantilla="hallazgo")


def auditoria(dominio: str, correo: str, puntuacion: int,
              euros_mes: float, correos_recibidos: int,
              horas_primero: float | None = None,
              ruta_pdf: str = "") -> Correo:
    """Plantilla completa: solo se usa DESPUÉS de haber sondeado de verdad."""
    marca = _marca(dominio)

    if correos_recibidos == 0:
        observado = (
            "Dejé un producto en el carrito con un correo válido y esperé tres "
            "días. No llegó nada. Ni un recordatorio, ni una bienvenida."
        )
    elif horas_primero is not None and horas_primero > 24:
        observado = (
            f"Dejé un producto en el carrito y el primer aviso tardó "
            f"{horas_primero:.0f} horas en llegar. A esas alturas la mayoría ya "
            "ha comprado en otro sitio."
        )
    else:
        observado = (
            f"Dejé un producto en el carrito y me llegaron {correos_recibidos} "
            "correos. Hay cosas bien puestas y otras que se pueden afinar."
        )

    cuerpo = f"""Hola,

Hice una prueba en {dominio} y te cuento qué salió, por si os sirve.

{observado}

Con el tráfico y el ticket medio de una tienda como la vuestra, eso son del
orden de {euros_mes:,.0f} € al mes que se quedan por el camino. Te adjunto
el detalle en dos páginas: qué llegó, cuándo, y qué falta.

Es una estimación con medias del sector, no una promesa. Si me pasas vuestras
cifras reales la afino en diez minutos, y si sale menos de lo que pone ahí,
te lo digo.

{FIRMA}""".replace(",", ".")

    return Correo(para=correo, asunto=f"probé una cosa en {dominio}",
                  cuerpo=cuerpo, dominio=dominio, plantilla="auditoria",
                  adjunto=ruta_pdf)
