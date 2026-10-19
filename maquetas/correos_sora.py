# -*- coding: utf-8 -*-
u"""Los diez correos de la campana de renovacion, con la identidad de Sora.

Que cambia respecto a la primera version
----------------------------------------
1. La paleta. Iba en coral #FF6B4A sobre crema, que no es Sora. Ahora:
     cabecera  #07090f  el casi negro de sorasystems.es
     filete    #2dd4bf  el turquesa de la marca
     boton     #2dd4bf  con texto #06211d, igual que el .btn-1 de la web
     precio    #8b5cf6  el violeta, en el borde del recuadro
   El cuerpo se queda en blanco a proposito: la marca es oscura, pero un
   correo entero en oscuro lo invierten la mitad de los clientes y se lee
   peor. La identidad la dan la cabecera, los acentos y la tipografia.

2. La direccion de la maqueta. Antes claude.ai/artifact/..., un dominio ajeno
   que encima obligaba a cambiar un permiso a mano por cada propuesta. Ahora
   sorasystems.es/propuestas/<negocio>, servido por la propia web.

Reglas que no se tocan: sin adjuntos, sin pixel de apertura, sin acortadores,
un solo precio (los 200 EUR), salida clara en el pie, y las dos marcas nunca
mezcladas (aqui no aparece "Sara Ferreira" en ningun sitio).
"""
import io, json, os

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = u"https://sorasystems.es/propuestas/"

# (recId, empresa con acentos, localidad, ano del pie, slug, sector)
R = [
 ("recFaWSlSIQKGIeDQ", u"Centro Dermatológico Estético", u"Alicante",            u"2017", "centro-dermatologico-estetico",  "estetica"),
 ("rec2Rci7puL92Kti4", u"Clínica Miramar",               u"Benissa",             u"2022", "clinica-miramar",                "estetica"),
 ("recFyE7TxDzD0x1dr", u"Gestoría Asesoría Toledano",    u"Alicante",            u"2023", "gestoria-asesoria-toledano",     "asesoria"),
 ("recrajsCFm80CvGOI", u"Naranjo Asesores",              u"Benidorm",            u"2022", "naranjo-asesores",               "asesoria"),
 ("recmR5ZiUPOhPqsEi", u"Clínica Trinum",                u"Alicante",            u"2022", "clinica-trinum",                 "estetica"),
 ("reczsqKPG5QSd8zEe", u"Clínica Guinova",               u"Elche",               u"2022", "clinica-guinova",                "estetica"),
 ("rec4MtXetmGIXFL2i", u"Clínica Dental Teresa González", u"Elda",               u"2022", "clinica-dental-teresa-gonzalez", "dental"),
 ("reclutIl7D3yLpovh", u"Congost Abogados",              u"La Nucía",            u"2021", "congost-abogados",               "abogados"),
 ("recAOlX3EOEnNxAmG", u"Centro Bodyfriendly",           u"Torrevieja",          u"2022", "centro-bodyfriendly",            "fisioterapia"),
 ("recmHYzy1pseSNJtw", u"Actuagest",                     u"Pilar de la Horadada", u"2022", "actuagest",                     "asesoria"),
]

# Lo que se les ofrece ensenar, con la palabra que usa cada sector. Con
# "servicios" para todos valdria, pero un dentista no llama servicios a lo que
# hace y eso se nota al leerlo.
QUE = {
    "estetica":     u"vuestros tratamientos",
    "dental":       u"vuestros tratamientos",
    "fisioterapia": u"vuestros servicios",
    "asesoria":     u"vuestros servicios",
    "abogados":     u"vuestras áreas",
}

TIPO = u"'Sora',Helvetica,Arial,sans-serif"      # Sora si el cliente la tiene
TXT = u"Helvetica,Arial,sans-serif"

