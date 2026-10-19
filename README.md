# Propuestas de Sora Systems

Esta rama (`master`) **no lleva código**: es el sitio público que sirve GitHub
Pages. El código del proyecto está en la rama de trabajo.

Cada carpeta es una propuesta de portada para un negocio, con su propia
dirección:

```
propuestas.sorasystems.es/clinica-miramar
propuestas.sorasystems.es/centro-dermatologico-estetico
...
```

Cada propuesta se envía por correo únicamente al negocio para el que está
hecha. La raíz del dominio **no las lista**: la cartera de clientes
potenciales no se publica.

## Cómo está servido

| | |
|---|---|
| Origen | rama `master`, carpeta raíz |
| Dominio | `propuestas.sorasystems.es` (CNAME a `saraferreirafdez.github.io`) |
| `.nojekyll` | para que Pages sirva el HTML tal cual, sin pasarlo por Jekyll |

## Por qué todas llevan `noindex`

Son páginas públicas con el nombre de un negocio ajeno. Que se vean con el
enlace es el objetivo; que aparezcan en Google no. Todas llevan
`<meta name="robots" content="noindex,nofollow,noarchive">` y una franja
arriba que dice, antes que nada, que esa página no es la web del negocio sino
una propuesta de Sora Systems.

## Si hay que regenerarlas

Las páginas no se editan a mano. Salen de las maquetas originales envueltas
como documentos completos (doctype, `charset`, `viewport`, `noindex`) por el
script `construir_sitio.py`. Editar la maqueta y volver a generar; nunca al
revés.
