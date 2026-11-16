"""Concordancia de ἀρετή en el corpus platónico y puentes entre diálogos.

Uso (desde la raíz del repositorio):
    python scripts/arete.py

Insumo: datos/perseus/ (vía secciones.py).
Resultado: web/arete_datos.js con
  - obras: las 36 obras con su lista de secciones Stephanus (para dibujar los carruseles);
  - pasajes: cada sección con ἀρetή (y cada sección destino de una remisión), con griego,
    inglés, número de apariciones y lentes temáticas;
  - puentes: remisiones de las notas Loeb (hechas por especialistas) y ecos de vocabulario
    (calculados), cada uno con su explicación.
"""

# PROCESO 0: Paquetes.
# json: escribe los datos para la página web.
import json
# math: logaritmo para el peso IDF y raíz para la similitud coseno.
import math
# re: tokeniza el griego y lee las referencias de las notas.
import re
# sys: permite importar secciones.py desde esta misma carpeta.
import sys
# unicodedata: quita acentos y espíritus para comparar formas griegas.
import unicodedata
# collections: cuenta palabras y agrupa resultados.
from collections import Counter, defaultdict
# pathlib: rutas de salida.
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# secciones: divide el corpus en secciones Stephanus alineadas griego-inglés.
from secciones import cargar_corpus  # noqa: E402

SALIDA = Path(__file__).resolve().parent.parent / "web" / "arete_datos.js"

# Títulos en español y agrupación cronológica convencional (aproximada y discutida).
TITULOS_ES = {
    1: "Eutifrón", 2: "Apología", 3: "Critón", 4: "Fedón", 5: "Crátilo", 6: "Teeteto",
    7: "Sofista", 8: "Político", 9: "Parménides", 10: "Filebo", 11: "Banquete", 12: "Fedro",
    13: "Alcibíades I", 14: "Alcibíades II", 15: "Hiparco", 16: "Los rivales", 17: "Teages",
    18: "Cármides", 19: "Laques", 20: "Lisis", 21: "Eutidemo", 22: "Protágoras", 23: "Gorgias",
    24: "Menón", 25: "Hipias mayor", 26: "Hipias menor", 27: "Ion", 28: "Menéxeno",
    29: "Clitofonte", 30: "República", 31: "Timeo", 32: "Critias", 33: "Minos", 34: "Leyes",
    35: "Epínomis", 36: "Cartas",
}
GRUPOS = {
    "Tempranos": [2, 3, 1, 18, 19, 20, 26, 27, 22, 21, 23, 25, 28, 24],
    "Medios": [4, 11, 30, 12, 5, 9, 6],
    "Tardíos": [7, 8, 10, 31, 32, 34],
    "Autoría discutida": [13, 14, 15, 16, 17, 29, 33, 35, 36],
}

# Lentes temáticas: raíces griegas (sin acentos) que acompañan a ἀρετή en la misma sección.
LENTES = {
    "ensenanza": ("¿Se enseña?", ["διδακ", "διδασκ", "διδαχ", "μαθ", "μανθαν", "ασκ"]),
    "saber": ("Saber y sabiduría", ["επιστημ", "φρονησ", "φρονιμ", "σοφι", "σοφο"]),
    "partes": ("Unidad y partes", ["μορι", "ολον", "ολου", "ολω", "ολη", "ολην", "ολησ"]),
    "virtudes": ("Justicia, templanza, valentía, piedad",
                 ["δικαιοσυν", "σωφροσυν", "ανδρει", "οσιοτ"]),
    "alma": ("Alma", ["ψυχ"]),
    "placer": ("Placer y dolor", ["ηδον", "λυπ"]),
    "naturaleza": ("Naturaleza o don divino", ["φυσει", "φυσισ", "φυσιν", "φυσεωσ", "θει", "μοιρ"]),
    "ciudad": ("Ciudad, leyes y educación", ["πολιτ", "νομο", "παιδει", "παιδευ"]),
    "felicidad": ("Felicidad", ["ευδαιμ"]),
}
EXACTAS = {"ολον", "ολου", "ολω", "ολη", "ολην", "ολησ"}

