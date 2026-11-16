"""Descarga las 36 obras de Platón (griego e inglés) del repositorio de Perseus en GitHub.

Uso (desde la raíz del repositorio):
    python scripts/descargar_perseus.py

Insumo: repositorio PerseusDL/canonical-greekLit, carpeta data/tlg0059 (código TLG de Platón).
Resultado: datos/perseus/griego/ (36 XML, edición de Burnet), datos/perseus/ingles/
(36 XML, traducción Loeb) y datos/perseus/LEEME.md con fuente, versión, licencia e índice.
"""

# PROCESO 0: Paquetes.
# json: lee las respuestas de la API de GitHub.
import json
# re: extrae el título de cada obra de su ficha __cts__.xml.
import re
# time: pausa breve entre descargas para no saturar el servidor.
import time
# urllib.request: descarga archivos sin instalar paquetes externos.
import urllib.request
# xml.etree.ElementTree: comprueba que cada archivo descargado sea XML válido.
import xml.etree.ElementTree as ET
# pathlib: arma las rutas de salida.
from pathlib import Path

REPO = "PerseusDL/canonical-greekLit"
API = f"https://api.github.com/repos/{REPO}"
RAW = f"https://raw.githubusercontent.com/{REPO}"
DESTINO = Path(__file__).resolve().parent.parent / "datos" / "perseus"

# Títulos en español (canon de Trasilo; el índice coincide con tlg001-tlg036).
TITULOS_ES = [
    "Eutifrón", "Apología de Sócrates", "Critón", "Fedón", "Crátilo", "Teeteto", "Sofista",
    "Político", "Parménides", "Filebo", "Banquete", "Fedro", "Alcibíades I", "Alcibíades II",
    "Hiparco", "Los rivales (Amantes)", "Teages", "Cármides", "Laques", "Lisis", "Eutidemo",
    "Protágoras", "Gorgias", "Menón", "Hipias mayor", "Hipias menor", "Ion", "Menéxeno",
    "Clitofonte", "República", "Timeo", "Critias", "Minos", "Leyes", "Epínomis", "Cartas",
]


def leer(url: str) -> bytes:
    """URL → contenido en bytes."""
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


# PROCESO 1: Fijar la versión del repositorio de Perseus.
# Antes: rama master, que puede cambiar. Después: un commit concreto (sha), para que
# la descarga sea reproducible y quede anotada en el LEEME.
def version_actual() -> str:
    """Nada → sha del último commit de master en canonical-greekLit."""
    return json.loads(leer(f"{API}/commits/master"))["sha"]


# PROCESO 2: Listar los XML de Platón en esa versión.
# Antes: árbol completo del repositorio (miles de archivos).
# Después: lista de (ruta, tamaño) de las ediciones de tlg0059, sin las fichas __cts__.
def listar_ediciones(sha: str) -> list[tuple[str, int]]:
    """sha → [(ruta, tamaño en bytes), ...] de las ediciones de Platón."""
    arbol = json.loads(leer(f"{API}/git/trees/{sha}?recursive=1"))
    if arbol.get("truncated"):
        raise RuntimeError("La API devolvió el árbol incompleto; reintentar más tarde.")
    return sorted(
        (x["path"], x["size"]) for x in arbol["tree"]
        if x["path"].startswith("data/tlg0059/") and x["path"].endswith(".xml")
        and "__cts__" not in x["path"]
    )


