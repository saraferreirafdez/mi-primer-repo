#!/usr/bin/env python3
"""Cruza los correos verificados con los expedientes y saca los hallazgos.

Solo entran las empresas cuyo correo está comprobado contra su NIF, y solo
salen los contratos que dan un hallazgo concreto. Lo normal es que la
mayoría no salga: eso es el filtro funcionando, no un fallo.

Uso:  python3 hallazgos_adjudicatarias.py            ver los correos
      python3 hallazgos_adjudicatarias.py --csv      escribir el CSV
"""
import csv
import sys
from pathlib import Path

from radar.contrato import Contrato, FUERA_DE_PERFIL, correo_contrato, hallazgo

RAIZ = Path(__file__).parent
CORREOS = RAIZ / "datos" / "adjudicatarios_correos.csv"
EXPEDIENTES = RAIZ / "datos" / "expedientes.csv"
SALIDA = RAIZ / "datos" / "hallazgos_adjudicatarias.csv"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def cargar():
    correos = {r["NIF"]: r for r in csv.DictReader(CORREOS.open(encoding="utf-8"))
               if r["Correo"]}
    vistos, contratos = set(), []
    for r in csv.DictReader(EXPEDIENTES.open(encoding="utf-8")):
        if r["nif"] not in correos:
            continue
        # El feed publica la misma adjudicación más de una vez (Rodi salía
        # dos veces idéntica). Sin esto se escribiría dos correos iguales.
        clave = (r["nif"], r["expediente"], r["lote"])
        if clave in vistos:
            continue
        vistos.add(clave)
        contratos.append((Contrato(
            nif=r["nif"], empresa=correos[r["nif"]]["Empresa"],
            expediente=r["expediente"], objeto=r["objeto"], organismo=r["organismo"],
            base=num(r["base"]), adjudicado=num(r["adjudicado"]),
            licitadores=int(r["licitadores"]) if r["licitadores"].isdigit() else 0,
            duracion=r["duracion"], duracion_ud=r["duracion_ud"], lote=r["lote"],
            enlace=r["enlace"]), correos[r["nif"]]["Correo"]))
    return contratos


def fuerza(h):
    """Para quedarnos con el mejor hallazgo de cada empresa.

    Manda la baja, porque es el dato que le duele a quien lo lee; si no
    hay baja, manda el número de licitadores.
    """
    b = h.contrato.baja_pct
    return (1, b) if b is not None and h.tipo == "baja" else (0, h.contrato.licitadores)


def main():
    contratos = cargar()
    con, sin, fuera = [], [], []
    for c, destino in contratos:
        if c.nif in FUERA_DE_PERFIL:
            fuera.append((c, FUERA_DE_PERFIL[c.nif]))
            continue
        h = hallazgo(c)
        (con if h else sin).append((c, destino, h))

    # UN correo por EMPRESA, no por contrato. Imrepol tenía dos contratos
    # con hallazgo y se le habrían escrito dos correos en frío el mismo día,
    # que es la forma más rápida de parecer un robot.
    mejor = {}
    for c, destino, h in con:
        if c.nif not in mejor or fuerza(h) > fuerza(mejor[c.nif][2]):
            mejor[c.nif] = (c, destino, h)
    descartados = len(con) - len(mejor)
    con = list(mejor.values())

    print(f"{len(contratos)} adjudicaciones de empresas con correo comprobado")
    print(f"  {len(con):>2} empresas con hallazgo · {len(sin):>2} sin nada concreto que decir"
          f" · {len(fuera):>2} fuera de perfil")
    if descartados:
        print(f"  ({descartados} contrato(s) descartado(s): su empresa ya tenía uno mejor)")
    print()

    for c, destino, h in sorted(con, key=lambda x: -(x[0].adjudicado or 0)):
        correo = correo_contrato(c, destino)
        print("=" * 74)
        print(f"PARA: {destino}   ({c.empresa})")
        print(f"HALLAZGO ({h.tipo}): {h.titular}")
        print(f"ASUNTO: {correo.asunto}")
        print("=" * 74)
        print(correo.cuerpo)
        print()

    print("=" * 74)
    print("SIN HALLAZGO, y por qué no se les escribe:")
    for c, _, _ in sorted(sin, key=lambda x: -(x[0].adjudicado or 0)):
        b = c.baja_pct
        razon = (f"baja de solo {b:.1f}%" if b is not None else "es un lote: sin baja calculable")
        print(f"  {c.empresa[:38]:<40} {c.licitadores} licitadores · {razon}")
    print("\nFUERA DE PERFIL:")
    for c, motivo in fuera:
        print(f"  {c.empresa[:38]:<40} {motivo}")

    if "--csv" in sys.argv:
        with SALIDA.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["NIF", "Empresa", "Correo", "Expediente", "Organismo",
                        "Importe", "Tipo", "Hallazgo", "Asunto", "Cuerpo"])
            for c, destino, h in con:
                co = correo_contrato(c, destino)
                w.writerow([c.nif, c.empresa, destino, c.expediente, c.organismo,
                            c.adjudicado, h.tipo, h.titular, co.asunto, co.cuerpo])
        print(f"\nEscrito {SALIDA} con {len(con)} filas")


if __name__ == "__main__":
    main()
