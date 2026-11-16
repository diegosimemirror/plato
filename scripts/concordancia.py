"""Concordancia de varios términos (ἀρετή, ἕν, νοῦς) en el corpus platónico y puentes entre diálogos.

Uso (desde la raíz del repositorio; primero scripts/halfwassen.py si se quiere el carrusel vertical):
    python scripts/concordancia.py

Insumo: datos/perseus/ (vía secciones.py) y, si existe, web/halfwassen_datos.js.
Resultado: web/concordancia_datos.js con
  - terminos: cada término con sus formas, glosa y lentes temáticas;
  - obras: las 36 obras con su lista de secciones Stephanus y las apariciones de cada término;
  - pasajes: las secciones con algún término, las de destino de remisiones y las que cita
    Halfwassen, con griego, inglés, apariciones y lentes por término;
  - puentes: remisiones de las notas Loeb y ecos de vocabulario, cada uno con el término
    (o términos) bajo el que se calculó.
"""

# PROCESO 0: Paquetes.
# json: lee el índice del libro y escribe los datos para la página.
import json
# math: logaritmo (peso IDF) y raíz cuadrada (norma del vector).
import math
# re: separa las palabras griegas.
import re
# sys: permite importar los módulos de esta carpeta.
import sys
# unicodedata: separa acentos y espíritus para comparar formas griegas.
import unicodedata
# collections: cuenta raíces y agrupa ecos.
from collections import Counter, defaultdict
# pathlib: rutas.
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# arete: reutiliza normalización, raíces, palabras vacías, remisiones, títulos y agrupación.
from arete import (GRUPOS, PALABRAS_VACIAS, TITULOS_ES, raiz, remisiones,  # noqa: E402
                   tokens)
# secciones: divide el corpus en secciones Stephanus alineadas griego-inglés.
from secciones import cargar_corpus  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "web" / "concordancia_datos.js"
LIBRO = RAIZ / "web" / "halfwassen_datos.js"

# Términos. Las formas se comparan sin acentos pero conservando el espíritu áspero («h»),
# para no confundir ἕν (uno) con la preposición ἐν (en).
TERMINOS = {
    "arete": {
        "griego": "ἀρετή", "glosa": "virtud",
        "formas": {"αρετη", "αρετησ", "αρετην", "αρεται", "αρετων", "αρεταισ", "αρετασ"},
        "ingles": r"\b(virtues?|virtuous|excellence|goodness)\b",
        "lentes": {
            "ensenanza": ("¿Se enseña?", ["διδακ", "διδασκ", "διδαχ", "μαθ", "μανθαν", "ασκ"], []),
            "saber": ("Saber y sabiduría", ["επιστημ", "φρονησ", "φρονιμ", "σοφι", "σοφο"], []),
            "partes": ("Unidad y partes", ["μορι"], ["ολον", "ολου", "ολω", "ολη", "ολην", "ολησ"]),
            "virtudes": ("Justicia, templanza, valentía, piedad",
                         ["δικαιοσυν", "σωφροσυν", "ανδρει", "οσιοτ"], []),
            "alma": ("Alma", ["ψυχ"], []),
            "placer": ("Placer y dolor", ["ηδον", "λυπ"], []),
            "naturaleza": ("Naturaleza o don divino", ["φυσει", "φυσισ", "φυσιν", "φυσεωσ", "θει", "μοιρ"], []),
            "ciudad": ("Ciudad, leyes y educación", ["πολιτ", "νομο", "παιδει", "παιδευ"], []),
            "felicidad": ("Felicidad", ["ευδαιμ"], []),
        },
    },
    "hen": {
        "griego": "ἕν", "glosa": "lo Uno",
        "formas": {"hεν", "hενοσ", "hενι"},
        "ingles": r"\b(the one|unity)\b",
        "lentes": {
            "ser": ("Ser y esencia", ["ουσι", "οντωσ"], ["ον", "οντοσ", "οντι", "οντα", "ειναι"]),
            "multiple": ("Uno y múltiple", ["πληθ"], ["πολλα", "πολλων", "πολλοισ"]),
            "partes": ("Todo y partes", ["μορι"], ["ολον", "ολου", "ολω", "ολη", "ολην", "ολησ"]),
            "limite": ("Límite e ilimitado", ["περασ", "περατ", "απειρ"], []),
            "mismo": ("Mismo y otro", ["ετερ"], ["ταυτον", "ταυτου", "ταυτω"]),
            "semejante": ("Semejante y desemejante", ["ομοι", "ανομοι"], []),
            "bien": ("El Bien", ["αγαθ"], []),
            "ideas": ("Ideas", [], ["ιδεα", "ιδεαν", "ιδεασ", "ιδεων", "ιδεαι", "ειδοσ", "ειδη", "ειδων"]),
        },
    },
    "nous": {
        "griego": "νοῦς", "glosa": "intelecto",
        "formas": {"νουσ", "νου", "νω", "νουν"},
        "ingles": r"\b(mind|intelligence|intellect|reason)\b",
        "lentes": {
            "alma": ("Alma", ["ψυχ"], []),
            "inteligible": ("Ideas e inteligible", ["νοητ"],
                            ["ιδεα", "ιδεαν", "ιδεασ", "ιδεων", "ιδεαι", "ειδοσ", "ειδη", "ειδων"]),
            "orden": ("Causa y orden", ["αιτι", "κοσμ", "ταξ", "τεταγ"], []),
            "bien": ("El Bien", ["αγαθ"], []),
            "divino": ("Lo divino", ["θει"], ["θεοσ", "θεου", "θεω", "θεον", "θεοι", "θεων", "θεοισ", "θεουσ"]),
            "saber": ("Saber y verdad", ["επιστημ", "φρονησ", "αληθ"], []),
            "devenir": ("Ser y devenir", ["ουσι", "οντωσ", "γενεσ"], []),
        },
    },
}
ORDEN_T = list(TERMINOS)


