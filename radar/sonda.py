"""Etapa 2 — la sonda: entrar en la tienda, suscribirse y abandonar un carrito.

Reproduce lo que hace un cliente real que se lo piensa mejor, usando un alias
de correo unico por tienda para poder atribuir despues cada email recibido.

Buena vecindad, y no es opcional:
  - una sola sonda por tienda, nunca en bucle
  - pausa configurable entre tiendas
  - agente identificable si se quiere ser transparente (identificarse=True)
  - no toca pasarelas de pago: se detiene al introducir el email
"""

from __future__ import annotations

import random
import time
from contextlib import contextmanager
from collections.abc import Iterator

from playwright.sync_api import Page, TimeoutError as TiempoAgotado, sync_playwright

from . import selectores as S
from .modelos import Sonda

CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ESPERA_CORTA = 4_000
ESPERA_NAVEGACION = 20_000

AGENTE_ANONIMO = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
AGENTE_IDENTIFICADO = (
    "Mozilla/5.0 (compatible; RadarRetencion/0.1; auditoria de retencion; "
    "+https://sorasystems.es/robot)"
)


def _primero_visible(pagina: Page, candidatos: list[str], espera: int = ESPERA_CORTA):
    """Devuelve el primer selector de la lista que exista y sea visible."""
    for selector in candidatos:
        try:
            elemento = pagina.locator(selector).first
            elemento.wait_for(state="visible", timeout=espera)
            return elemento
        except (TiempoAgotado, Exception):
            continue
    return None


def _pulsar(pagina: Page, candidatos: list[str], espera: int = ESPERA_CORTA) -> bool:
    elemento = _primero_visible(pagina, candidatos, espera)
    if elemento is None:
        return False
    try:
        elemento.click(timeout=espera)
        pagina.wait_for_timeout(1_500)
        return True
    except Exception:
        return False


def _rellenar(pagina: Page, candidatos: list[str], texto: str) -> bool:
    elemento = _primero_visible(pagina, candidatos)
    if elemento is None:
        return False
    try:
        elemento.fill(texto, timeout=ESPERA_CORTA)
        return True
    except Exception:
        return False


@contextmanager
def _navegador(identificarse: bool = False) -> Iterator:
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        contexto = navegador.new_context(
            user_agent=AGENTE_IDENTIFICADO if identificarse else AGENTE_ANONIMO,
            locale="es-ES",
            viewport={"width": 1440, "height": 900},
        )
        try:
            yield contexto
        finally:
            contexto.close()
            navegador.close()


def sondear(
    url: str,
    alias: str,
    carpeta_capturas: str | None = None,
    identificarse: bool = False,
) -> Sonda:
    """Ejecuta la sonda completa sobre una tienda.

    `alias` es el correo unico con el que se registra esta sonda. Debe ser un
    buzon real que se pueda leer despues (ver radar/buzon.py).
    """
    resultado = Sonda(url=url, alias=alias)
    if not url.startswith("http"):
        url = f"https://{url}"

    try:
        with _navegador(identificarse) as contexto:
            pagina = contexto.new_page()
            pagina.goto(url, timeout=ESPERA_NAVEGACION, wait_until="domcontentloaded")
            pagina.wait_for_timeout(2_500)   # deja que arranquen los popup

            if _pulsar(pagina, S.COOKIES, espera=3_000):
                resultado.notas.append("banner de cookies aceptado")

            # --- Suscripcion -------------------------------------------------
            # Se intenta antes de navegar: muchos popup solo salen en portada.
            if _rellenar(pagina, S.CAMPO_EMAIL_SUSCRIPCION, alias):
                if _pulsar(pagina, S.BOTON_SUSCRIPCION):
                    resultado.suscrito = True
                    resultado.notas.append("formulario de suscripcion enviado")
                else:
                    resultado.notas.append("campo de suscripcion sin boton usable")
            else:
                resultado.notas.append("sin formulario de suscripcion visible")

            pagina.wait_for_timeout(1_500)
            _pulsar(pagina, S.CERRAR_POPUP, espera=2_000)

            # --- Producto ----------------------------------------------------
            enlace = _primero_visible(pagina, S.ENLACE_PRODUCTO, espera=6_000)
            if enlace is None:
                resultado.error = "no se encontro ningun enlace de producto"
                return resultado
            try:
                resultado.producto_usado = (enlace.inner_text(timeout=2_000) or "").strip()[:80]
            except Exception:
                pass
            enlace.click(timeout=ESPERA_CORTA)
            pagina.wait_for_load_state("domcontentloaded", timeout=ESPERA_NAVEGACION)
            pagina.wait_for_timeout(2_000)
            _pulsar(pagina, S.CERRAR_POPUP, espera=2_000)

            # --- Carrito -----------------------------------------------------
            if not _pulsar(pagina, S.ANADIR_AL_CARRITO, espera=6_000):
                resultado.error = "no se pudo anadir el producto al carrito"
                return resultado
            resultado.carrito_alcanzado = True
            pagina.wait_for_timeout(2_500)

            if not _pulsar(pagina, S.IR_AL_CHECKOUT, espera=5_000):
                _pulsar(pagina, S.IR_AL_CARRITO, espera=5_000)
                pagina.wait_for_timeout(1_500)
                if not _pulsar(pagina, S.IR_AL_CHECKOUT, espera=6_000):
                    resultado.error = "no se pudo llegar al checkout"
                    return resultado
            resultado.checkout_alcanzado = True
            pagina.wait_for_load_state("domcontentloaded", timeout=ESPERA_NAVEGACION)
            pagina.wait_for_timeout(2_500)

            # --- El email, que es el objetivo de toda la sonda ----------------
            if _rellenar(pagina, S.CAMPO_EMAIL_CHECKOUT, alias):
                resultado.email_introducido = True
                resultado.notas.append("email dejado en el checkout")
                # Muchas plataformas solo disparan el flujo de carrito
                # abandonado cuando el campo pierde el foco o se avanza un paso.
                try:
                    pagina.keyboard.press("Tab")
                    pagina.wait_for_timeout(1_200)
                except Exception:
                    pass
                _pulsar(pagina, S.CONTINUAR_CHECKOUT, espera=4_000)
                pagina.wait_for_timeout(3_000)
            else:
                resultado.error = "no se encontro campo de email en el checkout"
                return resultado

            if carpeta_capturas:
                ruta = f"{carpeta_capturas}/{alias.split('@')[0]}.png"
                pagina.screenshot(path=ruta, full_page=False)
                resultado.capturas.append(ruta)

            # Abandono: se cierra sin pagar. Eso es justo lo que medimos.
            resultado.notas.append("carrito abandonado")

    except Exception as e:
        resultado.error = f"{type(e).__name__}: {e}"[:200]

    return resultado


def pausa_educada(minimo: float = 20.0, maximo: float = 45.0) -> None:
    """Espera entre tiendas. No quites esto al pasar a produccion."""
    time.sleep(random.uniform(minimo, maximo))
