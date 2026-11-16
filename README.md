# Navegador de textos: Platón

Corpus bilingüe (griego e inglés) de las obras de Platón, tomado de Perseus Digital Library,
y herramientas para estudiarlo.

## Contenido

| Carpeta | Qué contiene |
|---|---|
| `datos/perseus/griego/` | 36 obras en griego, edición de Burnet (Oxford), XML TEI |
| `datos/perseus/ingles/` | 36 obras en inglés, traducción Loeb (Fowler, Lamb, Shorey, Bury), XML TEI |
| `datos/perseus/LEEME.md` | Fuente, versión exacta, licencia e índice de obras con títulos en español |
| `scripts/descargar_perseus.py` | Vuelve a descargar y verificar los 72 archivos |
| `scripts/secciones.py` | Divide cada obra en secciones Stephanus alineadas griego-inglés, con las notas Loeb |
| `scripts/arete.py` | Primer prototipo: concordancia de ἀρετή → `web/arete.html` |
| `scripts/halfwassen.py` | Índice del libro de Halfwassen (segmentos, citas de Platón, densidad de términos) → `web/halfwassen_datos.js` |
| `scripts/concordancia.py` | Concordancia de ἀρετή, ἕν y νοῦς con remisiones y ecos → `web/concordancia_datos.js` |
| `web/concordancia.html` | **Navegador de textos: Platón**: diálogos en horizontal y el libro de Halfwassen en vertical |

## Ver el navegador

- **En la web:** https://diegosimemirror.github.io/plato/ (GitHub Pages, una vez activado).
- **En tu computadora:** abrir `web/concordancia.html` con doble clic.

El libro de Halfwassen no está en el repositorio. Para leer una página citada, pulsa «Vincular mi PDF
del libro» y elige tu ejemplar: se abre en tu navegador y no se sube a ningún sitio.

Para regenerar los datos:

```
python scripts/halfwassen.py "ruta/al/libro.pdf"
python scripts/concordancia.py
```

`halfwassen.py` necesita `pdftotext` (incluido con Git para Windows). El texto del libro se extrae a
una carpeta temporal y no se guarda: el libro tiene derechos reservados y el repositorio solo
contiene su índice (títulos del índice, números de página y referencias a Platón). **No subir el PDF.**

## Volver a descargar los textos

```
python scripts/descargar_perseus.py
```

Solo usa la biblioteca estándar de Python (3.9 o superior). La versión exacta de Perseus que se descargó
queda anotada en `datos/perseus/LEEME.md`.

## Herramientas en línea de Perseus

Perseus no ofrece una concordancia descargable, pero su búsqueda permite consultar palabra por palabra
desde el navegador:

- **Búsqueda (concordancia por palabra):** muestra cada aparición en contexto con su número Stephanus.
  Con «Expand» incluye todas las formas de la palabra, y se puede limitar a una obra. Ejemplo, ἀρετή en el *Menón*:
  https://www.perseus.tufts.edu/hopper/searchresults?target=greek&all_words=a%29reth%2F&all_words_expand=on&documents=Perseus%3Atext%3A1999.01.0177%3Atext%3DMeno
- **Word Study Tool** (`/hopper/morph`): análisis morfológico y enlace a los diccionarios LSJ, Middle Liddell y Autenrieth.
- **Frecuencia** (`/hopper/wordfreq`): frecuencia de una palabra por obra.
- **Vocabulary Tool**: lista de palabras de una obra, exportable a XML.

Estas herramientas solo funcionan desde un navegador; el sitio rechaza las consultas automáticas (HTTP 405).

## Licencias

- **Código** (`scripts/`): MIT, ver `LICENSE`.
- **Textos** (`datos/perseus/`): CC BY-SA 4.0, © Perseus Digital Library, Tufts University.
  Las obras derivadas de los textos deben compartirse con la misma licencia; eso incluye los
  datos de `web/arete_datos.js` y `web/concordancia_datos.js`, que contienen esos textos.
- **Índice del libro** (`web/halfwassen_datos.js`): solo títulos del índice, números de página y
  referencias a Platón de J. Halfwassen, *Hegel und der spätantike Neuplatonismus* (Meiner).
  El texto del libro no se reproduce.