PLANTILLA = u"""<table width="100%%" cellpadding="0" cellspacing="0" style="background:#0b0e16;padding:16px 0"><tr><td align="center"><table width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%%;background:#ffffff;border-radius:14px;overflow:hidden"><tr><td style="background:#07090f;padding:26px 32px 22px"><div style="font-family:%(tipo)s;font-size:26px;font-weight:800;color:#ffffff;letter-spacing:.4px">Sora Systems</div><div style="font-family:%(txt)s;font-size:13px;color:#9aa3c7;padding-top:7px">Webs y automatización para empresas</div></td></tr><tr><td style="background:#2dd4bf;height:5px;line-height:5px;font-size:0">&nbsp;</td></tr><tr><td style="padding:30px 32px 8px;font-family:%(txt)s;font-size:16px;line-height:1.65;color:#14161f"><p style="margin:0 0 16px">Hola, equipo de <b>%(emp)s</b>:</p><p style="margin:0 0 16px">Soy Sara, de Sora Systems. Trabajo con empresas de toda España.</p><p style="margin:0 0 16px">He entrado en vuestra web y <b>el pie de la página sigue poniendo %(ano)s</b>. Se nota, y es una pena: lo primero que mira quien os busca es la portada.</p><p style="margin:0 0 22px">Os he preparado una propuesta de cómo podría quedar, con vuestro nombre y %(que)s. Echadle un vistazo, sin compromiso:</p></td></tr><tr><td align="center" style="padding:0 32px 26px"><table cellpadding="0" cellspacing="0"><tr><td align="center" bgcolor="#2dd4bf" style="border-radius:8px"><a href="%(url)s" style="display:inline-block;padding:15px 30px;font-family:%(tipo)s;font-size:17px;font-weight:700;color:#06211d;text-decoration:none">Ver cómo quedaría vuestra web</a></td></tr></table></td></tr><tr><td style="padding:0 32px 26px"><table width="100%%" cellpadding="0" cellspacing="0" style="background:#f4f1ff;border-left:4px solid #8b5cf6;border-radius:6px"><tr><td style="padding:16px 18px;font-family:%(txt)s;font-size:16px;line-height:1.6;color:#211a33">Si os gusta, <b>os la dejamos así por 200 €</b>. Pago único, sin cuotas.<br><span style="color:#6d28d9">Es la oferta de octubre: termina el 31.</span></td></tr></table></td></tr><tr><td style="padding:0 32px 28px;font-family:%(txt)s;font-size:16px;line-height:1.65;color:#14161f"><p style="margin:0 0 20px">Y si ahora no es el momento, decídmelo sin problema y no os vuelvo a escribir.</p><p style="margin:0">Un saludo,<br><b>Sara</b> · Sora Systems</p></td></tr><tr><td style="background:#f7f8fb;border-top:1px solid #e6e8f0;padding:18px 32px;font-family:%(txt)s;font-size:13px;line-height:1.6;color:#5b6176"><a href="https://sorasystems.es" style="color:#0f766e;text-decoration:none;font-weight:600">sorasystems.es</a><div style="padding-top:10px;color:#8b90a3">Os escribo a la dirección pública de contacto de vuestro negocio. Si no os interesa, responded «no» y no volveré a escribiros.</div></td></tr></table></td></tr></table>"""

salida = []
for rid, emp, loc, ano, slug, sector in R:
    url = BASE + slug
    cuerpo = PLANTILLA % dict(tipo=TIPO, txt=TXT, emp=emp, loc=loc, ano=ano,
                              que=QUE[sector], url=url)
    asunto = u"Una idea para la web de %s" % emp

    # Antes de que esto llegue a un negocio de verdad.
    assert u"%(" not in cuerpo and u"{{" not in cuerpo, rid   # nada sin rellenar
    assert cuerpo.count(emp) == 1, rid
    assert url in cuerpo and u"claude.ai" not in cuerpo, rid  # ya no hay dominio ajeno
    assert u"Sara Ferreira" not in cuerpo, (rid, "las dos marcas no se mezclan")
    assert u"#2dd4bf" in cuerpo and u"#07090f" in cuerpo and u"#8b5cf6" in cuerpo, rid
    assert u"FF6B4A" not in cuerpo.upper(), (rid, "coral de la version vieja")
    assert cuerpo.count(u"200") == 1, (rid, "el precio, una sola vez")
    assert u"290" not in cuerpo and u"350" not in cuerpo, (rid, "otros packs no pintan aqui")
    assert u"responded" in cuerpo, (rid, "falta la salida clara")
    assert u"de aquí" not in cuerpo, (rid, "Sora no es de un sitio: es de toda España")
    assert u"aqu\u00ed en" not in cuerpo, (rid, "Sora no dice estar donde no esta")
    assert loc not in cuerpo, (rid, "la localidad no va en el cuerpo")
    assert u"<img" not in cuerpo, (rid, "sin imagenes: los clientes las bloquean")
    salida.append({"id": rid, "fields": {
        "fldxhYZT5O0Mu3SMp": cuerpo,   # Cuerpo
        "fld7eRD3xLJhjpSNG": asunto,   # Asunto
        "fldSPzGW9oNQgBIF5": url,      # Maqueta
    }})

assert len(salida) == 10
assert len(set(d["id"] for d in salida)) == 10
assert len(set(d["fields"]["fldSPzGW9oNQgBIF5"] for d in salida)) == 10, "url repetida"

ruta = os.path.join(AQUI, "correos_sora.json")
io.open(ruta, "w", encoding="utf-8").write(json.dumps(salida, ensure_ascii=False))
print(u"%d correos listos  ->  %s" % (len(salida), ruta))
for rid, emp, loc, ano, slug, sector in R:
    print(u"  %-32s %-22s pie %s   /propuestas/%s" % (emp, loc, ano, slug))
