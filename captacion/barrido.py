# -*- coding: utf-8 -*-
u"""Barrido de webs desactualizadas para la oferta de 200 EUR de Sora.

QUE HACE
    1. Pide a Overpass (OpenStreetMap) empresas con web, por provincia y
       sector. Gratis, sin clave, sin registro.
    2. Entra en cada web y lee SOLO el HTML. Sin navegador: lo que buscamos
       (el año del pie, si es responsive, el protocolo) esta en el codigo, no
       en lo que se ve. Mil webs en minutos en vez de mil minutos.
    3. Busca el correo generico y el aviso legal, que en España dice la razon
       social: ahi sale si es S.L. o S.A. sin preguntarle a nadie.
    4. Puntua y deja fuera lo que no cumple.

POR QUE ESTOS FILTROS Y NO OTROS
    La regla de Sara es inamovible: solo se escribe a la direccion generica
    de una sociedad (info@, contacto@ de una S.L. o S.A.). Las direcciones
    personales y las de autonomos son datos personales y NO se tocan. Este
    script no decide eso por intuicion: lo lee del aviso legal de su propia
    web, que es la fuente oficial y publica.

EDUCACION CON SUS SERVIDORES
    Un hilo, una peticion por dominio, pausa entre peticiones, User-Agent que
    dice quien soy y como contactarme, y nos rendimos a la primera a los 12
    segundos. No somos un escaner agresivo; leemos una pagina como haria una
    persona.

USO
    python3 barrido.py --probar            comprueba que la logica funciona
    python3 barrido.py --provincia ES-A --sector asesoria --limite 50
"""
import argparse, io, json, re, socket, ssl, sys, time
import urllib.error, urllib.parse, urllib.request
from datetime import date

AGENTE = ("SoraSystems-prospeccion/1.0 "
          "(+https://sorasystems.es; contacto: info@sorasystems.es)")
ESPERA = 1.0          # segundos entre peticiones
PLAZO = 12            # timeout por peticion
ESTE_ANO = date.today().year

# Sectores -> etiquetas de OpenStreetMap. Inmobiliarias NUNCA: son de la
# Agency y las dos marcas no se mezclan.
SECTORES = {
    "asesoria":     ['nwr["office"="accountant"]', 'nwr["office"="tax_advisor"]'],
    "abogados":     ['nwr["office"="lawyer"]'],
    "dental":       ['nwr["amenity"="dentist"]', 'nwr["healthcare"="dentist"]'],
    "clinica":      ['nwr["amenity"="clinic"]', 'nwr["healthcare"="centre"]'],
    "fisioterapia": ['nwr["healthcare"="physiotherapist"]'],
    "veterinario":  ['nwr["amenity"="veterinary"]'],
    "seguros":      ['nwr["office"="insurance"]'],
    "taller":       ['nwr["shop"="car_repair"]'],
    "gimnasio":     ['nwr["leisure"="fitness_centre"]'],
    "hotel":        ['nwr["tourism"="hotel"]'],
}

GENERICOS = ("info", "contacto", "hola", "administracion", "recepcion",
             "citas", "clinica", "despacho", "gestion", "oficina", "correo",
             "consultas", "atencion", "comercial", "secretaria")

RE_EMAIL = re.compile(r"[A-Za-z0-9._%%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}".replace("%%", "%"))
RE_MARCA = re.compile(r"(?:©|&copy;|\(c\)|copyright|todos los derechos|all rights)", re.I)
RE_ANO_SUELTO = re.compile(r"(?:19|20)\d{2}")
RE_SOC = re.compile(r"\b(S\.?\s?L\.?U?\.?|S\.?\s?A\.?|SOCIEDAD\s+LIMITADA|SOCIEDAD\s+AN[OÓ]NIMA)\b")
RE_VIEWPORT = re.compile(r'<meta[^>]+name=["\']?viewport', re.I)
RE_GENERADOR = re.compile(r'<meta[^>]+name=["\']?generator["\']?[^>]+content=["\']([^"\']+)', re.I)
RE_JQUERY = re.compile(r"jquery[.-]?(\d+)\.(\d+)[\d.]*(?:\.min)?\.js", re.I)


