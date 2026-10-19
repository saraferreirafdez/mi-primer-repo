# -*- coding: utf-8 -*-
u"""Convierte las maquetas en paginas web de verdad, servibles por GitHub Pages.

Las maquetas se escribieron como artifacts de Claude, que son FRAGMENTOS: no
llevan doctype, ni <html>, ni <head>, ni charset. Claude se los pone al
publicarlas. Un servidor web no: sin charset el navegador adivina, y
"Dermatologico Estetico" le sale al visitante como mojibake. De ahi este
envoltorio.

Tres cosas que anade cada pagina y que el artifact no necesitaba:
  - <meta charset="utf-8">        los acentos
  - <meta name="viewport">       el movil, que es donde se va a leer
  - <meta name="robots" noindex> Google no lista nunca estas paginas. Llevan el
                                 nombre de un negocio ajeno; que se vean con el
                                 enlace es el objetivo, que salgan en busquedas
                                 no.

Salida: una carpeta por negocio con su index.html, para que la direccion sea
propuestas.sorasystems.es/clinica-miramar y no ...­/maqueta_miramar.html
"""
import io, os, re, sys

ORIGEN = os.path.dirname(os.path.abspath(__file__))
# Las propuestas viven dentro de la web de Sora, que ya esta en Netlify y ya
# responde en sorasystems.es. Nada de alojamiento nuevo, ni subdominio, ni DNS,
# ni permisos que tocar: se sube a master y Netlify la publica.
DESTINO = sys.argv[1] if len(sys.argv) > 1 else "/home/user/sorasystems-web/propuestas"

# (fichero de origen, slug de la direccion, nombre del negocio tal y como se
#  escribe con acentos, una palabra que TIENE que aparecer en el fragmento)
PAGINAS = [
    ("maqueta_dermatologico.html",  "centro-dermatologico-estetico",  u"Centro Dermatológico Estético", u"Dermatol"),
    ("maqueta_miramar.html",        "clinica-miramar",                u"Clínica Miramar",              u"Miramar"),
    ("maqueta_toledano.html",       "gestoria-asesoria-toledano",     u"Gestoría Asesoría Toledano",   u"Toledano"),
    ("maqueta_naranjo.html",        "naranjo-asesores",               u"Naranjo Asesores",             u"Naranjo"),
    ("maqueta_trinum.html",         "clinica-trinum",                 u"Clínica Trinum",               u"Trinum"),
    ("maqueta_guinova.html",        "clinica-guinova",                u"Clínica Guinova",              u"Guinova"),
    ("maqueta_teresagonzalez.html", "clinica-dental-teresa-gonzalez", u"Clínica Dental Teresa González", u"Teresa"),
    ("maqueta_congost.html",        "congost-abogados",               u"Congost Abogados",             u"Congost"),
    ("maqueta_bodyfriendly.html",   "centro-bodyfriendly",            u"Centro Bodyfriendly",          u"Bodyfriendly"),
    ("maqueta_actuagest.html",      "actuagest",                      u"Actuagest",                    u"Actuagest"),
]

