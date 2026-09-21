"""Etapa 1 — detectar plataforma y proveedor de email de una tienda.

Es la etapa mas valiosa del robot y la unica que no necesita ni buzon ni
navegador: con una peticion HTTP por tienda se puede clasificar una lista
entera de candidatas en minutos.

Uso:
    from radar.detectar import detectar
    deteccion = detectar("https://ejemplo.es")
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Iterable, Iterator

from .huellas import CAPTACION, ESPS, PLATAFORMAS, SENALES_FORMULARIO
from .modelos import Deteccion

AGENTE = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIEMPO_ESPERA = 20
TAMANO_MAXIMO = 3_000_000  # 3 MB de HTML son de sobra; evita descargas absurdas


def _normalizar(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def _descargar(url: str) -> str:
    """Devuelve el HTML de la portada en minusculas, o lanza excepcion."""
    peticion = urllib.request.Request(
        _normalizar(url),
        headers={
            "User-Agent": AGENTE,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-ES,es;q=0.9",
        },
    )
    contexto = ssl.create_default_context()
    with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA, context=contexto) as r:
        crudo = r.read(TAMANO_MAXIMO)
    return crudo.decode("utf-8", errors="ignore").lower()


def _buscar(html: str, catalogo: dict[str, list[str]]) -> list[str]:
    """Devuelve las claves del catalogo cuyas huellas aparecen en el HTML."""
    return [clave for clave, senales in catalogo.items()
            if any(s in html for s in senales)]


def _hay_captura_email(html: str) -> bool:
    return any(s in html for s in SENALES_FORMULARIO)


def detectar(url: str) -> Deteccion:
    """Analiza una tienda y devuelve su ficha tecnica."""
    deteccion = Deteccion(url=url)
    try:
        html = _descargar(url)
    except urllib.error.HTTPError as e:
        deteccion.error = f"HTTP {e.code}"
        return deteccion
    except Exception as e:  # DNS, TLS, timeout, redireccion rota...
        deteccion.error = f"{type(e).__name__}: {e}"[:120]
        return deteccion

    plataformas = _buscar(html, PLATAFORMAS)
    deteccion.plataforma = plataformas[0] if plataformas else ""

    esps = _buscar(html, ESPS)
    if esps:
        deteccion.esp = esps[0]
        deteccion.esp_secundarios = esps[1:]

    # Las herramientas de captacion se anotan aparte: no son ESP, pero si
    # la tienda paga un popup y no tiene ESP, es una senal comercial fuerte.
    deteccion.esp_secundarios += _buscar(html, CAPTACION)
    deteccion.captura_email = _hay_captura_email(html)
    return deteccion


def detectar_lote(urls: Iterable[str], hilos: int = 8) -> Iterator[Deteccion]:
    """Analiza muchas tiendas en paralelo. Va devolviendo segun terminan."""
    urls = list(urls)
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        futuros = {pool.submit(detectar, u): u for u in urls}
        for futuro in as_completed(futuros):
            try:
                yield futuro.result()
            except Exception as e:
                yield Deteccion(url=futuros[futuro], error=f"fallo interno: {e}"[:120])
