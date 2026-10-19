# -*- coding: utf-8 -*-
u"""Genera las 9 maquetas que faltan, con el mismo molde que la de Clinica
Miramar (ya aprobada).

Que cambia por negocio: el nombre, la localidad, el gancho de portada, los
servicios reales copiados de su web y los tres datos de la tira. Que NO cambia:
la identidad de Sora y las dos franjas, arriba el aviso de que es una propuesta
y abajo el cierre con los 200 EUR. Una sola identidad con contenido propio es
lo que hace un estudio de verdad; cambiar los colores en cada cliente es lo que
hace una plantilla.
"""
import io, json, re

N = [
 dict(f="toledano", emp=u"Gestoría Asesoría Toledano", loc=u"Alicante",
   eyebrow=u"Alicante · desde el centro",
   h1=u"Tu empresa al día, sin que tengas que acordarte",
   sub=u"Fiscal, contable, laboral y jurídico en un solo sitio. Nos ocupamos de los plazos para que tú te ocupes del negocio.",
   cta=u"Pedir una primera cita", cta2=u"Llamar a la oficina",
   foto=u"Aquí iría una foto<br>de la oficina o del equipo",
   stit=u"En qué te ayudamos", sdesc=u"Los cinco servicios que ya ofrecéis, ordenados para que se entiendan de un vistazo.",
   serv=[(u"Asesoría fiscal", u"Impuestos, modelos trimestrales y la renta, presentados a tiempo."),
         (u"Asesoría contable", u"Contabilidad al día y cuentas anuales sin sobresaltos."),
         (u"Asesoría laboral", u"Nóminas, contratos y seguros sociales de tu plantilla."),
         (u"Asesoría jurídica", u"Un abogado que ya conoce tu empresa cuando hace falta."),
         (u"Escrituras y herencias", u"El trámite y el acompañamiento en los momentos delicados.")],
   datos=[(u"Dónde", u"Alicante", u"Atención presencial y a distancia"),
          (u"Primera visita", u"Sin compromiso", u"Te decimos qué necesitas antes de cobrar nada"),
          (u"Respuesta", u"El mismo día", u"Por teléfono, correo o WhatsApp")]),

 dict(f="naranjo", emp=u"Naranjo Asesores", loc=u"Benidorm",
   eyebrow=u"Benidorm · Costa Blanca",
   h1=u"Asesoría para quien tiene el negocio aquí y la vida en otro idioma",
   sub=u"Contable, fiscal, laboral, jurídico y extranjería. Todo lo que necesita una empresa de Benidorm, con quien entiende cómo se trabaja aquí.",
   cta=u"Pedir cita", cta2=u"Escribir por WhatsApp",
   foto=u"Aquí iría una foto<br>de la oficina o del equipo",
   stit=u"Lo que hacemos", sdesc=u"Los cinco servicios que ya ofrecéis en vuestra web.",
   serv=[(u"Contable", u"Libros, balances y cuentas anuales al día."),
         (u"Fiscal", u"Impuestos y modelos, presentados en plazo."),
         (u"Laboral", u"Nóminas, contratos y altas sin que tengas que pensarlo."),
         (u"Jurídico", u"Asesoramiento legal para el día a día de la empresa."),
         (u"Extranjería", u"Residencias, NIE y permisos, con los plazos controlados.")],
   datos=[(u"Dónde", u"Benidorm", u"Y toda la Marina Baixa"),
          (u"Idiomas", u"Te atendemos", u"Sea cual sea el tuyo"),
          (u"Cita", u"Por WhatsApp", u"O por teléfono, como prefieras")]),

 dict(f="dermatologico", emp=u"Centro Dermatológico Estético", loc=u"Alicante",
   eyebrow=u"Alicante · dermatología médica",
   h1=u"Dermatología de verdad, con criterio médico",
   sub=u"Piel, estética y alopecia tratadas por dermatólogos. Primero el diagnóstico; el tratamiento, después.",
   cta=u"Pedir consulta", cta2=u"Llamar a la clínica",
   foto=u"Aquí iría una foto<br>de la consulta o del equipo médico",
   stit=u"Nuestras consultas", sdesc=u"Los cinco tratamientos que ya ofrecéis, cada uno con lo que resuelve.",
   serv=[(u"Dermatología", u"Revisión de lunares, acné, psoriasis y dermatitis."),
         (u"Medicina estética facial", u"Arrugas, volumen y textura, sin cirugía."),
         (u"Medicina estética corporal", u"Contorno y firmeza con aparatología médica."),
         (u"Tratamiento capilar y alopecia", u"Estudio del folículo y plan de recuperación."),
         (u"Tratamiento de manchas", u"Melasma y manchas solares, con protocolo propio.")],
   datos=[(u"Dónde", u"Alicante", u"Consulta en el centro"),
          (u"Primera visita", u"Diagnóstico médico", u"Antes de proponer nada"),
          (u"Cita", u"Por teléfono", u"O desde el formulario de la web")]),

 dict(f="trinum", emp=u"Clínica Trinum", loc=u"Alicante",
   eyebrow=u"Alicante · medicina estética",
   h1=u"Verte bien sin que se note que has hecho nada",
   sub=u"Medicina estética facial y corporal, capilar y cirugía. Un plan hecho para ti, no para un catálogo.",
   cta=u"Pedir valoración", cta2=u"Escribir por WhatsApp",
   foto=u"Aquí iría una foto<br>de la clínica o del equipo",
   stit=u"Tratamientos", sdesc=u"Los cinco que ya ofrecéis en vuestra web.",
   serv=[(u"Medicina estética facial", u"Arrugas, volumen y luminosidad, paso a paso."),
         (u"Medicina estética corporal", u"Contorno, firmeza y grasa localizada."),
         (u"Capilar", u"Tratamiento de la caída con seguimiento."),
         (u"Cirugía estética", u"Lo que no se resuelve sin quirófano, con criterio médico."),
         (u"Mesoterapia facial", u"Hidratación profunda en sesiones cortas.")],
   datos=[(u"Dónde", u"Alicante", u"Clínica propia"),
          (u"Valoración", u"Sin compromiso", u"Plan y precio antes de decidir"),
          (u"Cita", u"Por WhatsApp", u"Respuesta el mismo día")]),

 dict(f="guinova", emp=u"Clínica Guinova", loc=u"Elche",
   eyebrow=u"Elche · medicina estética",
   h1=u"Tratamientos que se notan en el espejo, no en la cara",
   sub=u"Ácido hialurónico, hilos tensores, radiofrecuencia y láser. Resultados graduales, sin pasarse.",
   cta=u"Pedir valoración", cta2=u"Escribir por WhatsApp",
   foto=u"Aquí iría una foto<br>de la clínica o del equipo",
   stit=u"Lo que hacemos", sdesc=u"Los cinco tratamientos que ya ofrecéis.",
   serv=[(u"Ácido hialurónico", u"Volumen y contorno con producto reabsorbible."),
         (u"Peeling químico", u"Renovación de la piel y manchas superficiales."),
         (u"Hilos tensores PDO", u"Tensado sin cirugía, en una sesión."),
         (u"Radiofrecuencia facial y corporal", u"Firmeza progresiva, sin bajas."),
         (u"Depilación láser SHR", u"Sesiones rápidas y cómodas, todo el año.")],
   datos=[(u"Dónde", u"Elche", u"Clínica propia"),
          (u"Primera visita", u"Valoración gratuita", u"Con plan y precio por escrito"),
          (u"Cita", u"Por WhatsApp", u"O por teléfono")]),

 dict(f="teresagonzalez", emp=u"Clínica Dental Teresa González", loc=u"Elda",
   eyebrow=u"Elda · odontología",
   h1=u"La dentista que te explica lo que te va a hacer",
   sub=u"Ortodoncia, implantes y odontopediatría en Elda. Presupuesto claro antes de empezar y sin tratamientos que no necesitas.",
   cta=u"Pedir cita", cta2=u"Llamar a la clínica",
   foto=u"Aquí iría una foto<br>de la clínica o del equipo",
   stit=u"Tratamientos", sdesc=u"Los cinco que ya ofrecéis en vuestra web.",
   serv=[(u"Ortodoncia e Invisalign", u"Alineadores o brackets, con el plan a la vista."),
         (u"Implantes", u"Estudio, colocación y seguimiento del hueso."),
         (u"Odontopediatría", u"La primera visita de los niños, sin miedo."),
         (u"Periodoncia", u"Encías: el tratamiento que salva los dientes."),
         (u"Estética dental", u"Blanqueamiento y carillas, con criterio.")],
   datos=[(u"Dónde", u"Elda", u"Clínica propia"),
          (u"Presupuesto", u"Por escrito", u"Antes de empezar cualquier tratamiento"),
          (u"Urgencias", u"Hueco el mismo día", u"Llámanos y te encajamos")]),

 dict(f="congost", emp=u"Congost Abogados", loc=u"La Nucía",
   eyebrow=u"La Nucía · Marina Baixa",
   h1=u"Un despacho que contesta antes de que el problema crezca",
   sub=u"Empresas, particulares y comunidades de propietarios. Y el apoyo jurídico de asesorías y gestorías que necesitan a un abogado detrás.",
   cta=u"Pedir una consulta", cta2=u"Llamar al despacho",
   foto=u"Aquí iría una foto<br>del despacho o del equipo",
   stit=u"Áreas de trabajo", sdesc=u"Las cinco que ya figuran en vuestra web.",
   serv=[(u"Empresas", u"Contratos, societario y el conflicto que no esperabas."),
         (u"Particulares", u"Familia, herencias, arrendamientos y reclamaciones."),
         (u"Comunidades de propietarios", u"Juntas, impagos y obras, con el presidente al lado."),
         (u"Gestión patrimonial", u"Qué hay, de quién es y cómo se transmite."),
         (u"Servicio a asesorías y gestorías", u"El abogado al que llaman otros profesionales.")],
   datos=[(u"Dónde", u"La Nucía", u"Y toda la Marina Baixa"),
          (u"Primera consulta", u"Te decimos si hay caso", u"Antes de abrir expediente"),
          (u"Respuesta", u"En 24 horas", u"Por teléfono o correo")]),

 dict(f="bodyfriendly", emp=u"Centro Bodyfriendly", loc=u"Torrevieja",
   eyebrow=u"Torrevieja · osteopatía y fisioterapia",
   h1=u"El dolor de espalda tiene una causa, y se puede encontrar",
   sub=u"Osteopatía y fisioterapia en Torrevieja. Sesiones de una hora, manos y criterio, sin máquinas que hacen el trabajo solas.",
   cta=u"Pedir una sesión", cta2=u"Escribir por WhatsApp",
   foto=u"Aquí iría una foto<br>de la camilla o del centro",
   stit=u"Lo que hacemos", sdesc=u"Dos cosas, y las dos bien. Es lo que publicáis en vuestra web y no vamos a inventar más.",
   serv=[(u"Osteopatía", u"Buscamos de dónde viene el dolor, no solo dónde se siente. Valoración de la postura, el movimiento y las compensaciones, y tratamiento manual de la causa."),
         (u"Fisioterapia", u"Recuperación de lesiones, dolor crónico y vuelta al deporte. Sesión individual de una hora y ejercicios para casa que de verdad se pueden hacer.")],
   datos=[(u"Dónde", u"Torrevieja", u"Centro propio"),
          (u"Sesión", u"Una hora", u"Individual, nunca dos pacientes a la vez"),
          (u"Cita", u"Por WhatsApp", u"Te decimos el primer hueco libre")]),

 dict(f="actuagest", emp=u"Actuagest", loc=u"Pilar de la Horadada",
   eyebrow=u"Pilar de la Horadada · Vega Baja",
   h1=u"Los trámites que nadie quiere hacer, hechos",
   sub=u"Tráfico, extranjería, transportes, agricultura y nacionalidad. Vienes, lo dejas y te avisamos cuando está.",
   cta=u"Pedir cita", cta2=u"Llamar a la oficina",
   foto=u"Aquí iría una foto<br>de la oficina o del equipo",
   stit=u"Qué tramitamos", sdesc=u"Los cinco que ya ofrecéis en vuestra web.",
   serv=[(u"Tráfico", u"Transferencias, matriculaciones, bajas y duplicados."),
         (u"Extranjería", u"Residencias, NIE, renovaciones y arraigo."),
         (u"Transportes", u"Tarjetas, autorizaciones y el papeleo de la flota."),
         (u"Agricultura", u"Ayudas, declaraciones y registros del campo."),
         (u"Nacionalidad española", u"El expediente completo y los plazos vigilados.")],
   datos=[(u"Dónde", u"Pilar de la Horadada", u"Y toda la Vega Baja"),
          (u"Presupuesto", u"Antes de empezar", u"Sabes lo que cuesta desde el primer día"),
          (u"Aviso", u"Cuando está listo", u"No tienes que llamar a preguntar")]),
]

