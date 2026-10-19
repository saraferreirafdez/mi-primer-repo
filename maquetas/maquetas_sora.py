# -*- coding: utf-8 -*-
u"""Las maquetas, rehechas con la identidad REAL de Sora Systems.

Por que se rehacen
------------------
La primera version salio en arena, coral y tipografia Fraunces: una paleta
mediterranea bonita que no es la de Sora. La marca de verdad esta en
sorasystems.es y es otra cosa:

    fondo        #07090f  casi negro azulado, con dos halos difuminados
    turquesa     #2dd4bf  el acento principal
    violeta      #8b5cf6  el segundo acento (#cbb9ff en texto)
    texto        #eef1ff  claro,  #cdd3f0 secundario,  #9aa3c7 apagado
    tipografias  Sora (titulares, 700/800) + Inter (texto)
    el punto     degradado turquesa->violeta con halo, es la firma de la marca

Estos valores no me los he inventado ni los he deducido del skill: estan
sacados del CSS de sorasystems.es (servicios/diseno-web-branding.html).

Nota para quien lea esto despues: el skill de marca describe "naranjas
calidos, corales, fondos claros", que es justo lo contrario de lo que hay
publicado. Manda la web. El skill habria que corregirlo.

El contenido no se toca
-----------------------
Los textos por negocio (titular, servicios reales de su web, datos) ya estaban
bien y son lo que da credibilidad. Se leen de maquetas.py, que sigue siendo la
unica fuente de ese contenido: aqui solo cambia como se ve.
"""
import ast, io, os

AQUI = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# El contenido vive en maquetas.py. Importarlo entero ejecutaria su bucle y
# reescribiria las maquetas viejas, asi que ejecuto SOLO la asignacion de N.
# ---------------------------------------------------------------------------
_fuente = io.open(os.path.join(AQUI, "maquetas.py"), encoding="utf-8").read()
_arbol = ast.parse(_fuente)
_nodo = next(n for n in _arbol.body
             if isinstance(n, ast.Assign)
             and getattr(n.targets[0], "id", None) == "N")
_ns = {}
exec(compile(ast.Module(body=[_nodo], type_ignores=[]), "<N>", "exec"), _ns)
N = _ns["N"]
assert len(N) == 9, len(N)

# Clinica Miramar fue la primera y se escribio a mano, antes de que existiera
# el generador, asi que no esta en la N de maquetas.py. Su contenido es el del
# maqueta_miramar.html original, transcrito aqui para que las diez pasen por el
# mismo molde y ninguna se quede con la identidad vieja.
MIRAMAR = dict(
    f="miramar", emp=u"Clínica Miramar", loc=u"Benissa",
    eyebrow=u"Benissa · Costa Blanca",
    h1=u"Medicina estética con criterio médico",
    sub=u"Tratamientos faciales, corporales y capilares en Benissa. Primera "
        u"visita sin compromiso, con un plan hecho para ti y no para un catálogo.",
    cta=u"Pedir primera visita", cta2=u"Escribir por WhatsApp",
    foto=u"Aquí iría una foto<br>de la clínica o del equipo",
    stit=u"Lo que hacemos",
    sdesc=u"Los cinco tratamientos que ya ofrecéis, ordenados para que se "
          u"entiendan de un vistazo.",
    serv=[(u"Rellenos con ácido hialurónico",
           u"Volumen y contorno facial con producto reabsorbible, en una sola sesión."),
          (u"Endoláser lifting facial",
           u"Tensado del tercio inferior sin cirugía abierta ni ingreso."),
          (u"Hydrafacial",
           u"Limpieza profunda e hidratación. El tratamiento de mantenimiento."),
          (u"Trasplante capilar",
           u"Estudio del folículo e injerto, con seguimiento del resultado."),
          (u"Longevidad y medicina preventiva",
           u"Analítica, revisión y plan de salud a medio plazo.")],
    datos=[(u"Dónde", u"Benissa", u"Costa Blanca, Alicante"),
           (u"Primera visita", u"Sin compromiso", u"Valoración y plan antes de decidir"),
           (u"Cita", u"Por WhatsApp", u"O por teléfono, como prefieras")])

