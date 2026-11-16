"""Índice del libro de Jens Halfwassen para el carrusel vertical.

J. Halfwassen, «Hegel und der spätantike Neuplatonismus. Untersuchungen zur Metaphysik des
Einen und des Nous in Hegels spekulativer und geschichtlicher Deutung» (Hegel-Studien,
Beiheft 40; 2.ª ed., 2005; reimpr. Meiner, 2016).

Uso (desde la raíz del repositorio):
    python scripts/halfwassen.py "ruta/a/tu/ejemplar.pdf"
    (o definir la variable de entorno PLATO_PDF_HALFWASSEN con esa ruta)

Insumo: el PDF del libro (con capa de texto). El texto se extrae a una carpeta temporal y
NO se guarda en el repositorio: el libro tiene derechos reservados.
Resultado:
  - web/halfwassen_datos.js con solo datos de índice: segmentos del índice (capítulo, §,
    apartado y páginas), citas de pasajes de Platón por página y frecuencia por página de
    «Tugend/Arete», «das Eine» y «Nous»;
  - web/config_local.js (excluido de git) con el enlace a tu PDF, para abrirlo desde la página
    cuando la usas en tu computadora.
"""

# PROCESO 0: Paquetes.
# json: escribe los datos para la página web.
import json
# os: lee la ruta del PDF desde una variable de entorno, si no se pasa como argumento.
import os
# re: reconoce las citas de Platón y los términos alemanes.
import re
# shutil: encuentra el programa pdftotext.
import shutil
# subprocess: ejecuta pdftotext.
import subprocess
# sys: lee la ruta del PDF y permite importar secciones.py.
import sys
# tempfile: carpeta temporal para el texto extraído (se borra al terminar).
import tempfile
# collections: cuenta citas y términos.
from collections import Counter, defaultdict
# pathlib: rutas.
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# secciones: lista de secciones Stephanus válidas de cada obra (para validar citas).
from secciones import cargar_corpus  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "web" / "halfwassen_datos.js"
CONFIG_LOCAL = RAIZ / "web" / "config_local.js"   # excluido de git: guarda la ruta de tu PDF
DESFASE = 1               # página del PDF = página impresa + 1
PAGINAS = (13, 470)       # de la Einleitung al final de «Rückblick und Ausblick»