CAB = u'''<title>Portada %(emp)s</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Karla:wght@400;500;700&display=swap">

<style>
/* Maqueta de portada. Franja de Sora arriba y abajo, contenido del negocio en medio.
   Luz mediterranea: arena calida, tinta verde-azulada profunda, coral y turquesa de Sora. */
:root{
  --arena:#FDF8F4; --arena-2:#F6E7DC; --tinta:#16323A; --tinta-sv:#4A6670;
  --coral:#FF6B4A; --turquesa:#0E9488; --linea:#E8D8CC; --tarjeta:#FFFFFF;
  --display:"Fraunces",Georgia,"Times New Roman",serif;
  --texto:"Karla",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --arena:#121C20; --arena-2:#1B2A2F; --tinta:#EDF4F2; --tinta-sv:#9DB4B9;
  --coral:#FF8A6E; --turquesa:#3DC2B3; --linea:#28393F; --tarjeta:#1B2A2F;
  color-scheme:dark;
}}
:root[data-theme="dark"]{
  --arena:#121C20; --arena-2:#1B2A2F; --tinta:#EDF4F2; --tinta-sv:#9DB4B9;
  --coral:#FF8A6E; --turquesa:#3DC2B3; --linea:#28393F; --tarjeta:#1B2A2F;
  color-scheme:dark;
}
*{box-sizing:border-box}
body{margin:0;background:var(--arena);color:var(--tinta);font-family:var(--texto);
     font-size:17px;line-height:1.65;-webkit-font-smoothing:antialiased}
.gutter{padding-left:max(16px,env(safe-area-inset-left,0px));
        padding-right:max(16px,env(safe-area-inset-right,0px))}
.centro{max-width:1040px;margin:0 auto}
h1,h2,h3{font-family:var(--display);text-wrap:balance;margin:0;font-weight:600}
a{color:inherit}
.sora-top{background:var(--tinta);color:#FDF8F4}
.sora-top .centro{padding-block:14px;display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline}
.sora-marca{font-weight:700;letter-spacing:.14em;font-size:13px;color:#FF8A6E}
.sora-aviso{font-size:14px;color:#BBD0D3;min-width:0}
.nav .centro{padding-block:22px;display:flex;flex-wrap:wrap;gap:12px 28px;align-items:center}
.logo{font-family:var(--display);font-size:22px;font-weight:700;letter-spacing:-.01em}
.logo span{color:var(--turquesa)}
.menu{display:flex;flex-wrap:wrap;gap:22px;margin-left:auto;font-size:15px;color:var(--tinta-sv)}
.hero{position:relative;overflow:hidden;background:
   radial-gradient(70%% 90%% at 82%% 18%%, color-mix(in srgb,var(--turquesa) 20%%,transparent) 0%%, transparent 62%%),
   radial-gradient(58%% 80%% at 12%% 86%%, color-mix(in srgb,var(--coral) 18%%,transparent) 0%%, transparent 60%%),
   var(--arena)}
.hero .centro{padding-block:68px 60px;display:grid;grid-template-columns:1.15fr .85fr;gap:48px;align-items:center}
.eyebrow{font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:var(--turquesa);font-weight:700}
.hero h1{font-size:clamp(34px,6vw,58px);line-height:1.04;letter-spacing:-.02em;margin:14px 0 18px}
.hero p{font-size:clamp(17px,2.2vw,20px);color:var(--tinta-sv);margin:0 0 30px;max-width:46ch}
.botones{display:flex;flex-wrap:wrap;gap:12px}
.btn{display:inline-block;padding:14px 26px;border-radius:999px;font-weight:700;font-size:16px;
     text-decoration:none;border:2px solid transparent}
.btn-1{background:var(--coral);color:#fff}
.btn-2{border-color:var(--linea);color:var(--tinta)}
.retrato{aspect-ratio:4/5;max-width:100%%;border-radius:200px 200px 24px 24px;
  background:linear-gradient(170deg,color-mix(in srgb,var(--turquesa) 32%%,var(--arena-2)),var(--arena-2));
  border:1px solid var(--linea);display:grid;place-items:center;padding:24px;text-align:center}
.retrato small{color:var(--tinta-sv);font-size:13px;line-height:1.5}
.serv{background:var(--arena-2)}
.serv .centro{padding-block:62px}
.serv h2{font-size:clamp(26px,4vw,36px);letter-spacing:-.01em}
.serv>.centro>p{color:var(--tinta-sv);margin:10px 0 34px;max-width:52ch}
.rejilla{display:grid;grid-template-columns:repeat(auto-fit,minmax(248px,1fr));gap:18px}
.tarjeta{background:var(--tarjeta);border:1px solid var(--linea);border-radius:16px;
         padding:26px 24px;min-width:0;display:flex;flex-direction:column;gap:10px}
.tarjeta .num{font-family:var(--display);font-size:15px;color:var(--coral);font-weight:700}
.tarjeta h3{font-size:19px;line-height:1.3}
.tarjeta p{margin:0;font-size:15px;color:var(--tinta-sv)}
.datos .centro{padding-block:58px;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:30px}
.dato{min-width:0}
.dato .k{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--turquesa);font-weight:700}
.dato .v{font-family:var(--display);font-size:21px;margin-top:6px;line-height:1.35}
.dato .s{font-size:15px;color:var(--tinta-sv);margin-top:4px}
.cierre{background:var(--tinta);color:#FDF8F4}
.cierre .centro{padding-block:52px;display:grid;grid-template-columns:1.4fr 1fr;gap:36px;align-items:center}
.cierre h2{font-size:clamp(24px,3.6vw,34px);color:#fff;letter-spacing:-.01em}
.cierre p{color:#BBD0D3;margin:12px 0 0;max-width:48ch}
.precio{background:rgba(255,255,255,.06);border:1px solid rgba(255,138,110,.4);
        border-radius:18px;padding:26px;text-align:center}
.precio .n{font-family:var(--display);font-size:52px;font-weight:700;color:#FF8A6E;line-height:1}
.precio .t{font-size:15px;color:#BBD0D3;margin-top:8px}
.precio .f{font-size:13px;color:#8FA8AD;margin-top:14px;border-top:1px solid rgba(255,255,255,.12);padding-top:12px}
.pie{background:var(--arena)}
.pie .centro{padding-block:26px;font-size:13px;color:var(--tinta-sv);
             display:flex;flex-wrap:wrap;gap:6px 18px}
.pie b{color:var(--coral)}
@media (max-width:760px){
  .hero .centro,.cierre .centro{grid-template-columns:1fr;gap:34px}
  .retrato{max-width:300px;margin-inline:auto}
  .menu{display:none}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
'''