N = N + [MIRAMAR]
assert len(N) == 10, len(N)
assert len(set(n["f"] for n in N)) == 10, "hay un fichero repetido"


CAB = u'''<title>@EMP@ · propuesta de Sora Systems</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap">

<style>
/* Identidad de Sora Systems. Los valores salen de sorasystems.es. */
:root{
  --fondo:#07090f; --turquesa:#2dd4bf; --violeta:#8b5cf6; --violeta-claro:#cbb9ff;
  --texto:#eef1ff; --texto-2:#cdd3f0; --texto-3:#9aa3c7;
  --linea:rgba(255,255,255,.12); --tarjeta:rgba(255,255,255,.04);
  --borde-acento:rgba(45,212,191,.28);
  --titular:"Sora",system-ui,-apple-system,"Segoe UI",sans-serif;
  --cuerpo:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;
  color-scheme:dark;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:var(--cuerpo);color:var(--texto);background:var(--fondo);
     line-height:1.7;-webkit-font-smoothing:antialiased;overflow-x:hidden}
/* Los dos halos: turquesa arriba a la izquierda, violeta arriba a la derecha.
   Es lo que hace que el fondo no parezca un negro plano. */
body::before{content:"";position:fixed;inset:0;z-index:-1;background:
  radial-gradient(680px circle at 15% 0%,rgba(45,212,191,.12),transparent 55%),
  radial-gradient(760px circle at 90% 12%,rgba(139,92,246,.16),transparent 55%),
  var(--fondo)}
a{color:inherit}
.wrap{width:100%;max-width:980px;margin:0 auto;
      padding-left:max(22px,env(safe-area-inset-left,0px));
      padding-right:max(22px,env(safe-area-inset-right,0px))}
h1,h2,h3{font-family:var(--titular);letter-spacing:-.02em;text-wrap:balance}

/* ---- Barra de Sora. Va arriba del todo: nadie confunde esto con su web ---- */
.topbar{position:sticky;top:0;z-index:50;backdrop-filter:blur(12px);
        background:rgba(7,9,15,.78);border-bottom:1px solid rgba(255,255,255,.06)}
.topbar .wrap{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;
              min-height:62px;padding-block:11px}
.marca{display:flex;align-items:center;gap:10px;font-family:var(--titular);
       font-weight:700;font-size:1.05rem;color:#fff;white-space:nowrap}
.punto{width:14px;height:14px;border-radius:50%;flex:0 0 auto;
       background:linear-gradient(135deg,var(--turquesa),var(--violeta));
       box-shadow:0 0 14px rgba(45,212,191,.6)}
.aviso{font-size:.88rem;color:var(--texto-3);min-width:0}

/* ---- Portada ---- */
header.hero{padding:clamp(44px,8vh,86px) 0 10px}
.hero .rejilla-hero{display:grid;grid-template-columns:1.2fr .8fr;gap:44px;align-items:center}
.eyebrow{font-family:var(--titular);font-size:.8rem;font-weight:600;letter-spacing:.12em;
         text-transform:uppercase;color:var(--turquesa);margin-bottom:16px}
h1{font-family:var(--titular);font-weight:800;font-size:clamp(1.9rem,5.6vw,3.1rem);
   line-height:1.12;margin-bottom:20px;
   background:linear-gradient(100deg,#fff 20%,var(--violeta-claro));
   -webkit-background-clip:text;background-clip:text;color:transparent}
.intro{font-size:clamp(1.02rem,2.4vw,1.18rem);color:var(--texto-2);max-width:46ch}
.botones{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}
.btn{display:inline-block;padding:13px 26px;border-radius:999px;font-weight:600;
     font-size:1rem;text-decoration:none;font-family:var(--titular)}
.btn-1{background:var(--turquesa);color:#06211d;box-shadow:0 0 26px rgba(45,212,191,.28)}
.btn-2{border:1px solid var(--linea);color:var(--texto-2)}
.hueco{aspect-ratio:4/5;border-radius:20px;border:1px solid var(--borde-acento);
   background:linear-gradient(170deg,rgba(45,212,191,.10),rgba(139,92,246,.12));
   display:grid;place-items:center;padding:24px;text-align:center}
.hueco small{color:var(--texto-3);font-size:.86rem;line-height:1.6}

/* ---- Servicios ---- */
h2.sec{font-family:var(--titular);font-weight:700;font-size:clamp(1.3rem,3.4vw,1.75rem);
       margin:56px 0 10px;line-height:1.25}
.sec-sub{color:var(--texto-3);margin-bottom:26px;max-width:56ch}
.tarjetas{display:grid;grid-template-columns:repeat(auto-fit,minmax(252px,1fr));gap:16px}
.tarjeta{background:var(--tarjeta);border:1px solid var(--borde-acento);border-radius:18px;
         padding:24px 22px;min-width:0;display:flex;flex-direction:column;gap:9px}
.tarjeta .num{font-family:var(--titular);font-size:.78rem;font-weight:700;
              letter-spacing:.12em;color:var(--turquesa)}
.tarjeta h3{font-family:var(--titular);font-size:1.06rem;font-weight:600;line-height:1.35}
.tarjeta p{color:var(--texto-3);font-size:.96rem;line-height:1.6}

/* ---- De un vistazo ---- */
.vistazo{margin:40px 0 0;border-radius:18px;padding:22px 24px;
         background:var(--tarjeta);border:1px solid var(--borde-acento)}
.vistazo .tit{font-family:var(--titular);font-size:.78rem;font-weight:700;letter-spacing:.12em;
              text-transform:uppercase;color:var(--turquesa);margin-bottom:14px}
.vistazo dl{display:grid;grid-template-columns:minmax(150px,auto) 1fr;gap:11px 20px;margin:0}
.vistazo dt{font-family:var(--titular);font-weight:600;color:var(--texto-3);font-size:.92rem}
.vistazo dd{margin:0;color:var(--texto);font-size:.98rem}
.vistazo dd b{color:var(--turquesa);font-weight:600}

/* ---- Cierre comercial de Sora ---- */
.cierre{margin:56px 0 0;border-radius:22px;padding:34px 30px;
        background:linear-gradient(135deg,rgba(139,92,246,.16),rgba(45,212,191,.08));
        border:1px solid rgba(139,92,246,.35);
        display:grid;grid-template-columns:1.35fr .65fr;gap:30px;align-items:center}
.cierre h2{font-family:var(--titular);font-weight:700;font-size:clamp(1.3rem,3.4vw,1.7rem);
           margin-bottom:12px}
.cierre p{color:var(--texto-2);font-size:1rem}
.precio{text-align:center;background:rgba(7,9,15,.5);border:1px solid var(--borde-acento);
        border-radius:18px;padding:24px 20px}
.precio .n{font-family:var(--titular);font-weight:800;font-size:3rem;line-height:1;
           color:var(--turquesa)}
.precio .t{color:var(--texto-2);font-size:.95rem;margin-top:8px}
.precio .f{color:var(--texto-3);font-size:.82rem;margin-top:14px;
           border-top:1px solid rgba(255,255,255,.12);padding-top:12px}

/* ---- Pie ---- */
.pie{margin-top:52px;border-top:1px solid rgba(255,255,255,.06)}
.pie .wrap{padding-block:24px;display:flex;flex-wrap:wrap;gap:6px 20px;
           font-size:.85rem;color:var(--texto-3)}
.pie b{color:var(--texto-2);font-weight:600}

@media (max-width:760px){
  .hero .rejilla-hero,.cierre{grid-template-columns:1fr;gap:28px}
  .hueco{max-width:290px;margin-inline:auto}
  .vistazo dl{grid-template-columns:1fr;gap:3px}
  .vistazo dt{margin-top:10px}
  .vistazo dt:first-child{margin-top:0}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
'''