# PROCESO 3: Descargar y verificar cada edición.
# Antes: ruta en GitHub. Después: archivo NN_Titulo_edicion.xml en griego/ o ingles/,
# comprobado por tamaño (igual al publicado) y por estructura (XML válido).
def descargar(sha: str, ediciones: list[tuple[str, int]]) -> list[dict]:
    """sha + lista de ediciones → registros de lo descargado (lanza error si algo falla)."""
    titulos_en: dict[str, str] = {}
    registros, errores = [], []
    for ruta, tamano in ediciones:
        obra = ruta.split("/")[2]                       # tlg001 ... tlg036
        n = int(obra[3:])
        if obra not in titulos_en:
            cts = leer(f"{RAW}/{sha}/data/tlg0059/{obra}/__cts__.xml").decode("utf-8")
            m = re.search(r"<ti:title[^>]*>(.*?)</ti:title>", cts, re.S)
            titulos_en[obra] = " ".join(m.group(1).split())
        edicion = ruta.rsplit("/", 1)[1].split(".", 2)[2]  # perseus-grc2.xml, perseus-eng2.xml
        carpeta = "griego" if "grc" in edicion else "ingles"
        nombre = f"{n:02d}_{titulos_en[obra].replace(' ', '-')}_{edicion}"
        datos = leer(f"{RAW}/{sha}/{ruta}")
        try:
            ET.fromstring(datos)
            xml_ok = True
        except ET.ParseError:
            xml_ok = False
        if len(datos) != tamano or not xml_ok:
            errores.append(nombre)
        (DESTINO / carpeta).mkdir(parents=True, exist_ok=True)
        (DESTINO / carpeta / nombre).write_bytes(datos)
        registros.append({"n": n, "es": TITULOS_ES[n - 1], "en": titulos_en[obra],
                          "carpeta": carpeta, "archivo": nombre, "bytes": len(datos)})
        time.sleep(0.2)
    if errores:
        raise RuntimeError(f"Archivos con tamaño distinto o XML inválido: {errores}")
    return registros


# PROCESO 4: Escribir el LEEME de los datos.
# Antes: registros de la descarga. Después: datos/perseus/LEEME.md con fuente, versión,
# licencia (CC BY-SA 4.0, distinta de la licencia MIT del código) e índice de obras.
def escribir_leeme(sha: str, registros: list[dict]) -> None:
    """sha + registros → LEEME.md."""
    obras: dict[int, dict] = {}
    for r in registros:
        o = obras.setdefault(r["n"], {"es": r["es"], "en": r["en"]})
        o[r["carpeta"]] = r["archivo"]
    mb = sum(r["bytes"] for r in registros) / 1e6
    lineas = [
        "# Textos de Platón: Perseus Digital Library (griego e inglés)", "",
        f"Fuente: https://github.com/{REPO}, carpeta `data/tlg0059` (código TLG de Platón),",
        f"commit `{sha}`. Generado con `scripts/descargar_perseus.py`.", "",
        "- **griego/**: edición de John Burnet, *Platonis Opera*, Oxford Classical Texts, tomos I-V.",
        "- **ingles/**: *Plato in Twelve Volumes*, Loeb Classical Library (traducciones de "
        "H. N. Fowler, W. R. M. Lamb, P. Shorey y R. G. Bury).",
        "- Formato XML TEI, dividido según la paginación de Stephanus (17a, 17b, ...).",
        f"- {len(obras)} obras x 2 idiomas = {len(registros)} archivos ({mb:.1f} MB); cada uno "
        "verificado por tamaño y como XML válido.",
        "- Contiene las 36 obras del canon de Trasilo (35 diálogos + Cartas); no contiene los "
        "apócrifos (Definiciones, Axíoco, Erixias, etc.).", "",
        "**Licencia de estos textos:** CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), "
        "© Perseus Digital Library, Tufts University. La licencia MIT del repositorio cubre solo el "
        "código, no estos textos. Las obras derivadas de los textos deben compartirse con la misma licencia.", "",
        "| N.º | Obra | Título en Perseus | Griego | Inglés |",
        "|---|---|---|---|---|",
    ]
    for n in sorted(obras):
        o = obras[n]
        lineas.append(f"| {n} | {o['es']} | {o['en']} | `griego/{o.get('griego', '')}` "
                      f"| `ingles/{o.get('ingles', '')}` |")
    (DESTINO / "LEEME.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sha = version_actual()
    ediciones = listar_ediciones(sha)
    registros = descargar(sha, ediciones)
    escribir_leeme(sha, registros)
    print(f"Listo: {len(registros)} archivos en {DESTINO} (commit {sha[:7]}).")