CUERPO = u'''
<header class="sora-top gutter">
  <div class="centro">
    <span class="sora-marca">SORA SYSTEMS</span>
    <span class="sora-aviso">Propuesta de portada para %(emp)s. Esta página no es su web: es una idea de cómo podría quedar.</span>
  </div>
</header>

<nav class="nav gutter">
  <div class="centro">
    <div class="logo">%(logo)s</div>
    <div class="menu"><span>%(m1)s</span><span>El equipo</span><span>Dónde estamos</span><span>Contacto</span></div>
  </div>
</nav>

<section class="hero gutter">
  <div class="centro">
    <div>
      <div class="eyebrow">%(eyebrow)s</div>
      <h1>%(h1)s</h1>
      <p>%(sub)s</p>
      <div class="botones">
        <a class="btn btn-1" href="#">%(cta)s</a>
        <a class="btn btn-2" href="#">%(cta2)s</a>
      </div>
    </div>
    <div class="retrato"><small>%(foto)s</small></div>
  </div>
</section>

<section class="serv gutter">
  <div class="centro">
    <h2>%(stit)s</h2>
    <p>%(sdesc)s</p>
    <div class="rejilla">%(tarjetas)s</div>
  </div>
</section>

<section class="datos gutter">
  <div class="centro">%(datos)s</div>
</section>

<section class="cierre gutter">
  <div class="centro">
    <div>
      <h2>¿Os gusta cómo queda?</h2>
      <p>Esto es una propuesta, hecha con vuestro nombre y vuestros servicios. Si os convence, la dejamos funcionando tal cual, con vuestras fotos y vuestros textos definitivos.</p>
      <p style="margin-top:14px">Respondéis al correo y lo hablamos. Si no es el momento, decídmelo y no os vuelvo a escribir.</p>
    </div>
    <div class="precio">
      <div class="n">200&nbsp;€</div>
      <div class="t">Pago único. Sin cuotas.</div>
      <div class="f">Oferta de octubre. Termina el 31.</div>
    </div>
  </div>
</section>

<footer class="pie gutter">
  <div class="centro">
    <span><b>Sora Systems</b> · sorasystems.es</span>
    <span>Propuesta de diseño para %(emp)s · octubre de 2026</span>
  </div>
</footer>
'''