CUERPO = u'''
<div class="topbar">
  <div class="wrap">
    <span class="marca"><span class="punto"></span>Sora Systems</span>
    <span class="aviso">Propuesta para %(emp)s. Esta página no es su web: es una idea de cómo podría quedar.</span>
  </div>
</div>

<header class="hero">
  <div class="wrap rejilla-hero">
    <div>
      <div class="eyebrow">%(eyebrow)s</div>
      <h1>%(h1)s</h1>
      <p class="intro">%(sub)s</p>
      <div class="botones">
        <a class="btn btn-1" href="#">%(cta)s</a>
        <a class="btn btn-2" href="#">%(cta2)s</a>
      </div>
    </div>
    <div class="hueco"><small>%(foto)s</small></div>
  </div>
</header>

<section class="wrap">
  <h2 class="sec">%(stit)s</h2>
  <p class="sec-sub">%(sdesc)s</p>
  <div class="tarjetas">%(tarjetas)s</div>

  <div class="vistazo">
    <div class="tit">De un vistazo</div>
    <dl>%(datos)s</dl>
  </div>

  <div class="cierre">
    <div>
      <h2>¿Os gusta cómo queda?</h2>
      <p>Está hecha con vuestro nombre y vuestros servicios, no es una plantilla.
         Si os convence, la dejamos funcionando tal cual, con vuestras fotos y
         vuestros textos definitivos.</p>
      <p style="margin-top:12px">Respondéis al correo y lo hablamos. Si no es el
         momento, decídmelo y no os vuelvo a escribir.</p>
    </div>
    <div class="precio">
      <div class="n">200&nbsp;€</div>
      <div class="t">Pago único. Sin cuotas.</div>
      <div class="f">Oferta de octubre. Termina el 31.</div>
    </div>
  </div>
</section>

<footer class="pie">
  <div class="wrap">
    <span><b>Sora Systems</b> · sorasystems.es</span>
    <span>Propuesta de diseño para %(emp)s · octubre de 2026</span>
  </div>
</footer>
'''


