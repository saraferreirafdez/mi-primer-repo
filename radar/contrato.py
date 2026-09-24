"""Hallazgo y correo para las adjudicatarias de contratos públicos.

La línea de tiendas tenía algo que mirar: el carrito. Aquí no hay carrito.
Lo único que hay de cada empresa es su expediente en la Plataforma de
Contratación, y de ahí tiene que salir algo concreto y suyo, o no sale
correo. Una frase de plantilla con el nombre metido no es un hallazgo.

QUÉ TRAE EL FEED, COMPROBADO SOBRE 1.858 ADJUDICACIONES

  presupuesto base ....... 100 %   pero ojo con los lotes, abajo
  nº de licitadores ...... 100 %   va dentro de cada TenderResult
  importe adjudicado ......· 79 %
  duración ................ 83 %
  fecha de fin ............ 16 %   casi nunca: no se usa

LA TRAMPA DE LOS LOTES, QUE CASI ME HACE INVENTAR UNA CIFRA

De las 1.402 adjudicaciones a un lote concreto, CERO traen presupuesto
propio del lote: el único BudgetAmount del expediente es el del contrato
entero. Calcular la baja dividiendo lo adjudicado a UN lote entre el
presupuesto de TODOS da un porcentaje falso y enorme. El caso real que lo
destapó: Aldees Infantils, 169.698 € adjudicados en el lote 2 de un
expediente de 1.590.646 € — eso no es una baja del 89 %, es otra cosa.

Por eso la baja solo se calcula cuando la adjudicación es del contrato
entero. En los lotes no hay baja, y punto.

LO QUE EL CORREO PUEDE AFIRMAR Y LO QUE NO

  SÍ  las cifras del expediente: presupuesto, adjudicado, baja, licitadores,
      duración, organismo. Son públicas y son suyas.
  SÍ  la aritmética sobre esas cifras, dicha como aritmética.
  SÍ  la regla general del artículo 192 de la LCSP, dicha como regla
      general: las penalidades las fija el pliego sobre el precio del
      contrato y la ley las topa en el 10 %.
  NO  que estén incumpliendo. No hemos visto su expediente por dentro.
  NO  cuánto van a perder. Eso sería inventar sobre datos que no tenemos.

Sin precio, sin oferta y sin catálogo, con firma y con línea de baja: es lo
que lo mantiene del lado del aviso individual del artículo 21 de la LSSI y
no de la comunicación comercial en masa.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from .correo import FIRMA, Correo, ajustar

# Un contrato entero con una baja de este tamaño deja un margen fino: es el
# hallazgo más fuerte que da el feed.
BAJA_FUERTE = 10.0

# Con esta competencia, el contrato se peleó de verdad.
LICITADORES_MUCHOS = 6

# Por debajo de esto la baja es simbólica: ganaron por la oferta técnica,
# no por el precio. Es otro hallazgo, no la ausencia de uno.
BAJA_SIMBOLICA = 5.0

# El tope legal de las penalidades por ejecución defectuosa: artículo 192.1
# de la LCSP, sobre el precio del contrato sin IVA.
TOPE_PENALIDADES = 0.10

# Fuera del perfil de Sora aunque el hallazgo sea bueno: tienen informática
# propia y un departamento para esto. Se excluyen a mano y con el motivo,
# no se dejan caer en silencio.
FUERA_DE_PERFIL = {
    "B60864311": "Rodi Metro: 1.142 empleados",
    "A97929566": "Nunsys: integrador de TI grande, es competencia antes que cliente",
    "A79154126": "Universal McCann: multinacional de medios",
    "A28343358": "Carat España: multinacional de medios",
    "A79486833": "Elecnor Servicios: grupo grande",
    "A08214157": "Olympus Iberia: multinacional",
    "B46001897": "TK Elevadores: multinacional",
    "B86907128": "Agilent Technologies: multinacional",
    "A04038014": "Grupo Control: 4.500 empleados",
}

# Arranques de «objeto» que no dicen nada y estorban al leerlo en un correo.
PREAMBULOS = [
    r"^el contrato tiene por objeto (la |el |los |las )?",
    r"^el presente contrato tiene por objeto (la |el )?",
    r"^l'objecte d[’'e]aquest contracte és (la |el )?",
    r"^l'objecte del contracte és (la |el )?",
    r"^és objecte d[’'e]aquest contracte (la |el )?",
    r"^constituye el objeto del (presente )?contrato (la |el )?",
    r"^contrataci[oó]n del ",
    r"^contractaci[oó] (de |del )?",
]


def limpiar_objeto(texto: str) -> str:
    """Deja el objeto en algo que se pueda leer dentro de una frase.

    Del feed sale con entidades HTML sin resolver, con interrogantes donde
    iban los apóstrofos catalanes y con preámbulos de doscientos caracteres
    antes de decir de qué va el contrato.
    """
    t = html.unescape(texto or "").replace("\xa0", " ")
    t = re.sub(r"(?<=[a-zA-ZçÇ])\?(?=[a-zA-Z])", "'", t)   # d?entre -> d'entre
    # El apostrofo curvo hacia que «l'objecte d'aquest contracte» no
    # coincidiera con ningun preambulo y se colara entero en el correo.
    t = t.replace("\u2019", "'").replace("\u2018", "'")
    t = re.sub(r"\s+", " ", t).strip()
    for p in PREAMBULOS:
        nuevo = re.sub(p, "", t, flags=re.I)
        if nuevo != t:
            t = nuevo.strip()
            break
    if not t:
        return t
    # Bajar la inicial, salvo si la primera palabra son siglas («BG - Obres»),
    # que quedaban como «bG».
    primera = t.split(" ", 1)[0]
    if primera.isupper() and len(primera) > 1:
        return t
    return t[:1].lower() + t[1:]


# Palabras con las que no puede acabar una frase recortada: dejan al lector
# esperando lo que viene detrás («...atención integral a las,»).
COLGANDO = {
    "de", "del", "de la", "a", "al", "a la", "en", "con", "por", "para",
    "y", "e", "o", "u", "i", "el", "la", "los", "las", "un", "una", "unos",
    "unas", "que", "su", "sus", "dels", "als", "per", "amb", "dels", "les",
    "el·la", "d", "l", "sobre", "entre", "segun", "según", "mediante",
}


def recortar(texto: str, limite: int = 120) -> str:
    """Corta el objeto por un sitio donde la frase ya se sostiene sola.

    Cortar a pelo por el carácter 120 deja cosas como «atención integral a
    las», que en un correo parece que se ha roto algo. Se busca primero una
    coma o un punto y coma antes del límite, y si no hay, se retrocede
    palabra a palabra hasta que la última no sea una preposición ni un
    artículo colgando.
    """
    texto = texto.rstrip(" .,;:")
    if len(texto) <= limite:
        return texto

    corte = texto[:limite]
    for signo in (";", ",", " — ", " - "):
        if signo in corte[limite // 2:]:
            return corte[:corte.rfind(signo)].rstrip(" .,;:")

    palabras = corte.rsplit(" ", 1)[0].split(" ")
    while palabras and palabras[-1].lower().strip(".,;:") in COLGANDO:
        palabras.pop()
    return " ".join(palabras).rstrip(" .,;:")


def porcentaje(n: float) -> str:
    """En español el decimal va con coma, y el entero sin decimal.

    «Una baja del 14.0 %» delata que lo ha escrito una máquina.
    """
    return f"{n:.0f}" if abs(n - round(n)) < 0.05 else f"{n:.1f}".replace(".", ",")


# Colas de cargo que el organismo arrastra en su nombre oficial y que en un
# correo solo repiten lo ya dicho: «Universidad del Pais Vasco-La Gerente de
# la UPV/EHU» dice UPV/EHU tres veces.
CARGOS = re.compile(
    r"[-–,.]\s*(la\s+gerent\w*|el\s+gerent\w*|gerenci\w*|secretar[ií]a\s+general"
    r"|[óo]rgano\s+de\s+contrataci[óo]n|junta\s+de\s+gobierno|direcci[óo]n\s+general)"
    r"\b.*$", re.I)


def limpiar_organismo(nombre: str) -> str:
    """Deja el nombre del organismo en algo que se lea de una pasada.

    Del feed salen con la sigla delante, el nombre largo detrás y el cargo
    del firmante pegado al final. Se queda el trozo mas descriptivo y se le
    quita el cargo.
    """
    n = re.sub(r"\s+", " ", html.unescape(nombre or "")).strip()
    if " - " in n:
        n = max(n.split(" - "), key=len).strip()
    n = CARGOS.sub("", n).strip(" -–,.")
    return n


def euros(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".") + " €"


@dataclass
class Contrato:
    nif: str
    empresa: str
    expediente: str
    objeto: str
    organismo: str
    base: float | None
    adjudicado: float | None
    licitadores: int
    duracion: str
    duracion_ud: str
    lote: str
    enlace: str = ""

    @property
    def baja_pct(self) -> float | None:
        """La baja, solo cuando se puede calcular sin mentir.

        Hace falta que la adjudicación sea del contrato ENTERO: si es de un
        lote, el presupuesto que trae el feed es el de todos los lotes
        juntos y la división no significa nada.
        """
        if self.lote:
            return None
        if not self.base or not self.adjudicado or self.base <= 0:
            return None
        if self.adjudicado > self.base:      # dato incoherente del feed
            return None
        return (1 - self.adjudicado / self.base) * 100

    @property
    def dejado(self) -> float | None:
        """Euros de diferencia entre el presupuesto y lo que cobran."""
        b = self.baja_pct
        return None if b is None else self.base - self.adjudicado

    @property
    def plazo(self) -> str:
        """«24 MON» no se le dice a nadie en un correo."""
        if not self.duracion.isdigit():
            return ""
        n = int(self.duracion)
        if self.duracion_ud == "ANN":
            return "un año" if n == 1 else f"{n} años"
        if self.duracion_ud == "MON":
            return "un mes" if n == 1 else f"{n} meses"
        if self.duracion_ud == "DAY":
            return f"{n} días"
        return ""


@dataclass
class Hallazgo:
    contrato: Contrato
    tipo: str          # baja | tecnica | competido
    titular: str       # la frase concreta, en una línea
    motivo: str        # por qué pasa el filtro, para el CSV


def hallazgo(c: Contrato) -> Hallazgo | None:
    """El filtro. Devuelve None cuando no hay nada concreto que decir.

    Devolver None es el caso NORMAL y es lo que hace que esto no sea un
    envío masivo: de las 31 adjudicaciones de la lista, la mayoría no da
    para un correo honesto y no lo van a recibir.
    """
    if c.nif in FUERA_DE_PERFIL:
        return None
    if not (c.expediente and c.organismo and c.adjudicado):
        return None
    objeto = limpiar_objeto(c.objeto)
    if len(objeto) < 25:          # «571/2023 am alta tecnologia» no es un objeto
        return None

    baja, lic = c.baja_pct, c.licitadores

    if baja is not None and baja >= BAJA_FUERTE:
        return Hallazgo(c, "baja",
                        f"baja del {porcentaje(baja)} % ({euros(c.dejado)} por debajo del presupuesto)",
                        f"contrato entero, baja {porcentaje(baja)} % >= {BAJA_FUERTE:.0f} %")

    if lic >= LICITADORES_MUCHOS and baja is not None and baja < BAJA_SIMBOLICA:
        return Hallazgo(c, "tecnica",
                        f"{lic} licitadores y prácticamente sin bajar el precio",
                        f"{lic} licitadores con baja de solo {porcentaje(baja)} %")

    if lic >= LICITADORES_MUCHOS:
        return Hallazgo(c, "competido", f"{lic} licitadores en ese lote",
                        f"{lic} licitadores; es un lote, la baja no se puede calcular")

    return None


# --------------------------------------------------------------------------
# EL CORREO
# --------------------------------------------------------------------------

REGLA = (
    "En un contrato de servicios, lo que se ofertó como mejora deja de ser "
    "una promesa comercial y pasa a ser obligación contractual. Las "
    "penalidades por ejecutarlo mal las fija el pliego sobre el precio del "
    "contrato, y el artículo 192 de la Ley de Contratos topa cada una en el "
    "10 % de ese precio."
)

CIERRE = (
    "Lo que me encuentro casi siempre es que esos compromisos —plazos de "
    "respuesta, medios adscritos, mejoras ofertadas, informes periódicos— "
    "están repartidos entre el pliego, la oferta y el contrato, y nadie "
    "tiene la lista entera en un sitio. No digo que sea vuestro caso: no he "
    "visto vuestro expediente por dentro, solo lo que publica la Plataforma."
)


def _apertura(c: Contrato, objeto: str) -> str:
    plazo = f", para {c.plazo}" if c.plazo else ""
    return (f"Os escribo por el expediente {c.expediente}, el de "
            f"{limpiar_organismo(c.organismo)}: "
            f"{objeto}{plazo}.")


def correo_contrato(c: Contrato, destino: str) -> Correo | None:
    """Redacta el correo. Devuelve None si el contrato no da hallazgo."""
    h = hallazgo(c)
    if h is None:
        return None
    objeto = recortar(limpiar_objeto(c.objeto))
    tope = c.adjudicado * TOPE_PENALIDADES

    if h.tipo == "baja":
        nucleo = (
            f"Lo ganasteis por {euros(c.adjudicado)} sobre un presupuesto "
            f"base de {euros(c.base)}. Una baja del {porcentaje(c.baja_pct)} %: "
            f"{euros(c.dejado)} que dejasteis sobre la mesa para quedaros el "
            f"contrato.\n\n"
            f"Esa baja es también el margen que ya no está para absorber un "
            f"problema. {REGLA} Sobre vuestros {euros(c.adjudicado)} eso son "
            f"hasta {euros(tope)}."
        )
    elif h.tipo == "tecnica":
        nucleo = (
            f"Erais {c.licitadores} empresas y lo ganasteis sin bajar el "
            f"precio: {euros(c.adjudicado)} sobre un presupuesto de "
            f"{euros(c.base)}. O sea que ganasteis por lo que ofrecisteis, "
            f"no por lo que cobrasteis.\n\n"
            f"Y ahí está el detalle. {REGLA} Sobre vuestros "
            f"{euros(c.adjudicado)} eso son hasta {euros(tope)}."
        )
    else:
        nucleo = (
            f"Erais {c.licitadores} empresas peleando ese lote, y lo "
            f"ganasteis vosotros por {euros(c.adjudicado)}.\n\n"
            f"{REGLA} Sobre vuestros {euros(c.adjudicado)} eso son hasta "
            f"{euros(tope)}."
        )

    cuerpo = f"""Hola,

{_apertura(c, objeto)}

{nucleo}

Todo esto está publicado en la Plataforma de Contratación del Sector
Público. No es nada que no se pueda mirar; lo que pasa es que casi nadie
lo mira.

{CIERRE}

No te pido nada. Si te sirve, te cuento en dos líneas cómo lo reviso yo.

{FIRMA}"""

    cuerpo = ajustar(cuerpo.split(FIRMA)[0]).rstrip() + "\n\n" + FIRMA
    return Correo(para=destino, asunto=f"el expediente {c.expediente}",
                  cuerpo=cuerpo, dominio=c.empresa, plantilla=f"contrato/{h.tipo}")
