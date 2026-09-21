#!/usr/bin/env python3
"""Recolector de dominios de tiendas españolas.

Responde a la petición nº 9 de Cowork: conseguir dominios en volumen, gratis.

  python3 recolector.py --fuente tranco --limite 5000 --salida datos/dominios.txt
  python3 recolector.py --fuente commoncrawl --salida datos/dominios.txt
  python3 recolector.py --fuente ambas --salida datos/dominios.txt

IMPORTANTE — DÓNDE SE EJECUTA
Este script necesita red abierta. El contenedor de Claude Code tiene un proxy
que deniega los dominios arbitrarios (Common Crawl y Tranco dan 000), y el de
Cowork solo tiene DNS. Así que esto se ejecuta EN EL ORDENADOR DE SARA, que
no tiene esa restricción.

La salida es un fichero de texto plano, un dominio por línea y sin https://,
que es exactamente lo que pidió Cowork para su detector por DNS.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

AGENTE = "RadarRetencion/0.1 (+https://sorasystems.es)"
TRANCO = "https://tranco-list.eu/top-1m.csv.zip"
CC_COLINFO = "https://index.commoncrawl.org/collinfo.json"

# Dominios de servicio, prensa y plataformas: nunca son tiendas candidatas.
BASURA = re.compile(
    r"(google|facebook|instagram|twitter|youtube|tiktok|linkedin|amazon|"
    r"wikipedia|wordpress|blogspot|gob\.es|\.edu\.|elpais|elmundo|marca|"
    r"as\.com|abc\.es|lavanguardia|20minutos|rtve|correos|bbva|santander|"
    r"caixabank|idealista|fotocasa|infojobs|milanuncios|wallapop|booking|"
    r"airbnb|paypal|shopify\.com|myshopify)", re.I)


def _descargar(url: str, timeout: int = 120) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(peticion, timeout=timeout) as r:
        return r.read()


def _limpiar(dominio: str) -> str:
    d = dominio.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0].split(":")[0]
    return d[4:] if d.startswith("www.") else d


def _util(dominio: str) -> bool:
    return (
        bool(dominio)
        and "." in dominio
        and not BASURA.search(dominio)
        and len(dominio) > 4
    )


def de_tranco(limite: int) -> list[str]:
    """Dominios españoles del millón más visitado. Descarga libre, sin clave."""
    print(f"  Descargando Tranco (~20 MB)...", flush=True)
    crudo = _descargar(TRANCO)
    dominios: list[str] = []
    with zipfile.ZipFile(io.BytesIO(crudo)) as z:
        nombre = z.namelist()[0]
        with z.open(nombre) as f:
            texto = io.TextIOWrapper(f, encoding="utf-8")
            for fila in csv.reader(texto):
                if len(fila) < 2:
                    continue
                d = _limpiar(fila[1])
                # .es siempre; .com solo si el nombre sugiere negocio español
                if d.endswith(".es") and _util(d):
                    dominios.append(d)
                    if len(dominios) >= limite:
                        break
    print(f"  Tranco: {len(dominios)} dominios .es")
    return dominios


def de_commoncrawl(limite: int, coleccion: str | None = None) -> list[str]:
    """Dominios .es del índice público de Common Crawl. Gratis y sin clave."""
    if not coleccion:
        print("  Consultando colecciones de Common Crawl...", flush=True)
        info = json.loads(_descargar(CC_COLINFO, timeout=60))
        coleccion = info[0]["id"]
        print(f"  Usando la colección más reciente: {coleccion}")

    url = (f"https://index.commoncrawl.org/{coleccion}-index"
           f"?url=*.es&output=json&limit={limite}")
    print(f"  Descargando índice (puede tardar)...", flush=True)
    vistos: set[str] = set()
    try:
        crudo = _descargar(url, timeout=300).decode("utf-8", "ignore")
    except Exception as e:
        print(f"  ERROR consultando Common Crawl: {e}")
        return []
    for linea in crudo.splitlines():
        try:
            registro = json.loads(linea)
        except Exception:
            continue
        d = _limpiar(registro.get("url", ""))
        if _util(d):
            vistos.add(d)
    print(f"  Common Crawl: {len(vistos)} dominios únicos")
    return sorted(vistos)


def main() -> int:
    p = argparse.ArgumentParser(description="Recolector de dominios españoles")
    p.add_argument("--fuente", choices=["tranco", "commoncrawl", "ambas"],
                   default="tranco")
    p.add_argument("--limite", type=int, default=20_000)
    p.add_argument("--salida", default="datos/dominios.txt")
    p.add_argument("--coleccion", help="colección concreta de Common Crawl")
    args = p.parse_args()

    print("RECOLECTOR DE DOMINIOS\n" + "=" * 50)
    dominios: list[str] = []
    try:
        if args.fuente in ("tranco", "ambas"):
            dominios += de_tranco(args.limite)
        if args.fuente in ("commoncrawl", "ambas"):
            dominios += de_commoncrawl(args.limite, args.coleccion)
    except Exception as e:
        print(f"\nFALLO de red: {e}")
        print("Si ves esto en el contenedor de Claude Code, es lo esperado:")
        print("su proxy deniega estos dominios. Ejecuta el script en tu")
        print("ordenador, donde la red está abierta.")
        return 1

    unicos = sorted(set(dominios))
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(unicos) + "\n", encoding="utf-8")

    print("=" * 50)
    print(f"  {len(unicos)} dominios únicos -> {salida}")
    print(f"\nSiguiente paso, el detector por DNS:")
    print(f"  python3 cli.py adn --entrada {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
