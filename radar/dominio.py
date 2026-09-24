"""Del nombre de una empresa a su dominio, comprobado por DNS.

POR QUÉ ESTO EXISTE. El feed de PLACSP da el NIF y la razón social del
adjudicatario, y nada más: ni correo, ni teléfono, ni web. Comprobado sobre
1.858 WinningParty: dentro solo hay PartyIdentification y PartyName.

Desde este entorno no se puede abrir ninguna web (el proxy devuelve 403 a
todo lo que no sea GitHub, PyPI y npm), pero SÍ hay DNS. Y con DNS se
puede contestar a dos preguntas que quitan casi todo el trabajo manual:

  ¿existe este dominio?        registro A o AAAA
  ¿recibe correo?              registro MX

Un dominio sin MX no tiene buzón: escribir ahí es un rebote seguro. Así
que esto reduce una lista de conjeturas a un puñado de dominios vivos que
alguien con navegador solo tiene que abrir para leer el aviso legal.

LO QUE ESTO NO HACE, Y NO DEBE APARENTAR QUE HACE: no confirma que el
dominio sea de ESA empresa. Un nombre parecido no es una prueba. Eso se
confirma leyendo el aviso legal y comprobando que aparece el mismo NIF o
la misma razón social, y eso necesita abrir la página.
"""

from __future__ import annotations

import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import dns.resolver

# Formas jurídicas y adornos que no forman parte del nombre comercial.
FORMAS = [
    "sociedad limitada", "sociedad anonima", "sociedad cooperativa",
    "s a u", "s l u", "s l l", "s c p", "s coop", "sccl", "s a", "s l",
    "sau", "slu", "sll", "scp", "scoop", "sa", "sl", "slp", "ute",
    "unipersonal", "y asociados", "y cia", "e hijos",
]

# Palabras que no distinguen a nadie: un dominio hecho solo con esto no
# vale como conjetura.
VACIAS = {
    "grupo", "empresa", "empresas", "servicios", "servicio", "sociedad",
    "compania", "de", "del", "la", "el", "los", "las", "y", "e", "para",
    "gestion", "integral", "integrales", "nacional", "espana", "iberica",
    "centro", "general", "asociacion", "fundacion",
    # Palabras de catálogo: describen a qué se dedica, no cómo se llama.
    # Sin esto, «ELECNOR SERVICIOS Y PROYECTOS» solo cubría medio nombre
    # con elecnor.es, que es el dominio bueno.
    "proyectos", "proyecto", "tecnologia", "tecnologias", "soluciones",
    "ingenieria", "consulting", "consultoria", "asistencia", "mantenimiento",
    "obras", "digital", "digitales", "iberia", "sistemas", "global",
    "internacional", "productos", "comercial", "industrial", "tecnico",
    "tecnica", "implantacion", "aplicaciones", "calculo",
}

TLDS = (".es", ".com", ".cat", ".eus", ".gal", ".net", ".org")

# Sufijo NUTS de la región -> TLD que conviene probar primero.
TLD_POR_REGION = {
    "ES21": ".eus", "ES22": ".es", "ES51": ".cat", "ES11": ".gal",
}


def _limpiar(nombre: str) -> list[str]:
    """Nombre comercial en palabras, sin forma jurídica ni tildes."""
    t = unicodedata.normalize("NFKD", nombre.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for forma in FORMAS:
        t = re.sub(rf"(^|\s){re.escape(forma)}(\s|$)", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
    return [p for p in t.split() if p]


def candidatos(nombre: str, region: str = "", tope: int = 10) -> list[str]:
    """Dominios plausibles, del más probable al menos."""
    palabras = _limpiar(nombre)
    if not palabras:
        return []

    utiles = [p for p in palabras if p not in VACIAS] or palabras

    raices: list[str] = []
    def anadir(r: str) -> None:
        if len(r) >= 4 and r not in raices:
            raices.append(r)

    anadir("".join(utiles[:3]))
    anadir("".join(utiles[:2]))
    anadir(utiles[0])
    anadir("".join(palabras[:2]))     # con "grupo", que a veces sí va
    anadir("".join(palabras[:3]))

    tlds = list(TLDS)
    preferido = TLD_POR_REGION.get(region[:4])
    if preferido and preferido in tlds:
        tlds.remove(preferido)
        tlds.insert(0, preferido)

    salida = [r + t for r in raices for t in tlds]
    return salida[:tope]


@dataclass
class Dominio:
    dominio: str
    existe: bool = False
    recibe_correo: bool = False
    mx: list[str] = field(default_factory=list)
    cobertura: float = 0.0

    @property
    def fiabilidad(self) -> str:
        """Cuánto me fío de que este dominio sea de esa empresa.

        Nace de un susto real: para «GRUPO CONTROL EMPRESA DE SEGURIDAD»
        salían control.es y control.com, que existen y reciben correo pero
        no son suyos. Un dominio que solo recoge UNA palabra de un nombre
        de varias es casi siempre otra empresa.
        """
        if self.cobertura >= 0.99:
            return "alta"
        if self.cobertura >= 0.5:
            return "media"
        return "baja"


def _resolutor() -> dns.resolver.Resolver:
    r = dns.resolver.Resolver()
    r.nameservers = ["1.1.1.1", "8.8.8.8"]
    r.timeout = 3.0
    r.lifetime = 5.0
    return r


def comprobar(dominio: str) -> Dominio:
    """¿Existe? ¿Recibe correo? Nada más: esto no visita la web."""
    d = Dominio(dominio)
    r = _resolutor()
    try:
        r.resolve(dominio, "MX")
        d.existe = d.recibe_correo = True
        d.mx = sorted(str(x.exchange).rstrip(".").lower()
                      for x in r.resolve(dominio, "MX"))
        return d
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers, dns.exception.Timeout):
        pass
    try:
        r.resolve(dominio, "A")
        d.existe = True            # hay web, pero el correo no vive aquí
    except Exception:
        pass
    return d


def _cobertura(dominio: str, nombre: str) -> float:
    """Qué parte del nombre comercial recoge la raíz del dominio."""
    utiles = [p for p in _limpiar(nombre) if p not in VACIAS] or _limpiar(nombre)
    if not utiles:
        return 0.0
    raiz = dominio.rsplit(".", 1)[0]
    return sum(1 for p in utiles if p in raiz) / len(utiles)


def buscar(nombre: str, region: str = "", hilos: int = 10) -> list[Dominio]:
    """Los candidatos que existen, ordenados por fiabilidad y correo."""
    posibles = candidatos(nombre, region)
    if not posibles:
        return []
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        resultados = list(pool.map(comprobar, posibles))
    vivos = [d for d in resultados if d.existe]
    for d in vivos:
        d.cobertura = _cobertura(d.dominio, nombre)
    vivos.sort(key=lambda d: (-d.cobertura, not d.recibe_correo,
                              posibles.index(d.dominio)))
    return vivos