def construir(n):
    tarj = u"".join(
        u'\n    <article class="tarjeta"><div class="num">%02d</div><h3>%s</h3><p>%s</p></article>'
        % (i + 1, t, d) for i, (t, d) in enumerate(n["serv"]))
    dat = u"".join(u'\n      <dt>%s</dt><dd><b>%s</b> · %s</dd>' % kvs
                   for kvs in n["datos"])
    d = dict(n, tarjetas=tarj, datos=dat)
    return CAB.replace(u"@EMP@", n["emp"]) + (CUERPO % d)


if __name__ == "__main__":
    for n in N:
        html = construir(n)

        # Nada sin rellenar, las dos franjas de Sora puestas, el precio, la
        # paleta correcta, y las dos marcas sin mezclar.
        assert u"%(" not in html, n["f"]
        assert html.count(n["emp"]) >= 3, n["f"]
        assert u"no es su web" in html, n["f"]
        assert u"200&nbsp;€" in html, n["f"]
        assert u"Sara Ferreira" not in html, (n["f"], "las dos marcas no se mezclan")
        assert u"#2dd4bf" in html and u"#8b5cf6" in html, n["f"]   # turquesa y violeta
        assert u"#07090f" in html, n["f"]                          # el fondo de la marca
        assert u"FF6B4A" not in html.upper(), (n["f"], "coral viejo")
        assert u"Fraunces" not in html, (n["f"], "tipografia vieja")
        assert u"family=Sora" in html, n["f"]

        io.open(os.path.join(AQUI, "maqueta_%s.html" % n["f"]), "w",
                encoding="utf-8").write(html)
        print(u"%-16s %-34s %s" % (n["f"], n["emp"], n["loc"]))

    print(u"\n%d maquetas rehechas con la identidad de sorasystems.es" % len(N))
