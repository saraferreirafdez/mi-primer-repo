"""Fase 2 — confirmar por el código de la portada antes de escribir a nadie.

Motivo, medido por CoWork el 22/09/2026 sobre 121 dominios que habían pasado
LIMPIOS el filtro de DNS:

    Con ESP instalado visible en el código .... 41
    Tasa de falso positivo ................... 33,9 %

    Mailchimp 13 · Klaviyo 12 · Connectif 11 · Brevo 5 · MailerLite 2
    HubSpot 1 · ActiveCampaign 1 · Omnisend 0

La causa es la misma que hacía valiosa la señal del token, pero al revés: el
DNS solo deja huella cuando la tienda envía CON SU PROPIO DOMINIO. Una tienda
que instala el ESP desde la app de su plataforma y envía desde el dominio del
proveedor no publica NADA en su DNS. Es invisible por ahí y evidente en el
código.

Sin esta fase, una de cada tres tiendas a las que escribiéramos ya tendría el
sistema puesto, y el correo quedaría en ridículo. Esta es la fase que
convierte la lista en vendible.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from .detectar import _descargar, _hay_captura_email
from .huellas import CAPTACION, ESPS, PLATAFORMAS


@dataclass
class Veredicto:
    """¿Se le escribe a esta tienda, sí o no?"""

    dominio: str
    plataforma: str = ""
    esps: list[str] = field(default_factory=list)
    captadores: list[str] = field(default_factory=list)
    captura_email: bool = False
    error: str = ""

    @property
    def escribible(self) -> bool:
        """Solo se escribe a quien NO tiene ya resuelto el abandono.

        Descarta tanto por ESP como por captador de carrito: si la tienda
        paga un Privy o un Justuno, ya trabaja el abandono aunque no se le
        vea ESP, y el correo de hallazgo no tendría nada que decirle.
        """
        return not self.error and not self.esps and not self.captadores

    @property
    def motivo(self) -> str:
        if self.error:
            return f"no verificable: {self.error}"
        if self.esps:
            return f"ya tiene {', '.join(self.esps)}"
        if self.captadores:
            return f"ya usa captador: {', '.join(self.captadores)}"
        return "sin sistema de recuperación — ESCRIBIBLE"


def _buscar(html: str, catalogo: dict[str, list[str]]) -> list[str]:
    return [k for k, senales in catalogo.items() if any(s in html for s in senales)]


def verificar(dominio: str) -> Veredicto:
    """Descarga la portada y decide si la tienda es candidata de verdad."""
    v = Veredicto(dominio=dominio)
    try:
        html = _descargar(dominio)
    except Exception as e:
        v.error = f"{type(e).__name__}"[:40]
        return v

    plataformas = _buscar(html, PLATAFORMAS)
    v.plataforma = plataformas[0] if plataformas else ""
    v.esps = _buscar(html, ESPS)
    v.captadores = _buscar(html, CAPTACION)
    v.captura_email = _hay_captura_email(html)
    return v


def verificar_lote(dominios: Iterable[str], hilos: int = 4,
                   pausa: float = 1.0) -> Iterator[Veredicto]:
    """Verifica en paralelo, con pausa entre tandas para no machacar a nadie.

    Cuatro hilos y un segundo de pausa es el ritmo que CoWork midió como
    sostenible. No lo subas sin motivo: esto visita tiendas de terceros.
    """
    dominios = list(dominios)
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        futuros = {pool.submit(verificar, d): d for d in dominios}
        for futuro in as_completed(futuros):
            try:
                yield futuro.result()
            except Exception as e:
                yield Veredicto(dominio=futuros[futuro], error=str(e)[:40])
            time.sleep(pausa / max(hilos, 1))
