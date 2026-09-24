#!/usr/bin/env python3
"""Busca el dominio de cada adjudicatario del CSV, comprobándolo por DNS.

    python3 dominios_adjudicatarios.py

Lee datos/adjudicatarios.csv y escribe datos/adjudicatarios_dominios.csv con
los dominios que EXISTEN de verdad y los que además reciben correo.

Esto NO da el correo. Da el dominio, que es el 80 % del trabajo: quien
tenga navegador solo tiene que abrir el aviso legal de ese dominio,
comprobar que aparece el mismo NIF y copiar la dirección de contacto.

Y hace falta comprobar el NIF, no basta con que el nombre pegue. Para
«GRUPO CONTROL EMPRESA DE SEGURIDAD» salen control.es y control.com, que
existen y reciben correo y no son suyos. Por eso cada fila lleva su
fiabilidad: alta = el dominio recoge todo el nombre comercial.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from radar.dominio import buscar

ENTRADA = Path("datos/adjudicatarios.csv")
SALIDA = Path("datos/adjudicatarios_dominios.csv")

CAMPOS = ["Empresa", "NIF", "Importe", "Region", "Dominio", "Fiabilidad",
          "RecibeCorreo", "MX", "OtrosCandidatos", "Expediente", "Enlace"]


def _una(fila: dict) -> dict:
    encontrados = buscar(fila["Empresa"], fila.get("Region", ""))
    mejor = encontrados[0] if encontrados else None
    otros = [d.dominio for d in encontrados[1:4]]
    return {
        "Empresa": fila["Empresa"], "NIF": fila["NIF"],
        "Importe": fila["Importe"], "Region": fila.get("Region", ""),
        "Dominio": mejor.dominio if mejor else "",
        "Fiabilidad": mejor.fiabilidad if mejor else "sin candidato",
        "RecibeCorreo": "si" if mejor and mejor.recibe_correo else "no",
        "MX": mejor.mx[0] if mejor and mejor.mx else "",
        "OtrosCandidatos": " · ".join(otros),
        "Expediente": fila.get("Expediente", ""), "Enlace": fila.get("Enlace", ""),
    }


def main() -> int:
    if not ENTRADA.exists():
        print(f"No encuentro {ENTRADA}. Lanza antes adjudicaciones.py")
        return 1

    with ENTRADA.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    print(f"Buscando dominio de {len(filas)} empresas...\n")

    with ThreadPoolExecutor(max_workers=6) as pool:
        salida = list(pool.map(_una, filas))

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(salida)

    cuenta = Counter(r["Fiabilidad"] for r in salida)
    con_correo = sum(1 for r in salida if r["RecibeCorreo"] == "si")
    listos = sum(1 for r in salida
                 if r["Fiabilidad"] == "alta" and r["RecibeCorreo"] == "si")

    for r in sorted(salida, key=lambda x: (x["Fiabilidad"] != "alta",
                                           x["RecibeCorreo"] != "si")):
        marca = {"alta": "OK  ", "media": "DUDA", "baja": "DUDA"}.get(r["Fiabilidad"], "----")
        print(f"  {marca} {r['Empresa'][:38]:40} {r['Dominio'] or '(ninguno)':28} "
              f"{'correo' if r['RecibeCorreo'] == 'si' else '      '}")

    print(f"\n{'=' * 66}")
    for k, v in cuenta.most_common():
        print(f"  fiabilidad {k:.<20} {v:3}")
    print(f"  con dominio que recibe correo .. {con_correo:3}")
    print(f"  LISTOS para abrir el aviso legal {listos:3}")
    print(f"\nGuardado en {SALIDA}")
    print("\nEl correo NO sale de aquí: hay que abrir el aviso legal de cada")
    print("dominio y comprobar que aparece el mismo NIF antes de escribir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
