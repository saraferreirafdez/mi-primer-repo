#!/usr/bin/env python3
"""Enviador del correo de hallazgo, con ritmo y con freno de mano.

  python3 enviar.py --entrada datos/escribibles.csv             # SIMULACRO
  python3 enviar.py --entrada datos/escribibles.csv --redactar  # deja los .eml
  python3 enviar.py --entrada datos/escribibles.csv --enviar    # envía de verdad

POR DEFECTO NO ENVÍA NADA. Imprime lo que haría. Hay que pasar --enviar
explícitamente. Esto escribe a empresas reales: un fallo aquí no se deshace.

Protecciones, todas activas siempre:

  TOPE DIARIO    Arranca en 10 y sube poco a poco. Un dominio nuevo que
                 manda 100 correos el primer día acaba en spam y se lleva
                 por delante la reputación del dominio para siempre.

  SIN REPETIR    Cada envío queda registrado. Nunca se escribe dos veces a
                 la misma tienda, ni aunque se vuelva a pasar la lista.

  BAJAS          Se comprueba la lista de bajas antes de cada envío. Quien
                 pide no recibir más, no recibe más. Sin excepciones.

  PAUSA          Entre 40 y 90 segundos entre correos. Cien correos seguidos
                 en diez minutos es la firma de un robot y lo detectan.
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import smtplib
import sqlite3
import sys
import time
from datetime import date, datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from radar.correo import Correo, hallazgo

BASE = Path("datos/envios.db")
BAJAS = Path("datos/bajas.txt")
REDACTADOS = Path("datos/redactados")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS envios (
    dominio TEXT PRIMARY KEY, correo TEXT, asunto TEXT, plantilla TEXT,
    enviado_en TEXT, estado TEXT, error TEXT
);
"""

# Rampa de calentamiento. Un dominio de envío nuevo necesita construir
# reputación poco a poco: si el primer día salen 100 correos, el filtro de
# spam lo marca y ya no hay vuelta atrás.
RAMPA = {1: 10, 2: 10, 3: 15, 4: 15, 5: 20, 6: 25, 7: 30}
TOPE_MAXIMO = 40


def abrir() -> sqlite3.Connection:
    BASE.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(BASE)
    c.executescript(ESQUEMA)
    return c


def ya_enviado(c: sqlite3.Connection, dominio: str) -> bool:
    fila = c.execute("SELECT 1 FROM envios WHERE dominio = ? AND estado = 'enviado'",
                     (dominio,)).fetchone()
    return fila is not None


def enviados_hoy(c: sqlite3.Connection) -> int:
    hoy = date.today().isoformat()
    return c.execute(
        "SELECT COUNT(*) FROM envios WHERE estado = 'enviado' AND enviado_en LIKE ?",
        (f"{hoy}%",)).fetchone()[0]


def dias_enviando(c: sqlite3.Connection) -> int:
    filas = c.execute(
        "SELECT COUNT(DISTINCT substr(enviado_en, 1, 10)) FROM envios "
        "WHERE estado = 'enviado'").fetchone()
    return (filas[0] or 0) + 1