PALABRAS_VACIAS = set("""
και δε ο η το του τησ τω τη τον την οι αι τα των τοισ ταισ τουσ τασ γαρ μεν ουν αν εαν
εν εισ εσ εκ εξ προσ περι κατα κατ καθ μετα μετ μεθ δια δι υπο υπ υφ απο απ αφ επι επ εφ παρα παρ
αλλα αλλ ουκ ου ουχ μη ωσ ει οτι τι τισ τινα τινοσ τινι τινεσ τινων γε δη τε ουτε μητε ηδη
αυτοσ αυτου αυτω αυτον αυτη αυτην αυτησ αυτο αυτα αυτων αυτοισ αυτουσ ουτοσ τουτο τουτου τουτω
ταυτα ταυτην ταυτησ ταυτη τουτων τουτοισ τουτον αυτη εκεινοσ εκεινο εκεινου εκεινα εγω εμοι μοι με
εμε εμου μου συ σοι σε σου ημεισ ημιν ημασ ημων υμεισ υμιν υμασ υμων εστιν εστι ειναι ην ειη
ων ουσα ον οντα οντοσ οντων εφη φησι φημι ναι πανυ πωσ πολυ ουδε ουδεν μηδεν μηδε παντα πασ πασα
παν παντων πασι ετι νυν αρα αρ ω σωκρατεσ ωσπερ ουτωσ ουτω πωσ που οσ οσα ουσ ων οισ ην ησ
ειπερ επειδη επει τοινυν μαλα μαλιστα μαλλον αλλο αλλοσ αλλων αλλα αλλη αλλην αλλου αλλοισ
δοκει δοκεισ δοκω εοικεν δηλον ποτε τοτε ενθαδε ουδαμωσ γουν τοι μην που πη οιμαι εγωγε
εχει εχειν εστε εσμεν εισιν εσται εσονται γιγνεται γενεσθαι λεγω λεγεισ λεγει λεγεισ λεγειν
""".split())

ENDINGS = sorted("""
ομενοισ ομενουσ ομενων ομενη ομενοσ ομενον ουσιν ουσαι ουσα οντων οντεσ οντασ οντοσ οντι
εσθαι ασθαι ουσθαι ειαν εωσ εων ουσ οισ αισ ησ ην ηι ων ου οσ ον οι αι ασ εσ ει ειν
ιν ισ ια ιαν ιασ ιοσ ιον ιω η α ω ε ο υσ υν
""".split(), key=len, reverse=True)


