#!/usr/bin/env python3
"""Comprueba que el buzon del robot esta bien montado, antes de usarlo.

    python3 comprobar_buzon.py

Verifica cuatro cosas, en orden, y se para en la primera que falle:
  1. que las variables de entorno estan puestas
  2. que el servidor IMAP acepta las credenciales
  3. que existe la carpeta donde deben caer los correos del robot
  4. que las subetiquetas (info+algo@) llegan de verdad

El paso 4 es el unico que no se puede comprobar solo: hay que mandar un
correo de prueba a mano. El script dice exactamente a que direccion.
"""

from __future__ import annotations

import imaplib
import os
import sys

from radar.alias import alias_para

VARIABLES = ["RADAR_ALIAS_BASE", "RADAR_IMAP_SERVIDOR",
             "RADAR_IMAP_USUARIO", "RADAR_IMAP_CLAVE"]


def main() -> int:
    print("COMPROBACION DEL BUZON DEL ROBOT\n" + "=" * 50)

    # --- 1. Variables -------------------------------------------------------
    faltan = [v for v in VARIABLES if not os.environ.get(v)]
    if faltan:
        print("  FALLO  faltan variables de entorno:")
        for v in faltan:
            print(f"           {v}")
        print("\n  Ponlas asi (en tu terminal, o en un fichero .env):")
        print('    export RADAR_ALIAS_BASE="info@sorasystems.es"')
        print('    export RADAR_IMAP_SERVIDOR="imap.tuproveedor.com"')
        print('    export RADAR_IMAP_USUARIO="info@sorasystems.es"')
        print('    export RADAR_IMAP_CLAVE="..."')
        return 1
    print("  OK     las cuatro variables estan puestas")

    servidor = os.environ["RADAR_IMAP_SERVIDOR"]
    usuario = os.environ["RADAR_IMAP_USUARIO"]
    clave = os.environ["RADAR_IMAP_CLAVE"]
    carpeta = os.environ.get("RADAR_IMAP_CARPETA", "Auditorias")

    # --- 2. Conexion --------------------------------------------------------
    try:
        conexion = imaplib.IMAP4_SSL(servidor)
    except Exception as e:
        print(f"  FALLO  no se puede conectar a {servidor}: {e}")
        print("         Revisa el nombre del servidor IMAP de tu proveedor.")
        return 1
    print(f"  OK     conecta con {servidor}")

    try:
        conexion.login(usuario, clave)
    except Exception as e:
        print(f"  FALLO  el servidor rechaza las credenciales: {e}")
        print("         Si tu proveedor tiene verificacion en dos pasos,")
        print("         necesitas una CLAVE DE APLICACION, no tu contrasena.")
        return 1
    print(f"  OK     entra como {usuario}")

    # --- 3. Carpeta ---------------------------------------------------------
    estado, carpetas = conexion.list()
    nombres = [c.decode(errors="ignore") for c in (carpetas or [])]
    if not any(f'"{carpeta}"' in n or n.endswith(carpeta) for n in nombres):
        print(f"  AVISO  no existe la carpeta '{carpeta}'")
        print("         Creala en tu correo y manda alli todo lo dirigido a")
        print(f"         {os.environ['RADAR_ALIAS_BASE'].replace('@', '+*@')}")
        print("         Si no, los correos del robot taparan tu bandeja real.")
    else:
        print(f"  OK     existe la carpeta '{carpeta}'")

    # --- 4. Subetiquetas ----------------------------------------------------
    alias = alias_para("https://tienda-de-prueba.es")
    print("\n" + "=" * 50)
    print("ULTIMO PASO, A MANO:")
    print(f"  Mandate un correo desde cualquier cuenta a esta direccion:\n")
    print(f"      {alias}\n")
    print(f"  Si llega a la carpeta '{carpeta}', el buzon esta listo.")
    print("  Si no llega, tu proveedor no admite subetiquetas y hay que")
    print("  activar catch-all en el dominio.")
    conexion.logout()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