def cargar_bajas() -> set[str]:
    """Correos y dominios que han pedido no recibir más. Se respetan siempre."""
    if not BAJAS.exists():
        return set()
    return {l.strip().lower() for l in BAJAS.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")}


def registrar(c: sqlite3.Connection, correo: Correo, estado: str, error: str = "") -> None:
    c.execute("INSERT OR REPLACE INTO envios VALUES (?,?,?,?,?,?,?)",
              (correo.dominio, correo.para, correo.asunto, correo.plantilla,
               datetime.now(timezone.utc).isoformat(timespec="seconds"), estado, error))
    c.commit()


def construir(correo: Correo, remitente: str) -> EmailMessage:
    """Arma el mensaje. Lo comparten el envío por SMTP y la redacción a fichero."""
    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["To"] = correo.para
    mensaje["Subject"] = correo.asunto
    mensaje["Date"] = formatdate(localtime=True)
    # Las respuestas vuelven a la dirección que Sara ya lee, aunque el envío
    # salga de otro sitio.
    mensaje["Reply-To"] = os.environ.get("RADAR_RESPUESTAS", remitente)
    mensaje.set_content(correo.cuerpo)

    if correo.adjunto and Path(correo.adjunto).exists():
        datos = Path(correo.adjunto).read_bytes()
        mensaje.add_attachment(datos, maintype="application", subtype="pdf",
                               filename=Path(correo.adjunto).name)
    return mensaje


def redactar_fichero(correo: Correo, remitente: str, orden: int) -> Path:
    """Escribe el correo como .eml, listo para abrir y enviar a mano.

    Es la vía para cuando el puerto 587 está cerrado: un .eml se abre con
    doble clic en cualquier cliente de correo, ya relleno, y solo hay que
    darle a enviar. Las protecciones son las mismas: si una tienda está de
    baja o ya se le escribió, aquí ni se le redacta el fichero.
    """
    REDACTADOS.mkdir(parents=True, exist_ok=True)
    nombre = correo.dominio.replace(".", "_")
    ruta = REDACTADOS / f"{orden:03d}_{nombre}.eml"
    ruta.write_bytes(bytes(construir(correo, remitente)))
    return ruta


def mandar_smtp(correo: Correo, remitente: str) -> None:
    """Envío por SMTP. Credenciales siempre desde el entorno, nunca en el código."""
    servidor = os.environ["RADAR_SMTP_SERVIDOR"]
    puerto = int(os.environ.get("RADAR_SMTP_PUERTO", "587"))
    usuario = os.environ["RADAR_SMTP_USUARIO"]
    clave = os.environ["RADAR_SMTP_CLAVE"]
    mensaje = construir(correo, remitente)

    with smtplib.SMTP(servidor, puerto, timeout=30) as s:
        s.starttls()
        s.login(usuario, clave)
        s.send_message(mensaje)


def main() -> int:
    p = argparse.ArgumentParser(description="Enviador del correo de hallazgo")
    p.add_argument("--entrada", default="datos/escribibles.csv")
    p.add_argument("--enviar", action="store_true",
                   help="ENVÍA DE VERDAD por SMTP. Sin esto solo simula.")
    p.add_argument("--redactar", action="store_true",
                   help="No envía: deja los correos como .eml listos para mandar.")
    p.add_argument("--tope", type=int, help="fuerza el tope diario")
    p.add_argument("--remitente", default=os.environ.get("RADAR_REMITENTE", ""))
    args = p.parse_args()

    conexion = abrir()
    bajas = cargar_bajas()
    dia = dias_enviando(conexion)
    tope = args.tope or min(RAMPA.get(dia, TOPE_MAXIMO), TOPE_MAXIMO)
    restantes = max(tope - enviados_hoy(conexion), 0)

    if args.enviar:
        modo = "ENVÍO REAL"
    elif args.redactar:
        modo = "REDACCIÓN A FICHERO (no se envía nada)"
    else:
        modo = "SIMULACRO (no se envía nada)"
    print(f"{modo}\n{'=' * 62}")
    print(f"Día {dia} de envío · tope hoy {tope} · ya enviados {enviados_hoy(conexion)}"
          f" · quedan {restantes}\n")

    if (args.enviar or args.redactar) and not args.remitente:
        print("FALTA el remitente. Define RADAR_REMITENTE o usa --remitente.")
        print("Usa un subdominio de envío (ej. hola@correo.sorasystems.es),")
        print("NO info@sorasystems.es: el correo en frío quema la reputación")
        print("del dominio principal y luego no llegan ni las facturas.")
        return 1

    with Path(args.entrada).open(encoding="utf-8") as f:
        filas = [x for x in csv.DictReader(f) if x.get("escribible") in ("1", "true", "True")]

    hechos = saltados = 0
    indice: list[tuple[str, str, str]] = []
    for fila in filas:
        if hechos >= restantes:
            print(f"\nTope diario alcanzado. El resto, mañana.")
            break

        dominio = (fila.get("dominio") or "").strip()
        destino = (fila.get("correo") or "").strip()
        if not dominio or not destino:
            continue
        if destino.lower() in bajas or dominio.lower() in bajas:
            print(f"  BAJA     {dominio:34} pidió no recibir más")
            saltados += 1
            continue
        if ya_enviado(conexion, dominio):
            saltados += 1
            continue

        correo = hallazgo(dominio, destino, fila.get("plataforma", ""),
                          fila.get("captura_email") in ("1", "true", "True"))

        if args.redactar:
            ruta = redactar_fichero(correo, args.remitente, hechos + 1)
            registrar(conexion, correo, "redactado")
            indice.append((destino, correo.asunto, ruta.name))
            print(f"  REDACTA  {dominio:34} -> {ruta.name}")
            hechos += 1
            continue

        if not args.enviar:
            print(f"  SIMULA   {dominio:34} -> {destino:32} \"{correo.asunto}\"")
            hechos += 1
            continue

        try:
            mandar_smtp(correo, args.remitente)
            registrar(conexion, correo, "enviado")
            print(f"  ENVIADO  {dominio:34} -> {destino}")
            hechos += 1
            time.sleep(random.uniform(40, 90))
        except Exception as e:
            registrar(conexion, correo, "fallo", str(e)[:200])
            print(f"  FALLO    {dominio:34} {str(e)[:60]}")

    if indice:
        ruta_indice = REDACTADOS / "_indice.csv"
        with ruta_indice.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["para", "asunto", "fichero"])
            w.writerows(indice)
        print(f"\nÍndice en {ruta_indice}")

    print(f"\n{'=' * 62}")
    etiqueta = "Enviados" if args.enviar else ("Redactados" if args.redactar else "Simulados")
    print(f"{etiqueta}: {hechos} · saltados: {saltados}")
    if args.redactar:
        print(f"\nLos .eml están en {REDACTADOS}/. Se abren con doble clic en")
        print("cualquier cliente de correo, ya rellenos: solo hay que enviarlos.")
    elif not args.enviar:
        print("\nEsto ha sido un simulacro. Revisa la lista de arriba y, si está")
        print("bien, repite el comando añadiendo --enviar (o --redactar).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
