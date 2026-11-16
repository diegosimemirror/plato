"""Divide cada obra en secciones Stephanus (70a, 70b, ...) con su texto griego, inglés y notas.

Uso como módulo:
    from secciones import cargar_corpus
    corpus = cargar_corpus()   # {n_obra: {"titulo": ..., "secciones": [...]}}

Insumo: datos/perseus/griego/*.xml y datos/perseus/ingles/*.xml (TEI de Perseus).
Resultado: por obra, la lista ordenada de secciones; cada sección trae el texto griego,
el texto inglés y las notas del traductor Loeb ancladas en ella.
"""

# PROCESO 0: Paquetes.
# re: limpia espacios y separa el número de obra del nombre de archivo.
import re
# xml.etree.ElementTree: recorre el XML TEI en orden de lectura.
import xml.etree.ElementTree as ET
# pathlib: rutas a los datos.
from pathlib import Path

DATOS = Path(__file__).resolve().parent.parent / "datos" / "perseus"
TEI = "{http://www.tei-c.org/ns/1.0}"


def _local(tag: str) -> str:
    """'{ns}milestone' → 'milestone'."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


# PROCESO 1: Recorrer un XML y repartir su texto entre secciones Stephanus.
# Antes: árbol TEI con hitos <milestone unit="section" n="70a"/> intercalados en el texto.
# Después: {"70a": {"texto": "...", "notas": [...]}, ...} en orden de aparición.
def leer_secciones(ruta: Path) -> dict[str, dict]:
    """XML TEI → secciones ordenadas con su texto y sus notas."""
    raiz = ET.parse(ruta).getroot()
    cuerpo = raiz.find(f".//{TEI}body")
    secciones: dict[str, dict] = {}
    estado = {"actual": None}

    def agregar(texto):
        if texto and estado["actual"]:
            secciones[estado["actual"]]["partes"].append(texto)

    def recorrer(el):
        tag = _local(el.tag)
        if tag == "note":
            # Las notas del traductor no forman parte del texto: se guardan aparte.
            if estado["actual"]:
                nota = " ".join("".join(el.itertext()).split())
                if nota:
                    secciones[estado["actual"]]["notas"].append(nota)
            agregar(el.tail)
            return
        if tag == "milestone" and el.get("unit") == "section":
            n = el.get("n")
            estado["actual"] = n
            secciones.setdefault(n, {"partes": [], "notas": []})
        elif tag == "label":
            # Etiqueta de hablante (ΣΩ., Soc.): se conserva entre corchetes para la lectura.
            agregar(f" [{''.join(el.itertext()).strip()}] ")
            agregar(el.tail)
            return
        elif tag in ("head", "bibl"):
            agregar(el.tail)
            return
        agregar(el.text)
        for hijo in el:
            recorrer(hijo)
        agregar(el.tail)

    recorrer(cuerpo)
    return {k: {"texto": " ".join("".join(v["partes"]).split()), "notas": v["notas"]}
            for k, v in secciones.items()}


# PROCESO 2: Unir griego e inglés por sección.
# Antes: dos diccionarios por obra (griego, inglés). Después: una lista ordenada según el
# griego, con los campos id, griego, ingles y notas (las notas vienen del inglés Loeb).
def cargar_corpus() -> dict[int, dict]:
    """Nada → {n_obra: {"titulo": str, "secciones": [{id, griego, ingles, notas}, ...]}}."""
    corpus = {}
    for ruta_gr in sorted((DATOS / "griego").glob("*.xml")):
        n = int(ruta_gr.name[:2])
        titulo = ruta_gr.name.split("_")[1].replace("-", " ")
        ruta_en = next((DATOS / "ingles").glob(f"{n:02d}_*.xml"))
        gr, en = leer_secciones(ruta_gr), leer_secciones(ruta_en)
        ids = list(gr) + [k for k in en if k not in gr]
        corpus[n] = {
            "titulo": titulo,
            "secciones": [{"id": k,
                           "griego": gr.get(k, {}).get("texto", ""),
                           "ingles": en.get(k, {}).get("texto", ""),
                           "notas": en.get(k, {}).get("notas", [])} for k in ids],
        }
    return corpus