def traer(url, plazo=PLAZO):
    u"""Descarga una pagina. Devuelve (url_final, html) o (None, motivo)."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": AGENTE,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-ES,es;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=plazo) as r:
            bruto = r.read(600000)          # con 600 KB sobra para el pie
            tipo = r.headers.get("Content-Type", "")
            if "html" not in tipo.lower():
                return None, "no es html (%s)" % tipo[:40]
            juego = "utf-8"
            m = re.search(r"charset=([\w-]+)", tipo, re.I)
            if m:
                juego = m.group(1)
            txt = bruto.decode(juego, "replace")
            if "charset" not in tipo.lower():
                m = re.search(r'charset=["\']?([\w-]+)', txt[:2000], re.I)
                if m and m.group(1).lower() not in ("utf-8", juego.lower()):
                    txt = bruto.decode(m.group(1), "replace")
            return r.geturl(), txt
    except urllib.error.HTTPError as e:
        return None, "HTTP %s" % e.code
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ValueError) as e:
        return None, str(getattr(e, "reason", e))[:60]
    except Exception as e:                                   # nunca romper el barrido entero
        return None, "%s: %s" % (type(e).__name__, str(e)[:50])


def ano_del_pie(html):
    u"""El año del copyright.

    Nos quedamos con el MAYOR de los que aparecen junto a la marca de
    copyright. Si el pie pone "2015-2024" la web se toco en 2024, no en 2015,
    y escribirles diciendo que su web es de 2015 seria quedar fatal. Mejor
    perder una ficha dudosa que mandar un dato falso.
    """
    anos = []
    for m in RE_MARCA.finditer(html):
        ventana = html[max(0, m.start() - 20):m.end() + 60]
        anos += [int(a) for a in RE_ANO_SUELTO.findall(ventana)]
    anos = [a for a in anos if 1995 <= a <= ESTE_ANO + 1]
    return max(anos) if anos else None


def forma_juridica(texto):
    u"""S.L. o S.A. a partir del texto del aviso legal, normalizado.

    Devuelve None para una persona fisica. Eso NO es un fallo del filtro: a un
    autonomo no se le escribe, porque su correo es un dato personal. Que esto
    devuelva None es la regla funcionando.
    """
    m = RE_SOC.search(texto.upper())
    if not m:
        return None
    bruto = re.sub(r"[.\s]", "", m.group(1))
    if bruto.startswith("SOCIEDADLIMITADA") or bruto in ("SL", "SLU"):
        return "S.L."
    if bruto.startswith("SOCIEDADAN") or bruto == "SA":
        return "S.A."
    return None


def correos(html, dominio):
    u"""Correos genericos del propio dominio. Descarta los personales."""
    fuera = []
    for e in set(m.lower() for m in RE_EMAIL.findall(html)):
        if e.endswith((".png", ".jpg", ".gif", ".webp", ".svg")):
            continue
        usuario, _, host = e.partition("@")
        if dominio.replace("www.", "") not in host:
            continue                                   # correo de otro (gestor, plantilla)
        if any(usuario.startswith(g) for g in GENERICOS):
            fuera.append(e)
    return sorted(set(fuera))


def analizar(url):
    u"""Mira una web y devuelve las señales. No decide: solo mide."""
    if not url.startswith("http"):
        url = "https://" + url
    dominio = urllib.parse.urlparse(url).netloc.lower()
    final, html = traer(url)
    if final is None:
        return {"web": url, "error": html}

    r = {
        "web": url,
        "final": final,
        "dominio": dominio,
        "https": final.startswith("https://"),
        "responsive": bool(RE_VIEWPORT.search(html)),
        "ano_pie": ano_del_pie(html),
        "generador": None,
        "jquery": None,
        "emails": correos(html, dominio),
        "sociedad": None,
        "peso_kb": len(html) // 1024,
    }
    m = RE_GENERADOR.search(html)
    if m:
        r["generador"] = m.group(1)[:60]
    m = RE_JQUERY.search(html)
    if m:
        r["jquery"] = "%s.%s" % (m.group(1), m.group(2))

    # El aviso legal: ahi esta la razon social, y con ella si es sociedad.
    for ruta in ("/aviso-legal", "/aviso-legal/", "/avisolegal", "/legal",
                 "/politica-de-privacidad", "/privacidad"):
        _, h2 = traer(urllib.parse.urljoin(final, ruta), plazo=8)
        if h2 and len(h2) > 400:
            texto = re.sub(r"<[^>]+>", " ", h2)
            r["sociedad"] = forma_juridica(texto)
            if not r["emails"]:
                r["emails"] = correos(h2, dominio)
            break
        time.sleep(0.3)
    return r


def veredicto(r):
    u"""Decide si la ficha vale. Devuelve (apto, motivos, señal_para_el_correo).

    APTO exige las tres cosas a la vez, no dos de tres:
      - una señal de desactualizacion comprobable
      - un correo generico del propio dominio
      - constancia de que es sociedad
    """
    if r.get("error"):
        return False, ["no responde: %s" % r["error"]], None

    señales, motivos = [], []
    ano = r.get("ano_pie")
    if ano and ano <= ESTE_ANO - 2:
        señales.append(("pie", u"el pie de la página sigue poniendo %d" % ano))
    if not r["responsive"]:
        señales.append(("movil", u"la web no está preparada para el móvil"))
    if not r["https"]:
        señales.append(("https", u"la web no va por conexión segura"))
    if r.get("jquery") and int(r["jquery"].split(".")[0]) < 3:
        señales.append(("jquery", u"la web usa una librería de hace más de diez años"))

    if not señales:
        motivos.append("sin señal de desactualizacion")
    if not r["emails"]:
        motivos.append("sin correo generico del dominio")
    if not r.get("sociedad"):
        motivos.append("no consta sociedad en el aviso legal")

    return (not motivos), motivos, (señales[0] if señales else None)


# --------------------------------------------------------------- Overpass
def candidatos(provincia, sector, limite):
    partes = "".join('  %s["website"](area.p);\n' % t for t in SECTORES[sector])
    q = (u'[out:json][timeout:120];\n'
         u'area["ISO3166-2"="%s"][admin_level=6]->.p;\n(\n%s);\nout tags center;'
         % (provincia, partes))
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": q}).encode("utf-8"),
        headers={"User-Agent": AGENTE})
    d = json.loads(urllib.request.urlopen(req, timeout=180).read().decode("utf-8"))
    fuera, vistos = [], set()
    for e in d.get("elements", []):
        t = e.get("tags", {})
        web = (t.get("website") or t.get("contact:website") or "").strip()
        nombre = (t.get("name") or "").strip()
        if not web or not nombre:
            continue
        dom = urllib.parse.urlparse(web if web.startswith("http") else "https://" + web).netloc.lower()
        if not dom or dom in vistos:
            continue
        vistos.add(dom)
        fuera.append({"empresa": nombre, "web": web, "sector": sector,
                      "localidad": t.get("addr:city") or t.get("addr:town") or "",
                      "email_osm": t.get("email") or t.get("contact:email") or ""})
        if len(fuera) >= limite:
            break
    return fuera


# ----------------------------------------------------------------- pruebas
def probar():
    u"""Comprueba la logica sin depender de que la red este abierta."""
    html = u"""<html><head><meta name="viewport" content="width=device-width">
      <meta name="generator" content="WordPress 5.2"></head><body>
      Escríbenos a Info@Ejemplo.es o a maria.lopez@ejemplo.es
      <script src="/js/jquery-1.11.3.min.js"></script>
      <footer>© 2019 Ejemplo S.L. Todos los derechos reservados</footer></body></html>"""
    assert ano_del_pie(html) == 2019, ano_del_pie(html)
    assert ano_del_pie(u"<p>© 2015-2025 Cosas</p>") == 2025
    assert ano_del_pie(u"<p>sin año</p>") is None
    assert correos(html, "ejemplo.es") == ["info@ejemplo.es"], correos(html, "ejemplo.es")
    assert forma_juridica(u"Ejemplo S.L.") == "S.L."
    assert forma_juridica(u"EJEMPLO SL") == "S.L."
    assert forma_juridica(u"Clinica Dental S.A.") == "S.A."
    assert forma_juridica(u"GESTORIA SLU") == "S.L."
    assert forma_juridica(u"Juan Perez, autonomo") is None   # persona fisica: NO se escribe
    assert RE_JQUERY.search(html).group(1) == "1"
    assert RE_VIEWPORT.search(html)

    # Un caso que NO debe pasar el filtro: sin señal, sin sociedad.
    r = {"error": None, "ano_pie": ESTE_ANO, "responsive": True, "https": True,
         "jquery": None, "emails": ["info@x.es"], "sociedad": None}
    apto, motivos, _ = veredicto(r)
    assert not apto and "no consta sociedad en el aviso legal" in motivos

    # Uno que si: pie viejo, correo generico y sociedad.
    r2 = dict(r, ano_pie=2019, sociedad="S.L.")
    apto2, motivos2, señal = veredicto(r2)
    assert apto2 and motivos2 == [] and señal[0] == "pie", (apto2, motivos2, señal)
    assert u"2019" in señal[1]
    print("logica: OK (7 comprobaciones)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--probar", action="store_true")
    p.add_argument("--analizar", help="una sola web, para ver que sale")
    p.add_argument("--provincia", default="ES-A", help="codigo ISO, ej. ES-A Alicante, ES-M Madrid")
    p.add_argument("--sector", default="asesoria", choices=sorted(SECTORES))
    p.add_argument("--limite", type=int, default=40)
    p.add_argument("--salida", default="barrido.json")
    a = p.parse_args()

    if a.probar:
        return probar()

    if a.analizar:
        r = analizar(a.analizar)
        apto, motivos, señal = veredicto(r)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        print("APTO" if apto else "NO APTO: " + "; ".join(motivos))
        if señal:
            print(u"señal -> %s" % señal[1])
        return

    print(u"buscando %s en %s..." % (a.sector, a.provincia))
    lista = candidatos(a.provincia, a.sector, a.limite)
    print(u"%d candidatos con web\n" % len(lista))

    aptos = []
    for i, c in enumerate(lista, 1):
        r = analizar(c["web"])
        apto, motivos, señal = veredicto(r)
        c.update(r)
        c["apto"] = apto
        c["motivos"] = motivos
        c["señal"] = señal[1] if señal else None
        if apto:
            aptos.append(c)
        print(u"%3d/%d  %-34s %s" % (i, len(lista), c["empresa"][:34],
                                     u"APTO · " + señal[1] if apto else u"no: " + ", ".join(motivos)))
        time.sleep(ESPERA)

    io.open(a.salida, "w", encoding="utf-8").write(
        json.dumps(lista, ensure_ascii=False, indent=1))
    print(u"\n%d aptos de %d  ->  %s" % (len(aptos), len(lista), a.salida))


if __name__ == "__main__":
    main()