# Índice del libro (pp. 9-12 del original), con las erratas del OCR corregidas.
# (nivel, etiqueta, título, página impresa de inicio); nivel 1 = capítulo, 2 = §, 3 = apartado.
INDICE = [
    (1, "Einl.", "Einleitung", 13),
    (1, "I", "Die Bedeutung des Neuplatonismus für Hegels Denkentwicklung", 27),
    (2, "§ 1", "Erste Begegnungen", 27),
    (2, "§ 2", "Eusebios und der Mittelplatonismus", 39),
    (2, "§ 3", "Spuren mittel- und neuplatonischer Metaphysik in Hegels Frankfurter Schriften", 44),
    (3, "A", "Das Absolute und seine mystische Erfassung", 44),
    (3, "B", "Hegels Rezeption der mittelplatonischen Theologie", 57),
    (3, "C", "Das trinitarische Leben des Geistes: Hegels mittelplatonische Logosspekulation", 67),
    (2, "§ 4", "Die Bedeutung des Neuplatonismus für Hegels Jenaer Grundlegung seiner Dialektik", 78),
    (1, "II", "Die geschichtliche und systematische Ortsbestimmung des Neuplatonismus in Hegels "
              "Philosophie des absoluten Geistes", 99),
    (2, "§ 1", "Die Geschichte der Philosophie als das Zu-sich-Kommen des absoluten Geistes", 99),
    (3, "A", "Zum Problem der Textgrundlagen", 99),
    (3, "B", "Hegels Konzeption der Geschichte der Philosophie", 101),
    (2, "§ 2", "Der Neuplatonismus als Intellektualsystem und Vollendung der antiken Philosophie", 110),
    (3, "A", "Die Epochenstruktur der Philosophiegeschichte", 110),
    (3, "B", "Der Aufgang des Geistes", 118),
    (2, "§ 3", "Neuplatonismus und Christentum: Trinität als Struktur des absoluten Geistes", 126),
    (3, "A", "Transzendenz und immanente Trinität der Gottheit", 126),
    (3, "B", "Die „Idee des Christentums“: Trinität und Inkarnation in Hegels Deutung", 133),
    (3, "C", "Die Idee als unendliche Subjektivität: Defizienzen der neuplatonischen "
             "Transzendenzmetaphysik", 142),
    (2, "§ 4", "Neuplatonismus und griechische Religion: Metaphysik und Mythos", 150),
    (1, "III", "Der Neuplatonismus und seine Quellen in Hegels Sicht: Spekulative Synthese von "
               "Platonismus, Aristotelismus und Pythagoreismus", 160),
    (2, "§ 1", "Der synthetische Charakter des Neuplatonismus", 160),
    (2, "§ 2", "Die Trinität im „Pythagoreismus“: Die spekulative Idee des Absoluten in Platons "
               "Prinzipienlehre", 168),
    (3, "A", "Hegels Deutung der Zahlenlehre", 168),
    (3, "B", "Hegels Deutung der Prinzipienlehre", 175),
    (2, "§ 3", "Die „einfache Idee des Geistes“ bei Platon: Hegels spekulative Deutung des Timaios", 196),
    (3, "A", "Platons Lehre von der Zusammensetzung der Weltseele", 196),
    (3, "B", "Hegels Deutung der Seelenmischung", 202),
    (3, "C", "Das Verhältnis von Prinzip, Ideen und Seele in Hegels noologischer Timaios-Deutung", 209),
    (2, "§ 4", "Der platonische Charakter des Neuplatonismus aus den Perspektiven Hegels und der "
               "neueren Forschung", 216),
    (1, "IV", "Die Metaphysik des Einen bei Plotin und ihre Deutung durch Hegel", 221),
    (2, "§ 1", "Philosophie als Transzendieren: Der dialektische Aufstieg zum Einen", 221),
    (3, "A", "Plotin als Begründer des Neuplatonismus", 221),
    (3, "B", "Plotins Bestimmung der Dialektik: Der Aufstieg zum absoluten Prinzip", 225),
    (3, "C", "Die henologische Reduktion: Der transzendierende Rückgang zum absolut Einen", 231),
    (3, "D", "Der antignostische Charakter der Metaphysik Plotins", 243),
    (3, "E", "Hegels Deutung der Mystik Plotins", 247),
    (2, "§ 2", "Das Eine selbst als absolute Transzendenz bei Plotin und seine Umdeutung bei Hegel", 257),
    (3, "A", "Plotins Explikation der absoluten Transzendenz des Einen", 257),
    (3, "B", "Hegels Umdeutung des transzendenten Absoluten zum reinen Sein", 273),
    (3, "C", "Das Sein und das Absolute bei Hegel und im Platonismus", 286),
    (2, "§ 3", "Hegels Auseinandersetzung mit der negativen Theologie", 299),
    (3, "A", "Hegels Referat der negativen Theologie Plotins", 299),
    (3, "B", "Hegels spekulativ-logische Überwindung der negativen Theologie", 307),
    (1, "V", "Konstitution und Struktur der Noushypostase bei Plotin und ihre Deutung durch Hegel", 321),
    (2, "§ 1", "Die Paradoxie des absoluten Ursprungs", 321),
    (2, "§ 2", "Der Urakt des Denkens: Die Konstitution des Nous", 328),
    (3, "A", "Der Hervorgang des Nous aus dem Einen", 328),
    (3, "B", "Die Konstitution der Selbstbeziehung des Denkens im Transzendenzbezug zum "
             "jenseitigen Einen", 340),
    (2, "§ 3", "Der Nous als einheitliche Fülle der Ideen", 350),
    (3, "A", "Nous und Ideen bei Plotin und Aristoteles", 350),
    (3, "B", "Das Denken als in sich bewegte Einheit der Ideen", 357),
    (2, "§ 4", "Die triadische Einheit des Sich-Denkens bei Plotin und bei Hegel", 365),
    (3, "A", "Der Nous als Subjektivität in Hegels Plotindeutung", 365),
    (3, "B", "Das Selbstbewußtsein als triadische Einheit", 373),
    (1, "VI", "Dialektik und Triadik: Hegel und Proklos", 386),
    (2, "§ 1", "Die Philosophie des Proklos als Vollendung des Neuplatonismus und Erneuerung der "
               "Dialektik Platons", 386),
    (2, "§ 2", "Das Eine und das Viele: Prinzipienlehre und Parmenides-Interpretation bei Proklos "
               "und in Hegels Proklosdeutung", 399),
    (3, "A", "Die prinzipientheoretische Grundlegung der Metaphysik des Proklos", 399),
    (3, "B", "Die negative Dialektik des Einen bei Proklos und ihre Umdeutung durch Hegel", 414),
    (2, "§ 3", "Grundzüge der Triadik des Proklos und ihre Deutung durch Hegel", 432),
    (3, "A", "Proklische Triadik und Hegelsche Dialektik", 432),
    (3, "B", "Der Nous als Trias der Triaden: Sein-Leben-Denken", 445),
    (1, "R", "Rückblick und Ausblick", 463),
]
# Glosa breve en español de cada capítulo (traducción propia, para la etiqueta del carrusel).
GLOSA = {
    "Einl.": "Introducción", "I": "El neoplatonismo en la formación de Hegel",
    "II": "El lugar del neoplatonismo en la historia del espíritu",
    "III": "Las fuentes: Platón, Aristóteles y el pitagorismo",
    "IV": "Lo Uno en Plotino", "V": "El Nous en Plotino", "VI": "Proclo: dialéctica y tríada",
    "R": "Retrospectiva y perspectiva",
}