# PROCESO 1: Normalizar y tokenizar el griego.
# Antes: «ἆρα διδακτὸν ἡ ἀρετή;». Después: ["αρα", "διδακτον", "η", "αρετη"].
def normalizar(texto: str) -> str:
    """Texto griego → minúsculas sin acentos ni espíritus, sigma final unificada."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return t.replace("ς", "σ")


def tokens(texto: str) -> list[str]:
    """Texto griego → lista de palabras normalizadas (sin etiquetas de hablante)."""
    return re.findall(r"[α-ω]+", normalizar(re.sub(r"\[[^\]]*\]", " ", texto)))


def raiz(tok: str) -> str:
    """Palabra normalizada → raíz aproximada (quita una terminación y corta a 7 letras)."""
    for e in ENDINGS:
        if tok.endswith(e) and len(tok) - len(e) >= 4:
            tok = tok[: -len(e)]
            break
    return tok[:7]


def es_arete(tok: str) -> bool:
    """Palabra normalizada → ¿es una forma del sustantivo ἀρετή?"""
    return tok in {"αρετη", "αρετησ", "αρετην", "αρεται", "αρετων", "αρεταισ", "αρετασ"}


def lentes_de(toks: list[str]) -> list[str]:
    """Palabras de una sección → claves de las lentes temáticas presentes."""
    presentes = []
    for clave, (_, raices) in LENTES.items():
        for t in toks:
            if t.startswith("σοφιστ"):
                continue
            if any((t == r) if r in EXACTAS else t.startswith(r) for r in raices):
                presentes.append(clave)
                break
    return presentes


# PROCESO 2: Leer las remisiones de las notas Loeb.
# Antes: «Cf. Meno 71 B, 86 D-E, Laches 190 B». Después: [(24,"71b"), (24,"86d"), (19,"190b")].
NOMBRES = {
    "Euthyphro": 1, "Euthyph.": 1, "Apology": 2, "Apol.": 2, "Crito": 3, "Phaedo": 4,
    "Cratylus": 5, "Cratyl.": 5, "Crat.": 5, "Theaetetus": 6, "Theaet.": 6, "Sophist": 7,
    "Soph.": 7, "Statesman": 8, "Politicus": 8, "Polit.": 8, "Parmenides": 9, "Parm.": 9,
    "Philebus": 10, "Phileb.": 10, "Symposium": 11, "Symp.": 11, "Sympos.": 11, "Phaedrus": 12,
    "Phaedr.": 12, "Alcibiades I": 13, "Alc. I.": 13, "Alc. I": 13, "Alcib. I": 13,
    "Alcibiades II": 14, "Alc. II.": 14, "Alc. II": 14, "Hipparchus": 15, "Theages": 17,
    "Charmides": 18, "Charm.": 18, "Laches": 19, "Lach.": 19, "Lysis": 20, "Euthydemus": 21,
    "Euthyd.": 21, "Protagoras": 22, "Protag.": 22, "Prot.": 22, "Gorgias": 23, "Gorg.": 23,
    "Meno": 24, "Hippias Major": 25, "Hipp. Maj.": 25, "Greater Hippias": 25,
    "Hippias Minor": 26, "Hipp. Min.": 26, "Lesser Hippias": 26, "Ion": 27, "Menexenus": 28,
    "Menex.": 28, "Cleitophon": 29, "Clitophon": 29, "Republic": 30, "Rep.": 30,
    "Timaeus": 31, "Tim.": 31, "Critias": 32, "Minos": 33, "Laws": 34, "Epinomis": 35,
    "Epin.": 35, "Letters": 36, "Epist.": 36,
}
_NOMBRE_RE = "|".join(re.escape(k) for k in sorted(NOMBRES, key=len, reverse=True))
REF = r"(\d{1,3})\s?([A-E])?(?:\s?[-–]\s?(?:\d{1,3}\s?)?[A-E]?)?(?:\s?ff?\.)?"
RE_CON_NOMBRE = re.compile(rf"^(?:.*?\b)?({_NOMBRE_RE})\s+{REF}\s*\.?$")
RE_SOLO_REF = re.compile(rf"^(?:cf\.?|cp\.?|on|also|and|see|so|e\.g\.)?\s*{REF}\s*\.?$", re.I)
RE_OTRA_OBRA = re.compile(r"[A-Z][a-z]+\.?\s+(?:[ivxl]+\.\s*)?\d")


def resolver(obra: int, pagina: str, letra: str | None, ids: dict[int, set]) -> str | None:
    """Obra + página + letra → id de sección existente (o None si no existe)."""
    sec = f"{pagina}{(letra or 'a').lower()}"
    if sec in ids[obra]:
        return sec
    candidatas = sorted(s for s in ids[obra] if re.fullmatch(rf"{pagina}[a-e]", s))
    return candidatas[0] if candidatas else None


def remisiones(nota: str, obra_origen: int, ids: dict[int, set]) -> list[tuple[int, str]]:
    """Texto de una nota → [(obra, sección)] de pasajes platónicos citados."""
    actual = obra_origen
    salida = []
    for trozo in re.split(r"[,;]|\band\b", nota):
        trozo = trozo.strip()
        if not trozo:
            continue
        m = RE_CON_NOMBRE.match(trozo)
        if m:
            actual = NOMBRES[m.group(1)]
            sec = resolver(actual, m.group(2), m.group(3), ids)
        elif (m := RE_SOLO_REF.match(trozo)) and actual:
            sec = resolver(actual, m.group(1), m.group(2), ids)
        else:
            if RE_OTRA_OBRA.search(trozo) or re.search(r"[A-Z][a-z]{2,}", trozo):
                actual = None   # se pasó a otro autor u obra: los números que siguen no son de Platón
            continue
        if sec:
            salida.append((actual, sec))
    return salida


# PROCESO 3: Armar pasajes, lentes y puentes.
def construir() -> dict:
    """Corpus → {obras, grupos, lentes, pasajes, puentes}."""
    corpus = cargar_corpus()
    ids = {n: {s["id"] for s in o["secciones"]} for n, o in corpus.items()}
    sec_por_clave = {(n, s["id"]): s for n, o in corpus.items() for s in o["secciones"]}

    # 3a. Pasajes con ἀρετή. Antes: 8553 secciones. Después: las que contienen ἀρετή.
    toks_de, conteo = {}, {}
    for clave, s in sec_por_clave.items():
        t = tokens(s["griego"])
        toks_de[clave] = t
        k = sum(1 for x in t if es_arete(x))
        if k:
            conteo[clave] = k

    # 3b. Remisiones Loeb. Antes: notas sueltas. Después: puentes con la nota como explicación;
    # se guardan si el origen o el destino contiene ἀρετή.
    puentes = []
    vistos = set()
    for (n, sid), s in sec_por_clave.items():
        for nota in s["notas"]:
            for destino in remisiones(nota, n, ids):
                if destino == (n, sid):
                    continue
                if (n, sid) not in conteo and destino not in conteo:
                    continue
                llave = ("remision", n, sid, *destino)
                if llave in vistos:
                    continue
                vistos.add(llave)
                puentes.append({"tipo": "remision", "de": f"{n}:{sid}",
                                "a": f"{destino[0]}:{destino[1]}", "nota": nota})

    # 3c. Ecos de vocabulario entre pasajes con ἀρετή de diálogos distintos.
    # Antes: palabras de cada sección. Después: similitud coseno TF-IDF entre raíces,
    # con las raíces compartidas de mayor peso como explicación.
    df = Counter()
    raices_de = {}
    for clave, t in toks_de.items():
        r = [raiz(x) for x in t if x not in PALABRAS_VACIAS and len(x) > 3 and not es_arete(x)]
        raices_de[clave] = Counter(r)
        df.update(set(r))
    total = len(toks_de)
    idf = {r: math.log(total / c) for r, c in df.items()}
    forma_de = {}
    for clave in conteo:
        for x in toks_de[clave]:
            forma_de.setdefault(raiz(x), x)
    vec = {}
    for clave in conteo:
        v = {r: (1 + math.log(c)) * idf[r] for r, c in raices_de[clave].items() if df[r] >= 2}
        norma = math.sqrt(sum(w * w for w in v.values())) or 1
        vec[clave] = {r: w / norma for r, w in v.items()}
    claves = sorted(conteo)
    ecos_por = defaultdict(list)
    for i, a in enumerate(claves):
        for b in claves[i + 1:]:
            if a[0] == b[0]:
                continue
            va, vb = vec[a], vec[b]
            comunes = set(va) & set(vb)
            if not comunes:
                continue
            sim = sum(va[r] * vb[r] for r in comunes)
            if sim >= 0.10:
                top = sorted(comunes, key=lambda r: va[r] * vb[r], reverse=True)[:5]
                ecos_por[a].append((sim, b, top))
                ecos_por[b].append((sim, a, top))
    vistos = set()
    for a, lista in ecos_por.items():
        for sim, b, top in sorted(lista, reverse=True)[:3]:
            par = tuple(sorted([a, b]))
            if par in vistos:
                continue
            vistos.add(par)
            puentes.append({"tipo": "eco", "de": f"{par[0][0]}:{par[0][1]}",
                            "a": f"{par[1][0]}:{par[1][1]}", "fuerza": round(sim, 3),
                            "palabras": [forma_de.get(r, r) for r in top]})

    # 3d. Pasajes que se envían a la página: los que tienen ἀρετή y los destinos de remisiones.
    necesarios = set(conteo)
    for p in puentes:
        for lado in (p["de"], p["a"]):
            n, sid = lado.split(":")
            necesarios.add((int(n), sid))
    pasajes = {}
    for (n, sid) in sorted(necesarios):
        s = sec_por_clave[(n, sid)]
        pasajes[f"{n}:{sid}"] = {
            "gr": s["griego"], "en": s["ingles"], "k": conteo.get((n, sid), 0),
            "lentes": lentes_de(toks_de[(n, sid)]) if (n, sid) in conteo else [],
        }

    obras = [{"n": n, "es": TITULOS_ES[n], "en": o["titulo"],
              "secciones": [s["id"] for s in o["secciones"]],
              "k": sum(v for (m, _), v in conteo.items() if m == n)} for n, o in corpus.items()]
    return {"obras": obras, "grupos": GRUPOS,
            "lentes": {k: v[0] for k, v in LENTES.items()},
            "pasajes": pasajes, "puentes": puentes}


if __name__ == "__main__":
    datos = construir()
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text("window.DATOS = " + json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
                      + ";\n", encoding="utf-8")
    tipos = Counter(p["tipo"] for p in datos["puentes"])
    con_arete = sum(1 for p in datos["pasajes"].values() if p["k"])
    print(f"Pasajes con ἀρετή: {con_arete} | pasajes enviados: {len(datos['pasajes'])} | "
          f"puentes: {dict(tipos)} | {SALIDA.stat().st_size / 1e6:.2f} MB")