# PROCESO 1: Clave de comparación de una palabra griega.
# Antes: «ἕν», «ἐν», «ἀρετῆς». Después: «hεν», «εν», «αρετησ».
def clave(palabra: str) -> str:
    """Palabra griega → minúsculas sin acentos; antepone «h» si lleva espíritu áspero."""
    d = unicodedata.normalize("NFD", palabra.lower())
    h = "h" if "̔" in d else ""
    return h + "".join(ch for ch in d if not unicodedata.combining(ch)).replace("ς", "σ")


def claves(texto: str) -> list[str]:
    """Texto griego → claves de sus palabras (sin etiquetas de hablante)."""
    return [clave(w) for w in re.findall(r"[Ͱ-Ͽἀ-῿]+",
                                         re.sub(r"\[[^\]]*\]", " ", texto))]


def lentes_de(termino: str, toks: list[str]) -> list[str]:
    """Término + palabras normalizadas de la sección → lentes temáticas presentes."""
    presentes = []
    for k, (_, prefijos, exactas) in TERMINOS[termino]["lentes"].items():
        for t in toks:
            if t.startswith("σοφιστ"):
                continue
            if t in exactas or any(t.startswith(p) for p in prefijos):
                presentes.append(k)
                break
    return presentes


# PROCESO 2: Construir pasajes, lentes y puentes para cada término.
def construir() -> dict:
    """Corpus (+ índice del libro) → {terminos, obras, grupos, pasajes, puentes}."""
    corpus = cargar_corpus()
    ids = {n: {s["id"] for s in o["secciones"]} for n, o in corpus.items()}
    sec = {(n, s["id"]): s for n, o in corpus.items() for s in o["secciones"]}

    # 2a. Apariciones. Antes: 8553 secciones. Después: {(obra, sección): [k_arete, k_hen, k_nous]}.
    conteo, toks_de = {}, {}
    for llave, s in sec.items():
        cl = claves(s["griego"])
        toks_de[llave] = tokens(s["griego"])
        k = [sum(1 for c in cl if c in TERMINOS[t]["formas"]) for t in ORDEN_T]
        if any(k):
            conteo[llave] = k
    tiene = lambda llave, i: conteo.get(llave, [0, 0, 0])[i] > 0  # noqa: E731

    # 2b. Remisiones Loeb, etiquetadas con los términos presentes en alguno de sus extremos.
    puentes, vistos = [], set()
    for (n, sid), s in sec.items():
        for nota in s["notas"]:
            for destino in remisiones(nota, n, ids):
                if destino == (n, sid) or ("r", n, sid, *destino) in vistos:
                    continue
                ts = [t for i, t in enumerate(ORDEN_T) if tiene((n, sid), i) or tiene(destino, i)]
                if ts:
                    vistos.add(("r", n, sid, *destino))
                    puentes.append({"tipo": "remision", "t": ts, "de": f"{n}:{sid}",
                                    "a": f"{destino[0]}:{destino[1]}", "nota": nota})

    # 2c. Ecos de vocabulario por término (TF-IDF sobre raíces, entre diálogos distintos).
    excluir = {t.lstrip("h") for d in TERMINOS.values() for t in d["formas"]}
    df, raices_de = Counter(), {}
    for llave, t in toks_de.items():
        r = Counter(raiz(x) for x in t if x not in PALABRAS_VACIAS and len(x) > 3 and x not in excluir)
        raices_de[llave] = r
        df.update(r.keys())
    total = len(toks_de)
    idf = {r: math.log(total / c) for r, c in df.items()}
    vec = {}
    for llave in conteo:
        v = {r: (1 + math.log(c)) * idf[r] for r, c in raices_de[llave].items() if df[r] >= 2}
        norma = math.sqrt(sum(w * w for w in v.values())) or 1
        vec[llave] = {r: w / norma for r, w in v.items()}
    forma_de = {}
    for llave in conteo:
        for x in toks_de[llave]:
            forma_de.setdefault(raiz(x), x)
    for i, t in enumerate(ORDEN_T):
        claves_t = sorted(k for k in conteo if conteo[k][i])
        ecos = defaultdict(list)
        for a_i, a in enumerate(claves_t):
            va = vec[a]
            for b in claves_t[a_i + 1:]:
                if a[0] == b[0]:
                    continue
                vb = vec[b]
                comunes = va.keys() & vb.keys()
                if not comunes:
                    continue
                sim = sum(va[r] * vb[r] for r in comunes)
                if sim >= 0.10:
                    top = sorted(comunes, key=lambda r: va[r] * vb[r], reverse=True)[:5]
                    ecos[a].append((sim, b, top))
                    ecos[b].append((sim, a, top))
        pares = set()
        for a, lista in ecos.items():
            for sim, b, top in sorted(lista, reverse=True)[:3]:
                par = tuple(sorted([a, b]))
                if par in pares:
                    continue
                pares.add(par)
                puentes.append({"tipo": "eco", "t": [t], "de": f"{par[0][0]}:{par[0][1]}",
                                "a": f"{par[1][0]}:{par[1][1]}", "fuerza": round(sim, 3),
                                "palabras": [forma_de.get(r, r) for r in top]})

    # 2d. Pasajes que se envían: con algún término, extremos de puentes y citados por Halfwassen.
    necesarios = set(conteo)
    for p in puentes:
        for lado in (p["de"], p["a"]):
            n, sid = lado.split(":")
            necesarios.add((int(n), sid))
    if LIBRO.exists():
        libro = json.loads(LIBRO.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))
        for c in libro["citas"]:
            n, sid = c["s"].split(":")
            necesarios.add((int(n), sid))
    pasajes = {}
    for (n, sid) in sorted(necesarios):
        s = sec[(n, sid)]
        k = conteo.get((n, sid), [0, 0, 0])
        pasajes[f"{n}:{sid}"] = {
            "gr": s["griego"], "en": s["ingles"], "k": k,
            "l": {t: lentes_de(t, toks_de[(n, sid)]) for i, t in enumerate(ORDEN_T) if k[i]},
        }

    obras = [{"n": n, "es": TITULOS_ES[n], "en": o["titulo"],
              "secciones": [s["id"] for s in o["secciones"]],
              "k": [sum(v[i] for (m, _), v in conteo.items() if m == n) for i in range(len(ORDEN_T))]}
             for n, o in corpus.items()]
    terminos = {t: {"griego": d["griego"], "glosa": d["glosa"], "ingles": d["ingles"],
                    "formas": sorted(d["formas"]),
                    "lentes": {k: v[0] for k, v in d["lentes"].items()}} for t, d in TERMINOS.items()}
    return {"orden": ORDEN_T, "terminos": terminos, "obras": obras, "grupos": GRUPOS,
            "pasajes": pasajes, "puentes": puentes}


if __name__ == "__main__":
    datos = construir()
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text("window.DATOS = " + json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
                      + ";\n", encoding="utf-8")
    for i, t in enumerate(datos["orden"]):
        n_p = sum(1 for p in datos["pasajes"].values() if p["k"][i])
        n_r = sum(1 for p in datos["puentes"] if p["tipo"] == "remision" and t in p["t"])
        n_e = sum(1 for p in datos["puentes"] if p["tipo"] == "eco" and t in p["t"])
        print(f"{t}: {n_p} pasajes, {n_r} remisiones, {n_e} ecos")
    print(f"Pasajes enviados: {len(datos['pasajes'])} | {SALIDA.stat().st_size / 1e6:.2f} MB")