# Nombres alemanes y abreviaturas de los diálogos (numeración de Trasilo, como en datos/perseus).
NOMBRES = {
    "Euthyphron": 1, "Euthyphr.": 1, "Apologie": 2, "Apol.": 2, "Kriton": 3, "Phaidon": 4,
    "Phaid.": 4, "Phaed.": 4, "Kratylos": 5, "Krat.": 5, "Theaitetos": 6, "Theaitet": 6,
    "Theait.": 6, "Theaet.": 6, "Sophistes": 7, "Soph.": 7, "Politikos": 8, "Polit.": 8,
    "Parmenides": 9, "Parm.": 9, "Philebos": 10, "Phileb.": 10, "Phil.": 10, "Symposion": 11,
    "Symp.": 11, "Phaidros": 12, "Phaidr.": 12, "Phaedr.": 12, "Alkibiades": 13, "Alk.": 13,
    "Charmides": 18, "Charm.": 18, "Laches": 19, "Lach.": 19, "Lysis": 20, "Euthydemos": 21,
    "Euthyd.": 21, "Protagoras": 22, "Prot.": 22, "Gorgias": 23, "Gorg.": 23, "Menon": 24,
    "Men.": 24, "Menexenos": 28, "Kleitophon": 29, "Politeia": 30, "Pol.": 30, "Rep.": 30,
    "Resp.": 30, "Staat": 30, "Timaios": 31, "Tim.": 31, "Kritias": 32, "Nomoi": 34, "Nom.": 34,
    "Leg.": 34, "Epinomis": 35, "Epin.": 35, "Ep.": 36, "Epist.": 36,
}
_NOMBRE_RE = "|".join(re.escape(k) for k in sorted(NOMBRES, key=len, reverse=True))
# página + letra(s) [+ línea] [+ f/ff] [+ rango «- [página] letra»]
_REF = (r"(\d{2,3})\s?([A-E]{1,2}|[a-e])(?:ff?\.?)?(?![A-Za-zäöüß])(?:\s?\d{1,2}(?!\d))?(\s?ff?\.?)?"
        r"(?:\s?[-–]\s?(?:(\d{2,3})\s?)?([A-Ea-e])(?![A-Za-zäöüß])(?:\s?\d{1,2}(?!\d))?)?")
RE_CITA = re.compile(rf"(?<![A-Za-zäöüß])(In\s+)?({_NOMBRE_RE})\s?(?:[IVX]{{1,4}}\.?\s?)?{_REF}")
RE_SIGUE = re.compile(rf"\s?,\s?{_REF}")

# Términos alemanes que corresponden a cada término griego de la concordancia.
TERMINOS_DE = {
    "arete": re.compile(r"\b(?:Tugend\w*|Arete)\b"),
    "hen": re.compile(r"\b(?:das|des|dem|vom|zum|im|am|beim)\s+(?:\w+\s+)?Ein(?:e|en|em)\b|\bHen\b"),
    "nous": re.compile(r"\bNous\w*"),
}


# PROCESO 1: Extraer el texto del PDF a una carpeta temporal.
# Antes: PDF de 511 páginas. Después: lista de páginas de texto (índice 0 = página 1 del PDF).
def paginas_del_pdf(pdf: Path) -> list[str]:
    """Ruta del PDF → texto de cada página (no se guarda en disco fuera de la carpeta temporal)."""
    exe = shutil.which("pdftotext") or r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"
    with tempfile.TemporaryDirectory() as tmp:
        txt = Path(tmp) / "libro.txt"
        subprocess.run([exe, "-enc", "UTF-8", str(pdf), str(txt)], check=True)
        return txt.read_text(encoding="utf-8").split("\f")


# PROCESO 2: Reconocer las citas de Platón y validarlas.
# Antes: «Politeia 508 A - 509 C», «Soph. 248 E ff», «Tim. 29 A, 30 B».
# Después: secciones existentes (30:508a ... 30:509c, 7:248e, 31:29a, 31:30b).
def expandir(obra: int, pag: str, letras: str, pag_fin, letra_fin, abierto: bool,
             orden: dict[int, list[str]]) -> list[str]:
    """Una referencia → lista de secciones Stephanus válidas (expande rangos cortos)."""
    secs = orden[obra]
    inicio = [f"{pag}{l.lower()}" for l in letras]
    validas = [s for s in inicio if s in secs]
    if letra_fin and not abierto and validas:
        fin = f"{pag_fin or pag}{letra_fin.lower()}"
        if fin in secs:
            i, j = secs.index(validas[0]), secs.index(fin)
            if 0 < j - i <= 12:
                return secs[i:j + 1]
    return validas