CABECERA = u"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="referrer" content="no-referrer">
<title>%(titulo)s · propuesta de Sora Systems</title>
<meta name="description" content="Propuesta de portada preparada por Sora Systems. Esta pagina no es la web de %(negocio)s.">
%(cabeza)s
</head>
<body>
%(cuerpo)s
</body>
</html>
"""


def envolver(fragmento, negocio):
    u"""Parte el fragmento en <head> y <body> y lo cierra como documento."""
    corte = fragmento.find(u"</style>")
    assert corte != -1, u"el fragmento no trae bloque <style>"
    corte += len(u"</style>")
    cabeza, cuerpo = fragmento[:corte], fragmento[corte:]

    # El <title> del artifact decia "Portada X". En una pagina publica el title
    # es lo que se ve en la pestana y en el enlace compartido: lo reescribo
    # arriba, asi que aqui lo quito para no tener dos.
    cabeza = re.sub(u"<title>.*?</title>\\s*", u"", cabeza, flags=re.S)
    # Meta propia de Claude: fuera, en un servidor web no significa nada.
    cabeza = re.sub(u'<meta name="claude:[^>]*>\\s*', u"", cabeza)

    return CABECERA % {
        "titulo": negocio,
        "negocio": negocio,
        "cabeza": cabeza.strip(),
        "cuerpo": cuerpo.strip(),
    }


# ---------------------------------------------------------------- las paginas
if not os.path.isdir(DESTINO):
    os.makedirs(DESTINO)

hechas = []
for fichero, slug, negocio, palabra in PAGINAS:
    ruta_origen = os.path.join(ORIGEN, fichero)
    fragmento = io.open(ruta_origen, encoding="utf-8").read()

    # Que el fragmento sea el del negocio que creo que es. Publicar la maqueta
    # de una clinica con el nombre de otra seria el peor error posible aqui.
    assert palabra in fragmento, u"%s no menciona %s" % (fichero, palabra)

    pagina = envolver(fragmento, negocio)

    # Comprobaciones sobre el resultado, antes de escribir nada.
    assert pagina.startswith(u"<!doctype html>"), slug
    assert u'charset="utf-8"' in pagina, slug
    assert u"noindex" in pagina, slug
    assert u"claude:" not in pagina, slug
    assert pagina.count(u"<title>") == 1, slug
    assert pagina.count(u"<body>") == 1 and pagina.count(u"</body>") == 1, slug
    assert negocio.split()[-1] in pagina, slug          # el nombre con acentos sobrevive
    assert u"Sora Systems" in pagina, slug              # la barra que avisa de que no es su web
    assert u"no es su web" in pagina, slug
    assert u"200" in pagina, slug                       # el precio sigue ahi
    # La identidad tiene que ser la de sorasystems.es, no la primera que hice.
    assert u"#2dd4bf" in pagina and u"#8b5cf6" in pagina, (slug, "falta la paleta")
    assert u"#07090f" in pagina, (slug, "falta el fondo de la marca")
    assert u"FF6B4A" not in pagina.upper(), (slug, "queda coral de la version vieja")
    assert u"Fraunces" not in pagina, (slug, "queda tipografia vieja")

    carpeta = os.path.join(DESTINO, slug)
    if not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    io.open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8").write(pagina)
    hechas.append((slug, negocio, len(pagina)))

# ------------------------------------------------------- la raiz del dominio
# Quien reciba el correo va a recortar la direccion para ver quien le escribe.
# Si eso da un 404 parece una chapuza. Pero la raiz NO lista los negocios: la
# cartera de clientes potenciales no se publica.
RAIZ = u"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Propuestas · Sora Systems</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500&display=swap">
<style>
  /* Misma identidad que sorasystems.es: fondo casi negro, halos turquesa y
     violeta, Sora para el titular, Inter para el texto. */
  *{margin:0;padding:0;box-sizing:border-box}
  body{min-height:100vh;display:grid;place-items:center;padding:0 22px;
       background:#07090f;color:#eef1ff;line-height:1.7;
       font-family:'Inter',system-ui,-apple-system,"Segoe UI",sans-serif;
       -webkit-font-smoothing:antialiased}
  body::before{content:"";position:fixed;inset:0;z-index:-1;background:
    radial-gradient(680px circle at 15% 0%,rgba(45,212,191,.12),transparent 55%),
    radial-gradient(760px circle at 90% 12%,rgba(139,92,246,.16),transparent 55%),
    #07090f}
  .caja{max-width:32rem;text-align:center}
  .marca{display:inline-flex;align-items:center;gap:10px;font-family:'Sora',sans-serif;
         font-weight:700;font-size:1.05rem;color:#fff}
  .punto{width:14px;height:14px;border-radius:50%;
         background:linear-gradient(135deg,#2dd4bf,#8b5cf6);
         box-shadow:0 0 14px rgba(45,212,191,.6)}
  h1{font-family:'Sora',sans-serif;font-weight:800;letter-spacing:-.02em;
     font-size:clamp(1.6rem,5vw,2.3rem);line-height:1.15;margin:20px 0 14px;
     background:linear-gradient(100deg,#fff 20%,#cbb9ff);
     -webkit-background-clip:text;background-clip:text;color:transparent}
  p{color:#cdd3f0;margin:0 0 28px}
  a{display:inline-block;padding:13px 26px;border-radius:999px;background:#2dd4bf;
    color:#06211d;text-decoration:none;font-weight:600;font-family:'Sora',sans-serif;
    box-shadow:0 0 26px rgba(45,212,191,.28)}
</style>
</head>
<body>
  <div class="caja">
    <div class="marca"><span class="punto"></span>Sora Systems</div>
    <h1>Aquí dejo las propuestas de diseño</h1>
    <p>Cada propuesta tiene su propia dirección y se la envío solo al negocio
       para el que la he preparado. Si has llegado aquí por el enlace de un
       correo mío, vuelve a pincharlo: te lleva a la tuya.</p>
    <a href="https://sorasystems.es">Ir a sorasystems.es</a>
  </div>
</body>
</html>
"""
io.open(os.path.join(DESTINO, "index.html"), "w", encoding="utf-8").write(RAIZ)

print("paginas:", len(hechas))
for slug, negocio, n in hechas:
    print("  %-32s %-34s %5d bytes" % (slug, negocio, n))
print("  %-32s %-34s %5d bytes" % ("(raiz)", "Sora Systems", len(RAIZ)))
