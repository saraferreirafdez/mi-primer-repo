"""Candidatos de selector para cada paso de la sonda.

Las tiendas no comparten maquetacion, asi que la sonda prueba una lista de
candidatos por paso y se queda con el primero que exista y sea visible.
Estan en espanol y en ingles porque muchas tiendas espanolas usan temas
traducidos a medias.

Este es el fichero que se toca cuando una tienda concreta no funciona:
se anade su selector al final de la lista que corresponda.
"""

COOKIES = [
    "#onetrust-accept-btn-handler",
    "button#didomi-notice-agree-button",
    "button[id*='accept']", "button[class*='accept']",
    "button:has-text('Aceptar todo')", "button:has-text('Aceptar todas')",
    "button:has-text('Aceptar')", "button:has-text('Accept all')",
    "button:has-text('Accept')", "button:has-text('De acuerdo')",
    "button:has-text('Entendido')", "a:has-text('Aceptar')",
]

# Los popup de suscripcion hay que cerrarlos para poder navegar, pero solo
# DESPUES de haber intentado suscribirse en ellos.
CERRAR_POPUP = [
    "button[aria-label*='lose']", "button[aria-label*='errar']",
    "button[class*='close']", "div[class*='modal'] button[class*='close']",
    ".needsclick button", "button:has-text('No, gracias')",
    "button:has-text('No thanks')", "[aria-label='Close dialog']",
]

CAMPO_EMAIL_SUSCRIPCION = [
    "form[class*='newsletter'] input[type='email']",
    "form[id*='newsletter'] input[type='email']",
    "footer input[type='email']",
    "div[class*='modal'] input[type='email']",
    "div[class*='popup'] input[type='email']",
    "input[name='email'][placeholder*='orreo']",
    "input[type='email']",
]

BOTON_SUSCRIPCION = [
    "form[class*='newsletter'] button[type='submit']",
    "footer button[type='submit']",
    "button:has-text('Suscribirme')", "button:has-text('Suscribir')",
    "button:has-text('Subscribe')", "button:has-text('Apuntarme')",
    "button:has-text('Quiero mi descuento')",
    "input[type='submit']", "button[type='submit']",
]

ENLACE_PRODUCTO = [
    "a[href*='/products/']",          # Shopify
    "a[href*='/producto/']",          # WooCommerce en espanol
    "a[href*='/product/']",
    "a[class*='product-card']", "a[class*='product-item']",
    "li[class*='product'] a", "div[class*='product'] a[href]",
]

ANADIR_AL_CARRITO = [
    "button[name='add']",             # Shopify estandar
    "button.single_add_to_cart_button",   # WooCommerce estandar
    "form[action*='/cart/add'] button[type='submit']",
    "button:has-text('Anadir al carrito')",
    "button:has-text('Añadir al carrito')",
    "button:has-text('Agregar al carrito')",
    "button:has-text('Add to cart')", "button:has-text('Comprar')",
    "button[class*='add-to-cart']", "button[id*='AddToCart']",
]

IR_AL_CARRITO = [
    "a[href$='/cart']", "a[href*='/carrito']", "a[href*='/cart']",
    "a[class*='cart-link']", "a[aria-label*='arrito']",
]

IR_AL_CHECKOUT = [
    "button[name='checkout']",
    "a[href*='/checkout']", "a.checkout-button",
    "button:has-text('Finalizar compra')",
    "button:has-text('Tramitar pedido')",
    "button:has-text('Checkout')", "button:has-text('Pagar')",
    "a:has-text('Finalizar compra')", "a:has-text('Tramitar pedido')",
]

CAMPO_EMAIL_CHECKOUT = [
    "input#email", "input[name='email']",
    "input[name='billing_email']",     # WooCommerce
    "input[type='email']",
]

CONTINUAR_CHECKOUT = [
    "button:has-text('Continuar')", "button:has-text('Continue')",
    "button[type='submit']",
]
