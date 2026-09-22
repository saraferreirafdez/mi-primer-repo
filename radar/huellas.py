"""Huellas para identificar plataforma de ecommerce y proveedor de email.

Cada huella es una lista de cadenas que se buscan en el HTML y en las URLs
de los recursos que carga la pagina. Se buscan en minusculas.

Manten esto ordenado: es el fichero que hay que tocar cuando una plataforma
cambia sus dominios de servicio.
"""

# Plataforma de ecommerce
PLATAFORMAS: dict[str, list[str]] = {
    "shopify": [
        "cdn.shopify.com", "/cdn/shop/", "shopify.theme",
        "shopifycloud", "myshopify.com", "shopify-features",
    ],
    "woocommerce": [
        "wp-content/plugins/woocommerce", "woocommerce-page",
        "wc-ajax", "woocommerce_params", "wc_add_to_cart_params",
    ],
    "prestashop": ["prestashop", "/modules/ps_", "prestashop-"],
    "magento": ["/static/version", "magento_", "mage/cookies"],
    "bigcommerce": ["bigcommerce.com", "cdn11.bigcommerce"],
    "squarespace": ["squarespace.com", "static1.squarespace"],
    "wix": ["wix.com", "wixstatic.com", "parastorage.com"],
}

# Proveedor de email (ESP). El orden importa: el primero que acierte, gana.
ESPS: dict[str, list[str]] = {
    "klaviyo": [
        "static.klaviyo.com", "static-tracking.klaviyo.com", "klaviyo.js",
        "a.klaviyo.com", "_learnq", "klaviyo_subscribe", "fast.a.klaviyo",
    ],
    "mailchimp": [
        "chimpstatic.com", "list-manage.com", "mc.us", "mailchimp.com/",
        "mcjs", "downloads.mailchimp.com", "mailchi.mp",
    ],
    "omnisend": [
        "omnisrc.com", "omnisend.com", "omnisendsnippet", "omnisnippet",
    ],
    "brevo": [
        "sibautomation.com", "sendinblue.com", "brevo.com", "sib-api",
        "sibforms.com",
    ],
    "activecampaign": [
        "prism.app-us1.com", "trackcmp.net", "activehosted.com",
        "activecampaign.com",
    ],
    "connectif": ["connectif.ai", "connectif.cloud", "cdn.connectif"],
    "mailerlite": ["mailerlite.com", "ml-attr", "mlsend.com"],
    "doppler": ["fromdoppler.com", "doppler.io"],
    "acumbamail": ["acumbamail.com"],
    "drip": ["getdrip.com", "drip.com/", "_dcq"],
    "hubspot": ["js.hs-scripts.com", "hs-analytics", "hubspot.com/"],
    "shopify_email": ["shopify_email", "shopifyemail"],
}

# Connectif es española y en el mercado español pesa tanto como Klaviyo o
# Mailchimp. CoWork la encontró en 11 de 41 tiendas el 22/09/2026 y por DNS
# se escapaba casi entera. Va al primer nivel, no como secundaria.

# Herramientas de captacion / popup. No son ESP, pero si una tienda paga un
# captador de carrito YA TRABAJA EL ABANDONO: no es clienta aunque no se le
# detecte ESP. Verlas aquí descarta, no suma.
CAPTACION: dict[str, list[str]] = {
    "privy": ["privy.com", "privymktg", "widget.privy"],
    "attentive": ["attentivemobile.com", "attn.tv"],
    "justuno": ["justuno.com"],
    "optinmonster": ["optinmonster.com", "omappapi"],
    "sumo": ["sumo.com", "sumome.com"],
    "yotpo": ["yotpo.com"],
}

# Pistas de que la pagina pide el email en algun sitio
SENALES_FORMULARIO: list[str] = [
    'type="email"', "type='email'", 'name="email"', "newsletter",
    "suscri", "subscribe", "boletin", "bolet&iacute;n",
]
