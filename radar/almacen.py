"""Persistencia simple en SQLite. Una fila por tienda y etapa."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .modelos import Auditoria, Deteccion, Sonda

RUTA_POR_DEFECTO = Path("datos/radar.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS detecciones (
    url TEXT PRIMARY KEY, detectado_en TEXT, plataforma TEXT, esp TEXT,
    secundarios TEXT, captura_email INTEGER, prioridad TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS sondas (
    alias TEXT PRIMARY KEY, url TEXT, lanzada_en TEXT, producto TEXT,
    suscrito INTEGER, checkout INTEGER, email_introducido INTEGER,
    notas TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS informes (
    url TEXT PRIMARY KEY, generado_en TEXT, puntuacion INTEGER,
    euros_mes REAL, ruta_pdf TEXT
);
"""


def abrir(ruta: Path | str = RUTA_POR_DEFECTO) -> sqlite3.Connection:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.executescript(ESQUEMA)
    return conexion


def guardar_deteccion(conexion: sqlite3.Connection, d: Deteccion) -> None:
    conexion.execute(
        "INSERT OR REPLACE INTO detecciones VALUES (?,?,?,?,?,?,?,?)",
        (d.url, d.detectado_en, d.plataforma, d.esp,
         json.dumps(d.esp_secundarios, ensure_ascii=False),
         int(d.captura_email), d.prioridad, d.error),
    )
    conexion.commit()


def guardar_sonda(conexion: sqlite3.Connection, s: Sonda) -> None:
    conexion.execute(
        "INSERT OR REPLACE INTO sondas VALUES (?,?,?,?,?,?,?,?,?)",
        (s.alias, s.url, s.lanzada_en, s.producto_usado, int(s.suscrito),
         int(s.checkout_alcanzado), int(s.email_introducido),
         json.dumps(s.notas, ensure_ascii=False), s.error),
    )
    conexion.commit()


def guardar_informe(conexion: sqlite3.Connection, a: Auditoria, ruta_pdf: str,
                    generado_en: str) -> None:
    conexion.execute(
        "INSERT OR REPLACE INTO informes VALUES (?,?,?,?,?)",
        (a.tienda.url, generado_en, a.puntuacion, a.euros_perdidos_mes, ruta_pdf),
    )
    conexion.commit()
