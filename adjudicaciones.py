#!/usr/bin/env python3
"""Saca de los feeds de PLACSP los adjudicatarios a los que merece escribir.

    python3 adjudicaciones.py datos/placsp/*.atom

No envía nada ni toca Airtable. Produce un CSV para revisar a mano antes de
cargar nada, porque una adjudicación mal leída es un correo a una empresa
hablándole de un contrato que no es suyo.

EL FILTRO, y por qué cada parte:

  ADJUDICADO    ResultCode 8 o 9. Un desierto no tiene a quién escribir.
  ORGANIZACION  Sociedad, UTE o asociación. Una P es un ayuntamiento: es
                el cliente de nuestro cliente. Un NIF que empieza por
                número es una persona física, y ahí no entramos.
  IMPORTE       De 100.000 a 1.000.000 €. Por debajo no paga el mapa; por
                encima es una empresa con departamento jurídico propio.
  CPV           Familias con ejecución continuada (limpieza, mantenimiento,
                servicios sociales, formación...). Si el contrato se agota
                en una entrega, no hay nada que justificar cada mes.
  UN CONTRATO   Si el expediente tiene más de tres ganadores es un acuerdo
                marco, no un contrato con compromisos propios.
  VIVO          Un contrato que ya terminó no tiene nada que justificar.
  YA ESCRITO    Los cuatro que ya contactamos no se repiten.

LO QUE ESTE FILTRO NO PUEDE HACER, y hay que decirlo: el feed NO trae los
criterios de adjudicación, así que no se puede exigir "al menos un 20 % de
la puntuación no es precio". Eso está en el PCAP. Sale en el CSV el enlace
al expediente para mirarlo, que es el trabajo que se cobra.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from radar.placsp import ADJUDICADOS, Adjudicacion, leer

IMPORTE_MIN = 100_000
IMPORTE_MAX = 1_000_000

# Si un mismo expediente tiene muchos ganadores, no es un contrato: es un
# acuerdo marco o un sistema dinámico, donde entran todos los que cumplen.
# Ahí no hay compromisos propios que justificar cada mes, que es lo que
# vendemos. Medido en el feed del 25/08: 12 de las 32 candidatas salían de
# un solo expediente de consultoría con 17 ofertas admitidas.
MAX_GANADORES = 3

# Ya contactados el 23/09/2026. No se les vuelve a escribir por esta vía.
YA_ESCRITOS = {"actua", "stv", "limcamar", "vareser"}

CAMPOS = ["Empresa", "NIF", "Tipo", "Expediente", "Objeto", "Lote", "Organismo",
          "Importe", "Presupuesto", "CPV", "Ofertas", "GanadoresExpediente", "FechaContrato",
          "Inicio", "Fin", "Region", "Enlace"]


def _importe_util(a: Adjudicacion) -> float | None:
    """El del lote; si viene a cero (acuerdos marco, sistemas dinámicos),
    el presupuesto del expediente. Si no hay ninguno, no hay importe: no se
    inventa."""
    if a.importe and a.importe > 0:
        return a.importe
    if a.presupuesto and a.presupuesto > 0:
        return a.presupuesto
    return None


def _ya_escrito(nombre: str) -> bool:
    n = nombre.lower()
    return any(m in n for m in YA_ESCRITOS)


def filtrar(todas: list[Adjudicacion], hoy: date | None = None) -> tuple[list[dict], Counter]:
    motivos = Counter()
    buenas: list[dict] = []
    hoy = hoy or date.today()

    ganadores = Counter(a.expediente for a in todas
                        if a.resultado in ADJUDICADOS and a.nif)

    for a in todas:
        if a.resultado not in ADJUDICADOS:
            motivos["no adjudicado"] += 1
            continue
        if not a.adjudicatario or not a.nif:
            motivos["sin adjudicatario identificado"] += 1
            continue
        if a.es_publico:
            motivos["el ganador es un organismo publico"] += 1
            continue
        if not a.es_escribible:
            motivos[f"no es organizacion ({a.tipo_entidad or 'sin NIF'})"] += 1
            continue
        if _ya_escrito(a.adjudicatario):
            motivos["ya contactado"] += 1
            continue
        if not a.cpv_interesante:
            motivos["CPV sin ejecucion continuada"] += 1
            continue
        if ganadores[a.expediente] > MAX_GANADORES:
            motivos["acuerdo marco (muchos ganadores)"] += 1
            continue
        if a.fin:
            try:
                if date.fromisoformat(a.fin[:10]) < hoy:
                    motivos["contrato ya terminado"] += 1
                    continue
            except ValueError:
                pass

        importe = _importe_util(a)
        if importe is None:
            motivos["sin importe en el feed"] += 1
            continue
        if not (IMPORTE_MIN <= importe <= IMPORTE_MAX):
            motivos["fuera del rango de importe"] += 1
            continue

        buenas.append({
            "Empresa": a.adjudicatario, "NIF": a.nif, "Tipo": a.tipo_entidad,
            "Expediente": a.expediente, "Objeto": a.objeto,
            "Lote": a.objeto_lote or a.lote, "Organismo": a.organismo_padre or a.organismo,
            "Importe": f"{importe:.2f}",
            "Presupuesto": f"{a.presupuesto:.2f}" if a.presupuesto else "",
            "CPV": a.cpv, "Ofertas": a.ofertas or "",
            "GanadoresExpediente": ganadores[a.expediente],
            "FechaContrato": a.fecha_contrato, "Inicio": a.inicio, "Fin": a.fin,
            "Region": a.region, "Enlace": a.enlace,
        })

    return buenas, motivos


def main() -> int:
    p = argparse.ArgumentParser(description="Adjudicatarios desde PLACSP")
    p.add_argument("ficheros", nargs="+")
    p.add_argument("--salida", default="datos/adjudicatarios.csv")
    args = p.parse_args()

    todas: list[Adjudicacion] = []
    for f in args.ficheros:
        ruta = Path(f)
        if not ruta.exists():
            print(f"  no encuentro {ruta}")
            continue
        leidas = leer(ruta)
        print(f"  {ruta.name}: {len(leidas)} adjudicaciones")
        todas += leidas

    # Un mismo contrato reaparece en varios ficheros y en varios días cuando
    # el órgano lo actualiza. Aviso de CoWork, y se nota: sin esto la misma
    # adjudicación cuenta dos veces y falsea el embudo. Clave: expediente +
    # lote + NIF; nos quedamos con la de fecha de contrato más reciente.
    antes = len(todas)
    unicas_adj: dict[tuple, Adjudicacion] = {}
    for a in todas:
        clave = (a.expediente, a.lote, a.nif)
        previa = unicas_adj.get(clave)
        if previa is None or (a.fecha_contrato or "") > (previa.fecha_contrato or ""):
            unicas_adj[clave] = a
    todas = list(unicas_adj.values())
    if antes != len(todas):
        print(f"  repetidas entre ficheros: {antes - len(todas)}")

    buenas, motivos = filtrar(todas)

    # una empresa puede ganar varios lotes: se escribe una vez
    vistas, unicas = set(), []
    for b in buenas:
        if b["NIF"] in vistas:
            continue
        vistas.add(b["NIF"])
        unicas.append(b)

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(unicas)

    print(f"\n{'=' * 64}")
    print(f"adjudicaciones leidas ............... {len(todas):5}")
    for motivo, n in motivos.most_common():
        print(f"  descartadas · {motivo:.<40} {n:5}")
    print(f"pasan el filtro ..................... {len(buenas):5}")
    print(f"empresas distintas .................. {len(unicas):5}")
    print(f"\nGuardado en {salida}")
    print("\nEsto NO se carga en Airtable todavía: falta mirar en el PCAP")
    print("cuánto de la puntuación no era precio, que el feed no lo trae.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
