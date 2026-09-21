# Radar de Retención

Robot de auditoría de carrito abandonado para **Sora Systems**.

Produce el diagnóstico que abre la conversación de venta: qué plataforma de
email usa una tienda, qué le llega al cliente que abandona un carrito, y
cuánto dinero está dejando sobre la mesa.

El informe resultante es lo que se manda por correo de hallazgo, lo que
alimenta el estudio sectorial, y lo que se le entrega a una agencia con su
marca en la modalidad de marca blanca.

---

## Las cuatro etapas

```
 1. DETECTAR          2. SONDEAR           3. ESCUCHAR        4. INFORMAR
 ─────────────        ─────────────        ─────────────      ─────────────
 Qué plataforma  →    Suscribirse y   →    Leer el buzón  →   Puntuar y
 y qué ESP lleva      abandonar un         durante 72 h       generar el PDF
 cada tienda          carrito
 HTTP, sin buzón      Playwright           IMAP               reportlab
```

**La etapa 1 es la más valiosa y la única que no necesita nada montado.**
Con una petición HTTP por tienda clasifica una lista entera en minutos.

---

## Por qué la etapa 1 prioriza Mailchimp

Verificado el 21/09/2026 sobre la guía oficial del programa de partners de
Klaviyo: el escalón **Silver exige 250 $ de MRR referido Y 250 $ de MRR
gestionado**, las dos cosas a la vez.

Adoptar la cuenta de una tienda que **ya paga Klaviyo** solo genera MRR
gestionado. **Migrar** una tienda desde Mailchimp genera las dos métricas de
golpe. De ahí el orden de prioridad que aplica `Deteccion.prioridad`:

| Prioridad | Qué tiene la tienda | Por qué |
|---|---|---|
| **máxima** | Mailchimp, Brevo, ActiveCampaign, Drip | Migrable → referido + gestionado |
| media | Ninguna plataforma | Migrable, pero la venta es más larga |
| baja | Ya tiene Klaviyo | Solo genera gestionado |

---

## Uso

```bash
pip install -r requirements.txt

# 1. Clasificar una lista de candidatas (lo primero, siempre)
python3 cli.py detectar --entrada datos/tiendas.csv --salida datos/clasificadas.csv

# 2. Abandonar un carrito en una tienda
python3 cli.py sondear --url https://tienda.es

# 3. (la escucha del buzón se lanza desde radar/buzon.py con las
#     credenciales en el entorno, ver abajo)

# 4. Puntuar y generar el PDF
python3 cli.py informar --url https://tienda.es --visitas 30000 --ticket 60

# Informe de ejemplo, sin tocar ninguna tienda real
python3 cli.py demo
```

### Variables de entorno

Nunca escribas credenciales en el código ni las subas al repositorio.

```bash
export RADAR_ALIAS_BASE="auditoria@sorasystems.es"   # buzón con catch-all
export RADAR_IMAP_SERVIDOR="imap.tudominio.com"
export RADAR_IMAP_USUARIO="auditoria@sorasystems.es"
export RADAR_IMAP_CLAVE="..."
```

El buzón necesita admitir **subetiquetas** (`auditoria+loquesea@…`) o
catch-all. Cada tienda recibe un alias distinto, y ese alias es lo que
permite saber después qué tienda ha mandado cada correo.

---

## Buena vecindad

No es opcional, y está puesto en el código:

- **Una sola sonda por tienda.** Nunca en bucle.
- **Pausa de 20 a 45 segundos** entre tiendas (`pausa_educada()`).
- **La sonda se detiene al introducir el email.** No toca pasarelas de pago.
- `--identificarse` pone un agente de usuario identificable con una URL
  explicativa, por si se prefiere ser transparente.

---

## Cuando una tienda concreta falla

Casi siempre es un selector que esa tienda no usa. Se añade el suyo al final
de la lista que corresponda en **`radar/selectores.py`** y vuelve a funcionar.
Ese fichero está pensado para tocarse a menudo; el resto no.

Si cambia un dominio de servicio de una plataforma (Klaviyo, Mailchimp…),
el fichero a tocar es **`radar/huellas.py`**.

---

## Estructura

```
radar/
  modelos.py      Estructuras de datos y la lógica de prioridad
  huellas.py      Firmas de plataformas y ESP        ← se toca al cambiar un CDN
  detectar.py     Etapa 1: HTTP, en paralelo
  selectores.py   Candidatos de selector por paso    ← se toca a menudo
  sonda.py        Etapa 2: Playwright
  buzon.py        Etapa 3: IMAP y clasificación de correos
  rubrica.py      Etapa 4a: puntuación y estimación de euros
  informe.py      Etapa 4b: el PDF de dos páginas
  alias.py        Alias único por tienda
  almacen.py      Persistencia en SQLite
cli.py            Orquestador
pruebas/tienda_falsa/   Tienda de prueba para validar el flujo en local
```

---

## Sobre las cifras del informe

La estimación de euros perdidos **se presenta siempre como estimación**, con
los supuestos impresos en el propio PDF: 70 % de carritos abandonados y 8 %
de recuperación con una secuencia bien montada.

Cuando el cliente da sus cifras reales se pasa `--cifras-reales` y el informe
lo dice. Un número inflado se descubre en la primera reunión y se lleva por
delante la credibilidad de todo lo demás.

---

## Probarlo en local sin tocar ninguna tienda

```bash
cd pruebas/tienda_falsa && python3 -m http.server 8777 &
cd ../.. && python3 cli.py sondear --url http://localhost:8777/
```

La tienda falsa lleva huellas de Shopify y Klaviyo, banner de cookies,
popup de suscripción, carrito y checkout, así que ejercita el flujo entero.

---

## La calculadora pública (`web/calculadora.html`)

Página autónoma, sin dependencias externas, lista para desplegar en
sorasystems.es desde Netlify. Es la pieza que convierte el embudo en
entrante: el visitante mete tres cifras, ve lo que pierde al instante y de
ahí pasa a pedir la auditoría gratis que ejecuta este mismo robot.

**Usa los mismos supuestos que `radar/rubrica.py`** (70 % de abandono, 8 %
de recuperación), pero es **deliberadamente conservadora**: su suelo de
recuperación es 0,02 frente al 0,01 de la rúbrica. Así la auditoría real
casi siempre revela una cifra mayor que la que vio el cliente en la web.
Al revés — prometer más de lo que luego aparece — se paga en la primera
reunión.

Si cambias un supuesto en `rubrica.py`, cámbialo también en el `<script>`
de la calculadora. Una cifra distinta en la web y en el informe resta
credibilidad justo en el momento de la venta.
