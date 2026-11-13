"""Subtítulos, gancho y cierre en un solo archivo .ass que se quema en el video."""
import re

from ..config import color_ass, plegar

VACIAS = {
    "para", "pero", "como", "porque", "cuando", "donde", "desde", "hasta", "entre", "sobre",
    "todos", "todas", "estos", "estas", "esto", "este", "esta", "eso", "esos", "ellos",
    "ellas", "nosotros", "usted", "ustedes", "tiene", "tienen", "hacer", "puede", "pueden",
    "tambien", "entonces", "despues", "antes", "ahora", "mucho", "muchos", "algo", "cada",
    "mismo", "otra", "otro", "tanto", "porque", "aunque", "quiero", "vamos", "voy",
}


def tiempo(segundos):
    cs = int(round(max(0.0, segundos) * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _limpio(texto, mayusculas):
    texto = texto.replace("{", "(").replace("}", ")").replace("\\", "")
    texto = re.sub(r"[.,;:…]+$", "", texto)
    return texto.upper() if mayusculas else texto


def _clave(grupo, palabras_clave):
    """Índice de la palabra clave del grupo, o None."""
    plegadas = [plegar(w["text"]) for w in grupo]
    for i, p in enumerate(plegadas):
        if p in palabras_clave:
            return i
    candidatas = [(len(p), i) for i, p in enumerate(plegadas) if len(p) >= 5 and p not in VACIAS]
    return max(candidatas)[1] if candidatas else None


def _grupos(palabras, por_frase):
    grupos, actual = [], []
    for w in palabras:
        if actual and (len(actual) >= por_frase or w["start"] - actual[-1]["end"] > 0.5):
            grupos.append(actual)
            actual = []
        actual.append(w)
        if re.search(r"[.!?…]$", w["text"]):
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)
    return grupos


def generar(plan, estilo, duracion, ancho, alto):
    sub, gan, cie = estilo["subtitulos"], estilo["gancho"], estilo["cierre"]
    clave_color = color_ass(sub["color_clave"])
    blanco = color_ass(sub["color"])
    claves = {plegar(p) for p in sub["palabras_clave"]}
    estilos = [
        ("Sub", sub["fuente"], sub["tamano"], sub["color"], sub["borde"], 1, sub["grosor_borde"],
         2, sub["margen_izquierdo"], sub["margen_derecho"], sub["margen_inferior"]),
        ("Gancho", sub["fuente"], gan["tamano"], gan["color"], gan["borde"], 1,
         gan["grosor_borde"], 8, 80, 80, gan["margen_superior"]),
        ("Cierre", sub["fuente"], cie["tamano"], cie["color"], cie["fondo"], 3, 18, 8, 80, 80,
         cie["margen_superior"]),
    ]
    lineas = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {ancho}", f"PlayResY: {alto}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    ]
    for nombre, fuente, tam, color, borde, estilo_borde, grosor, alin, ml, mr, mv in estilos:
        lineas.append(
            f"Style: {nombre},{fuente},{tam},{color_ass(color)},&H000000FF,{color_ass(borde)},"
            f"&H64000000,0,0,0,0,100,100,0,0,{estilo_borde},{grosor},2,{alin},{ml},{mr},{mv},1")
    lineas += ["", "[Events]",
               "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]

    por_frase = 1 if sub["modo"] == "palabra" else sub["palabras_por_frase"]
    grupos = _grupos(plan.palabras, por_frase)
    for n, grupo in enumerate(grupos):
        inicio = grupo[0]["start"]
        fin = grupo[-1]["end"] + 0.1
        if n + 1 < len(grupos):
            siguiente = grupos[n + 1][0]["start"]
            fin = siguiente if siguiente - fin < 0.3 else fin
        fin = min(fin, duracion)
        k = _clave(grupo, claves)
        partes = []
        for i, w in enumerate(grupo):
            t = _limpio(w["text"], sub["mayusculas"])
            partes.append(f"{{\\c{clave_color}&}}{t}{{\\c{blanco}&}}" if i == k else t)
        pop = r"{\fscx94\fscy94\t(0,80,\fscx100\fscy100)}"
        lineas.append(f"Dialogue: 0,{tiempo(inicio)},{tiempo(fin)},Sub,,0,0,0,,{pop}"
                      + " ".join(partes))

    if plan.gancho:
        fin_gancho = min(max(gan["duracion"], plan.gancho_fin + 0.2), gan["duracion"] + 2.0)
        lineas.append(f"Dialogue: 1,{tiempo(0)},{tiempo(fin_gancho)},Gancho,,0,0,0,,"
                      r"{\fad(0,150)}" + plan.gancho.replace("{", "(").replace("}", ")"))
    if cie["texto"]:
        texto = cie["texto"].upper() if sub["mayusculas"] else cie["texto"]
        lineas.append(f"Dialogue: 1,{tiempo(max(0.0, duracion - cie['duracion']))},"
                      f"{tiempo(duracion)},Cierre,,0,0,0,,{{\\fad(200,0)}}{texto}")
    return "\n".join(lineas) + "\n"
