# -*- coding: utf-8 -*-
u"""Limpia la lista de CoWork antes de tocar una sola web.

Descartar aqui es gratis; descartar despues cuesta una peticion a su servidor
y, si se cuela, cuesta la cara de Sora delante de un cliente que no lo era.
"""
import csv, io, os, sys
# -I aisla sys.path (lo uso porque el CSV viene de fuera y no quiero que un
# fichero vecino se importe solo). Anado a mano el directorio del script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import Counter
from barrido import motivo_descarte

filas = list(csv.DictReader(io.open("candidatos-sora.csv", encoding="utf-8")))
print(u"filas en el CSV: %d" % len(filas))

vivos, fuera, dominios = [], Counter(), set()
for f in filas:
    web = (f.get("web") or "").strip()
    emp = (f.get("empresa") or "").strip()
    if not web or not emp:
        fuera["sin web o sin nombre"] += 1
        continue
    m = motivo_descarte(web, emp)
    if m:
        fuera[m] += 1
        continue
    host = web.split("//")[-1].split("/")[0].lower().replace("www.", "")
    if host in dominios:
        fuera["dominio repetido"] += 1
        continue
    dominios.add(host)
    vivos.append(f)

print(u"\n--- descartes ---")
for k, v in fuera.most_common():
    print(u"  %-22s %4d" % (k, v))
print(u"\nquedan: %d webs que merece la pena mirar" % len(vivos))

print(u"\n--- por provincia ---")
for p, n in Counter(f["provincia"] for f in vivos).most_common():
    print(u"  %-6s %4d" % (p, n))
print(u"\n--- por sector ---")
for s, n in Counter(f["sector"] for f in vivos).most_common():
    print(u"  %-16s %4d" % (s, n))
print(u"\ncon email ya en OSM: %d" % sum(1 for f in vivos if (f.get("email_osm") or "").strip()))

w = csv.DictWriter(io.open("candidatos-limpios.csv", "w", encoding="utf-8", newline=""),
                   fieldnames=["provincia", "empresa", "web", "localidad", "sector", "email_osm"])
w.writeheader()
w.writerows(vivos)
print(u"\nescrito: candidatos-limpios.csv")
