#!/usr/bin/env python3
"""Radar de Retencion — linea de comandos.

  python3 cli.py detectar --entrada datos/tiendas.csv --salida datos/clasificadas.csv
  python3 cli.py sondear  --url https://tienda.es
  python3 cli.py informar --url https://tienda.es [--visitas 30000 --ticket 60]
  python3 cli.py demo

La etapa `detectar` es la unica que no necesita ni buzon ni navegador, y es
la que hay que correr primero sobre toda la lista de candidatas.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from radar import almacen
from radar.alias import alias_para
from radar.adn import analizar_lote
from radar.detectar import detectar, detectar_lote
from radar.informe import generar
from radar.modelos import Auditoria, Tienda
from radar.rubrica import estimar, puntuar
from radar.verificar import verificar_lote
from radar.sonda import pausa_educada, sondear

ORDEN_PRIORIDAD = {"maxima": 0, "media": 1, "baja": 2, "error": 3}


def _leer_urls(ruta: Path) -> list[str]:
    urls: list[str] = []
    with ruta.open(encoding="utf-8") as f:
        for fila in csv.reader(f):
            if fila and fila[0].strip() and not fila[0].startswith("#"):
                urls.append(fila[0].strip())
    return urls


def cmd_detectar(args) -> int:
    urls = _leer_urls(Path(args.entrada))
    print(f"Analizando {len(urls)} tiendas con {args.hilos} hilos...\n")
    conexion = almacen.abrir()
    resultados = []
    for d in detectar_lote(urls, hilos=args.hilos):
        almacen.guardar_deteccion(conexion, d)
        resultados.append(d)
        marca = {"maxima": "***", "media": " * ", "baja": "   ", "error": " ! "}[d.prioridad]
        print(f"{marca} {d.url[:46]:48} {d.plataforma or '-':13} "
              f"{d.esp or 'sin ESP':14} {d.error[:28]}")

    resultados.sort(key=lambda d: ORDEN_PRIORIDAD[d.prioridad])
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["url", "prioridad", "plataforma", "esp",
                           "captura_email", "secundarios", "error"])
        for d in resultados:
            escritor.writerow([d.url, d.prioridad, d.plataforma, d.esp,
                               int(d.captura_email), "|".join(d.esp_secundarios), d.error])

    conteo = {p: sum(1 for d in resultados if d.prioridad == p)
              for p in ORDEN_PRIORIDAD}
    print(f"\n{'=' * 62}")
    print(f"PRIORIDAD MAXIMA (migrables: Mailchimp/Brevo/AC) .. {conteo['maxima']:4}")
    print(f"PRIORIDAD MEDIA  (sin ESP) ........................ {conteo['media']:4}")
    print(f"PRIORIDAD BAJA   (ya en Klaviyo) .................. {conteo['baja']:4}")
    print(f"ERRORES ........................................... {conteo['error']:4}")
    print(f"\nGuardado en {salida}. Empieza por las de prioridad maxima.")
    return 0


def cmd_adn(args) -> int:
    """Prefiltro por DNS: gratis, ~20 dominios/segundo, sin bajar HTML."""
    dominios = [l.strip() for l in Path(args.entrada).read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
    print(f"Consultando el DNS de {len(dominios)} dominios...\n")
    filas, conteo = [], {1: 0, 2: 0, 3: 0}
    confirmadas = pendientes = errores = 0

    for a in analizar_lote(dominios, hilos=args.hilos):
        if a.error:
            errores += 1
            continue
        conteo[a.grupo] += 1
        if a.es_tienda:
            confirmadas += 1
        elif a.necesita_html:
            pendientes += 1
        filas.append(a)
        if a.grupo == 1:
            print(f"  G1  {a.dominio:34} {a.esp:15} {a.estado}")

    filas.sort(key=lambda a: (a.grupo, not a.es_tienda, a.dominio))
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dominio", "grupo", "plataforma", "esp", "estado",
                    "es_tienda", "necesita_html", "evidencia", "nota"])
        for a in filas:
            w.writerow([a.dominio, a.grupo, a.plataforma, a.esp, a.estado,
                        int(a.es_tienda), int(a.necesita_html), a.evidencia, a.nota])

    print(f"\n{'=' * 62}")
    print(f"GRUPO 1  migrables (Mailchimp, Brevo...) .... {conteo[1]:5}  <- empieza por aqui")
    print(f"GRUPO 2  sin huella de marketing ............ {conteo[2]:5}")
    print(f"GRUPO 3  ya tienen Klaviyo .................. {conteo[3]:5}")
    print(f"\nShopify confirmado por DNS .................. {confirmadas:5}")
    print(f"Sin confirmar (pasan a `detectar`) .......... {pendientes:5}")
    print(f"Errores de DNS .............................. {errores:5}")
    print(f"\nGuardado en {salida}")
    return 0


def cmd_verificar(args) -> int:
    """Fase 2: confirma por el codigo de la portada. Quita los falsos positivos."""
    ruta = Path(args.entrada)
    if ruta.suffix == ".csv":
        with ruta.open(encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
        campo = next((c for c in ("dominio", "url", "web") if filas and c in filas[0]), None)
        if not campo:
            print(f"No encuentro columna de dominio en {ruta}")
            return 1
        dominios = [f[campo].strip() for f in filas if f.get(campo, "").strip()]
    else:
        dominios = [l.strip() for l in ruta.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")]

    print(f"Verificando el codigo de {len(dominios)} tiendas...\n")
    escribibles, descartadas, fallidas = [], [], []
    for v in verificar_lote(dominios, hilos=args.hilos):
        if v.error:
            fallidas.append(v)
        elif v.escribible:
            escribibles.append(v)
            print(f"  OK       {v.dominio:36} {v.plataforma or '-':13} escribible")
        else:
            descartadas.append(v)
            print(f"  DESCARTA {v.dominio:36} {v.motivo[:44]}")

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dominio", "plataforma", "escribible", "motivo",
                    "esps", "captadores", "captura_email"])
        for v in escribibles + descartadas + fallidas:
            w.writerow([v.dominio, v.plataforma, int(v.escribible), v.motivo,
                        "|".join(v.esps), "|".join(v.captadores), int(v.captura_email)])

    total = len(escribibles) + len(descartadas)
    tasa = (len(descartadas) / total * 100) if total else 0
    print(f"\n{'=' * 62}")
    print(f"ESCRIBIBLES (sin sistema de recuperacion) ... {len(escribibles):4}")
    print(f"DESCARTADAS (ya tienen algo puesto) ........ {len(descartadas):4}  ({tasa:.1f}% falsos positivos)")
    print(f"NO VERIFICABLES (fallo de red) ............. {len(fallidas):4}")
    print(f"\nGuardado en {salida}")
    print("Solo se escribe a las escribibles. Las demas ya tienen el sistema.")
    return 0


def cmd_sondear(args) -> int:
    conexion = almacen.abrir()
    urls = [args.url] if args.url else _leer_urls(Path(args.entrada))
    Path("informes/capturas").mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(urls):
        alias = alias_para(url)
        print(f"[{i + 1}/{len(urls)}] {url}\n    alias: {alias}")
        s = sondear(url, alias, carpeta_capturas="informes/capturas",
                    identificarse=args.identificarse)
        almacen.guardar_sonda(conexion, s)
        print(f"    {'OK' if s.valida else 'FALLO'}  "
              f"suscrito={s.suscrito} checkout={s.checkout_alcanzado} "
              f"email={s.email_introducido} {s.error}")
        if i < len(urls) - 1:
            pausa_educada()
    return 0


def _construir_auditoria(url: str, correos=None) -> Auditoria:
    auditoria = Auditoria(tienda=Tienda(url=url))
    auditoria.deteccion = detectar(url)
    auditoria.correos = correos or []
    auditoria.puntuacion, auditoria.hallazgos = puntuar(auditoria)
    return auditoria


def cmd_informar(args) -> int:
    auditoria = _construir_auditoria(args.url)
    estimacion = estimar(auditoria.puntuacion, visitas_mes=args.visitas,
                         tasa_conversion=args.conversion, ticket_medio=args.ticket)
    auditoria.euros_perdidos_mes = estimacion.euros_perdidos_mes

    Path("informes").mkdir(exist_ok=True)
    nombre = auditoria.tienda.dominio().replace(".", "_")
    ruta = f"informes/{nombre}.pdf"
    generar(auditoria, estimacion, ruta, cifras_reales=args.cifras_reales)

    almacen.guardar_informe(almacen.abrir(), auditoria, ruta,
                            datetime.now(timezone.utc).isoformat(timespec="seconds"))
    print(f"Puntuacion: {auditoria.puntuacion}/100")
    print(f"Perdidas estimadas: {estimacion.euros_perdidos_mes:,.0f} EUR/mes")
    print(f"Informe: {ruta}")
    return 0


def cmd_demo(args) -> int:
    """Genera un informe de ejemplo sin tocar ninguna tienda real."""
    auditoria = Auditoria(tienda=Tienda(url="https://tienda-ejemplo.es",
                                        nombre="Tienda de Ejemplo"))
    auditoria.deteccion = detectar("http://localhost:8777/")
    auditoria.deteccion.url = "https://tienda-ejemplo.es"
    auditoria.puntuacion, auditoria.hallazgos = puntuar(auditoria)
    estimacion = estimar(auditoria.puntuacion, visitas_mes=30_000,
                         tasa_conversion=0.018, ticket_medio=60.0)
    auditoria.euros_perdidos_mes = estimacion.euros_perdidos_mes
    Path("informes").mkdir(exist_ok=True)
    ruta = generar(auditoria, estimacion, "informes/EJEMPLO.pdf")
    print(f"Puntuacion {auditoria.puntuacion}/100 | "
          f"{estimacion.euros_perdidos_mes:,.0f} EUR/mes | {ruta}")
    for h in auditoria.hallazgos:
        print(f"  - {h[:100]}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Radar de Retencion — Sora Systems")
    sub = p.add_subparsers(dest="comando", required=True)

    d = sub.add_parser("detectar", help="clasifica una lista de tiendas por ESP")
    d.add_argument("--entrada", default="datos/tiendas.csv")
    d.add_argument("--salida", default="datos/clasificadas.csv")
    d.add_argument("--hilos", type=int, default=8)
    d.set_defaults(func=cmd_detectar)

    a = sub.add_parser("adn", help="prefiltro por DNS: gratis y rapidisimo")
    a.add_argument("--entrada", default="datos/dominios.txt")
    a.add_argument("--salida", default="datos/adn.csv")
    a.add_argument("--hilos", type=int, default=40)
    a.set_defaults(func=cmd_adn)

    v = sub.add_parser("verificar", help="FASE 2: confirma por codigo antes de escribir")
    v.add_argument("--entrada", default="datos/adn.csv")
    v.add_argument("--salida", default="datos/escribibles.csv")
    v.add_argument("--hilos", type=int, default=4)
    v.set_defaults(func=cmd_verificar)

    s = sub.add_parser("sondear", help="abandona un carrito en una o varias tiendas")
    s.add_argument("--url")
    s.add_argument("--entrada", default="datos/clasificadas.csv")
    s.add_argument("--identificarse", action="store_true",
                   help="usa un agente de usuario identificable")
    s.set_defaults(func=cmd_sondear)

    i = sub.add_parser("informar", help="puntua y genera el PDF")
    i.add_argument("--url", required=True)
    i.add_argument("--visitas", type=int, default=10_000)
    i.add_argument("--conversion", type=float, default=0.015)
    i.add_argument("--ticket", type=float, default=45.0)
    i.add_argument("--cifras-reales", action="store_true", dest="cifras_reales")
    i.set_defaults(func=cmd_informar)

    dm = sub.add_parser("demo", help="informe de ejemplo, sin tocar tiendas reales")
    dm.set_defaults(func=cmd_demo)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
