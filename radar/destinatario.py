"""Clasificación del tipo de dirección de correo.

La tabla "Envios Sora" de Airtable lo tiene escrito en el propio campo:

    "Solo se escribe a Generica de sociedad (info@, contacto@ de una SL o
     SA). Las otras dos NO se envian: son datos personales."

Y es correcto. Una dirección genérica de empresa es un dato de la sociedad;
nombre.apellido@ o un gmail de autónomo son datos personales de una persona
física, con otra protección. Este módulo hace esa separación, y el enviador
descarta todo lo que no sea genérica.
"""

from __future__ import annotations

import re

GENERICA = "Generica de sociedad"
NOMINATIVA = "Nominativa"
PERSONAL = "Autonomo o personal"

# Buzones de función: pertenecen a la empresa, no a una persona.
PREFIJOS_GENERICOS = {
    "info", "contacto", "contact", "hola", "hello", "pedidos", "ventas",
    "comercial", "atencion", "atencioncliente", "clientes", "tienda",
    "shop", "store", "admin", "administracion", "soporte", "ayuda",
    "reservas", "logistica", "compras", "facturacion", "marketing",
    "web", "online", "correo", "mail", "buzon", "general", "oficina",
}

# Proveedores gratuitos: casi siempre autónomo o persona física.
DOMINIOS_GRATUITOS = {
    "gmail.com", "hotmail.com", "hotmail.es", "outlook.com", "outlook.es",
    "yahoo.com", "yahoo.es", "live.com", "msn.com", "icloud.com", "me.com",
    "aol.com", "protonmail.com", "proton.me", "gmx.es", "terra.es",
    "telefonica.net", "movistar.es", "ya.com", "wanadoo.es",
}

# Direcciones de plantilla sin rellenar que se cuelan al extraer de webs.
BASURA = {
    "tu@email.com", "info@mysite.com", "email@example.com", "tu@correo.com",
    "donate@opencart.com", "nombre@dominio.com", "info@tudominio.com",
    "youremail@domain.com", "example@example.com", "test@test.com",
}


def clasificar(correo: str) -> str:
    """Devuelve el valor exacto del campo "Tipo de direccion" de Airtable."""
    correo = (correo or "").strip().lower()
    if "@" not in correo:
        return PERSONAL
    usuario, _, dominio = correo.partition("@")

    if dominio in DOMINIOS_GRATUITOS:
        return PERSONAL

    # Se normaliza quitando puntos, guiones y dígitos de cola: "atencion.cliente"
    # y "atencion-cliente2" son el mismo buzón de función.
    limpio = re.sub(r"[._\-]", "", usuario)
    limpio = re.sub(r"\d+$", "", limpio)
    if limpio in PREFIJOS_GENERICOS or usuario in PREFIJOS_GENERICOS:
        return GENERICA

    # nombre.apellido@ o inicial+apellido@ en dominio propio: persona con
    # nombre y apellidos dentro de la empresa.
    if re.match(r"^[a-zñáéíóú]+[._][a-zñáéíóú]+$", usuario) or len(usuario) <= 2:
        return NOMINATIVA

    # Dominio propio y prefijo que no reconocemos: se trata como nominativa,
    # que es el lado prudente. No enviar de más nunca ha costado una sanción.
    return NOMINATIVA


def es_basura(correo: str) -> bool:
    return (correo or "").strip().lower() in BASURA


def escribible(correo: str) -> bool:
    """Solo se escribe a direcciones genéricas de sociedad, y nunca a basura."""
    return not es_basura(correo) and clasificar(correo) == GENERICA