def citas_por_pagina(paginas: list[str], orden: dict[int, list[str]]) -> list[dict]:
    """Páginas del libro → [{p: página impresa, s: "obra:sección"}] sin duplicados."""
    vistas, citas = set(), []
    for i, texto in enumerate(paginas):
        impresa = i + 1 - DESFASE
        if not (PAGINAS[0] <= impresa <= PAGINAS[1]):
            continue
        plano = " ".join(texto.split())
        for m in RE_CITA.finditer(plano):
            if m.group(1):          # «In Parm.», «In Tim.»: comentario de Proclo, no Platón
                continue
            obra = NOMBRES[m.group(2)]
            refs = [m.groups()[2:8]]
            fin = m.end()
            while (m2 := RE_SIGUE.match(plano, fin)):
                refs.append(m2.groups()[0:6])
                fin = m2.end()
            for pag, letras, abierto, pag_fin, letra_fin in (r[:5] for r in refs):
                for sec in expandir(obra, pag, letras, pag_fin, letra_fin, bool(abierto), orden):
                    clave = (impresa, f"{obra}:{sec}")
                    if clave not in vistas:
                        vistas.add(clave)
                        citas.append({"p": impresa, "s": f"{obra}:{sec}"})
    return citas


# PROCESO 3: Frecuencia por página de los términos alemanes.
# Antes: texto de cada página. Después: {"hen": {"182": 7, ...}, "nous": {...}, "arete": {...}}.
def densidad(paginas: list[str]) -> dict[str, dict[str, int]]:
    """Páginas → apariciones de cada término alemán por página impresa."""
    salida = defaultdict(dict)
    for i, texto in enumerate(paginas):
        impresa = i + 1 - DESFASE
        if not (PAGINAS[0] <= impresa <= PAGINAS[1]):
            continue
        plano = " ".join(texto.split())
        for termino, patron in TERMINOS_DE.items():
            k = len(patron.findall(plano))
            if k:
                salida[termino][str(impresa)] = k
    return dict(salida)


# PROCESO 4: Segmentos del índice con su página final.
# Antes: lista de títulos con página de inicio. Después: cada segmento con inicio y fin.
def segmentos() -> list[dict]:
    """INDICE → [{nivel, etq, cap, titulo, glosa, ini, fin}]."""
    salida, cap = [], None
    for i, (nivel, etq, titulo, ini) in enumerate(INDICE):
        if nivel == 1:
            cap = etq
        fin = PAGINAS[1]
        for nivel2, _, _, ini2 in INDICE[i + 1:]:
            if nivel2 <= nivel:
                fin = max(ini, ini2 - 1)
                break
        salida.append({"nivel": nivel, "etq": etq, "cap": cap, "titulo": titulo,
                       "glosa": GLOSA.get(etq, "") if nivel == 1 else "", "ini": ini, "fin": fin})
    return salida


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PLATO_PDF_HALFWASSEN")
    if not ruta:
        sys.exit("Indica la ruta del PDF como argumento o en PLATO_PDF_HALFWASSEN.")
    pdf = Path(ruta)
    paginas = paginas_del_pdf(pdf)
    orden = {n: [s["id"] for s in o["secciones"]] for n, o in cargar_corpus().items()}
    citas = citas_por_pagina(paginas, orden)
    datos = {
        "autor": "Jens Halfwassen",
        "titulo": "Hegel und der spätantike Neuplatonismus",
        "subtitulo": "Untersuchungen zur Metaphysik des Einen und des Nous in Hegels spekulativer "
                     "und geschichtlicher Deutung",
        "edicion": "Hegel-Studien, Beiheft 40. 2.ª ed. 2005; reimpr. Meiner, Hamburgo, 2016",
        "desfase": DESFASE, "paginas": PAGINAS,
        "segmentos": segmentos(), "citas": citas, "densidad": densidad(paginas),
    }
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text("window.LIBRO = " + json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
                      + ";\n", encoding="utf-8")
    CONFIG_LOCAL.write_text(f"window.PDF_LOCAL = {json.dumps(pdf.resolve().as_uri())};\n", encoding="utf-8")
    por_obra = Counter(int(c["s"].split(":")[0]) for c in citas)
    print(f"Citas de Platón: {len(citas)} en {len({c['p'] for c in citas})} páginas | "
          f"por obra: {dict(por_obra.most_common(8))} | {SALIDA.stat().st_size / 1e3:.0f} KB")
