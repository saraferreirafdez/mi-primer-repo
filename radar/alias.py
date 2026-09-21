"""Generacion de alias unicos por tienda.

Cada sonda usa un alias distinto sobre un mismo buzon con catch-all o
subetiquetas, para poder atribuir sin ambiguedad que tienda manda cada correo.
"""

from __future__ import annotations

import hashlib
import os
import re


def alias_para(url: str, base: str | None = None) -> str:
    """Devuelve algo como auditoria+tiendaejemplo7f3a@sorasystems.es."""
    base = base or os.environ.get("RADAR_ALIAS_BASE", "auditoria@sorasystems.es")
    usuario, _, dominio = base.partition("@")
    limpio = re.sub(r"^https?://(www\.)?", "", url.lower())
    limpio = re.sub(r"[^a-z0-9]", "", limpio.split("/")[0])[:16]
    firma = hashlib.sha1(url.encode()).hexdigest()[:4]
    return f"{usuario}+{limpio}{firma}@{dominio}"