def logo(emp):
    p = emp.split()
    return u"%s <span>%s</span>" % (u" ".join(p[:-1]), p[-1]) if len(p) > 1 \
           else u"<span>%s</span>" % emp

for n in N:
    tarj = u"".join(
        u'\n      <article class="tarjeta"><div class="num">%02d</div><h3>%s</h3><p>%s</p></article>'
        % (i + 1, t, d) for i, (t, d) in enumerate(n["serv"]))
    dat = u"".join(
        u'\n    <div class="dato"><div class="k">%s</div><div class="v">%s</div><div class="s">%s</div></div>'
        % kvs for kvs in n["datos"])
    d = dict(n, tarjetas=tarj, datos=dat, logo=logo(n["emp"]),
             m1=n["stit"] if len(n["stit"]) < 18 else u"Servicios")
    html = (CAB % d) + (CUERPO % d)

    # Comprobaciones: ningun hueco sin rellenar y las dos franjas puestas.
    assert u"%(" not in html, n["f"]
    assert html.count(n["emp"]) >= 3, n["f"]
    assert u"no es su web" in html, n["f"]
    assert u"200&nbsp;&euro;" in html or u"200&nbsp;€" in html, n["f"]
    assert u"Sara Ferreira" not in html, (n["f"], "las dos marcas no se mezclan")
    io.open("maqueta_%s.html" % n["f"], "w", encoding="utf-8").write(html)
    print(u"%-16s %-34s %s" % (n["f"], n["emp"], n["loc"]))

print(u"\n%d maquetas escritas" % len(N))
