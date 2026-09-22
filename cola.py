#!/usr/bin/env python3
"""Genera la cola de correos para la tabla "Envios Sora" de Airtable.

    python3 cola.py --entrada datos/escribibles.csv

No envía nada. Produce un CSV con las columnas exactas de la tabla, listo
para cargar. El envío lo hace después el escenario de Make leyendo las filas
con Estado = Pendiente, porque el puerto 587 está cerrado tanto en la máquina
de Sara como en el contenedor de CoWork (medido el 22/09/2026).

TRES FILTROS, y ninguno es opcional:

  1. FASE 2      Solo pasan las filas con escribible = 1, es decir, las que
                 no tienen ya un ESP ni un captador de carrito instalado.

  2. DIRECCIÓN   Solo direcciones genéricas de sociedad. La propia tabla lo
                 dice en el campo "Tipo de direccion": las nominativas y las
                 personales NO se envían, son datos de una persona física.

  3. HALLAZGO    Sin "Hallazgo concreto" la fila no se genera. También es
                 regla de la tabla: es lo que convierte el correo en
                 información útil sobre SU tienda y no en publicidad.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from radar.correo import hallazgo
from radar.destinatario import clasificar, escribible as direccion_escribible

# Columnas EXACTAS de "Envios Sora" (app6M2vHgS6ADYGEQ / tblOLbHIvpIQnw9xK),
# comprobadas contra el esquema real el 22/09/2026.
CAMPOS = ["Empresa", "Email", "Web", "FuenteEmail", "Sector", "Asunto",
          "Cuerpo", "Estado", "Linea", "Hallazgo concreto", "Tipo de direccion"]

# CoWork escribió "estado=listo" en su documento 18, pero ese valor no existe
# en la tabla: Estado solo admite Pendiente, Enviado, Respondido, BAJA y
# Pausado. Make recoge las de Pendiente.
ESTADO_INICIAL = "Pendiente"

# La campaña de ecommerce va en su propia línea. El campo avisa de que una
# empresa solo puede estar en UNA línea, nunca en dos.
LINEA = "Auditoria de correo"

VERDADEROS = ("1", "true", "True", "si", "sí")


def _redactar_hallazgo(dominio: str, plataforma: str, captura: bool) -> str:
    """El hecho comprobado sobre ESTA tienda, con fecha. Va a Airtable."""
    partes = [
        f"Comprobado el {date.today().strftime('%d/%m/%Y')} sobre el código de "
        f"la portada de {dominio}: no hay ninguna herramienta de recuperación "
        f"de carrito instalada (ni Klaviyo, ni Mailchimp, ni Connectif, ni "
        f"Brevo) ni captador de carrito."
    ]
    if plataforma:
        partes.append(f"Tienda {plataforma}.")
    partes.append(
        "Sí tiene formulario de captación de correo." if captura
        else "Tampoco tiene formulario de captación de correo."
    )
    return " ".join(partes)


def main() -> int:
    p = argparse.ArgumentParser(description="Cola de correos para Airtable")
    p.add_argument("--entrada", default="datos/escribibles.csv")
    p.add_argument("--salida", default="datos/airtable_envios.csv")
    args = p.parse_args()

    entrada = Path(args.entrada)
    if not entrada.exists():
        print(f"No encuentro {entrada}")
        return 1

    with entrada.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    cola: list[dict[str, str]] = []
    descartes = {"fase2": 0, "direccion": 0, "sin_datos": 0}

    print(f"Procesando {len(filas)} filas de {entrada}\n")

    for fila in filas:
        dominio = (fila.get("dominio") or "").strip()
        destino = (fila.get("correo") or fila.get("email") or "").strip()

        if not dominio or not destino:
            descartes["sin_datos"] += 1
            continue

        if fila.get("escribible") not in VERDADEROS:
            descartes["fase2"] += 1
            continue

        tipo = clasificar(destino)
        if not direccion_escribible(destino):
            print(f"  OMITE  {dominio:34} dirección {tipo.lower()}")
            descartes["direccion"] += 1
            continue

        plataforma = (fila.get("plataforma") or "").strip()
        captura = fila.get("captura_email") in VERDADEROS
        correo = hallazgo(dominio, destino, plataforma, captura)

        cola.append({
            "Empresa": (fila.get("tienda") or fila.get("empresa") or dominio).strip(),
            "Email": destino,
            "Web": f"https://{dominio}",
            "FuenteEmail": (fila.get("fuente_email") or "").strip(),
            "Sector": (fila.get("sector") or "").strip(),
            "Asunto": correo.asunto,
            "Cuerpo": correo.cuerpo,
            "Estado": ESTADO_INICIAL,
            "Linea": LINEA,
            "Hallazgo concreto": _redactar_hallazgo(dominio, plataforma, captura),
            "Tipo de direccion": tipo,
        })
        print(f"  COLA   {dominio:34} -> {destino}")

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(cola)

    print(f"\n{'=' * 62}")
    print(f"EN COLA ................................. {len(cola):4}")
    print(f"descartadas por fase 2 (ya tienen ESP) .. {descartes['fase2']:4}")
    print(f"descartadas por dirección personal ...... {descartes['direccion']:4}")
    print(f"sin dominio o sin correo ................ {descartes['sin_datos']:4}")
    print(f"\nGuardado en {salida}")
    print("\nCárgalo en la tabla Envios Sora. Make recoge las de Estado=Pendiente")
    print("y aplica la rampa diaria. Este script NO envía nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
