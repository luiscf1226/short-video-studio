"""Textos de las publicaciones: textos/semana-NN.json, que llena Marca.

Cada entrada es {"video", "red", "texto", "hashtags"}. Un video sin texto
válido para una red no se programa en esa red; el texto generado aquí
(`sugerir`) solo sale como sugerencia en el resumen de la corrida.
"""
import json
import pathlib
import re
from dataclasses import dataclass, field

from .config import menciona_prohibida, plegar

ALIAS_RED = {
    "tiktok": "tiktok",
    "instagram": "instagram", "ig": "instagram", "reels": "instagram",
    "youtube": "youtube", "shorts": "youtube", "yt": "youtube",
    "linkedin": "linkedin",
}
HASHTAG = re.compile(r"^#[^\s#]+$")
HASHTAG_EN_TEXTO = re.compile(r"(?<![\w#])#[^\s#]+")


@dataclass
class Texto:
    video: str
    red: str
    texto: str
    hashtags: list = field(default_factory=list)
    archivo: str = ""


def id_video(nombre):
    """El id con el que Marca nombra un video: el nombre del archivo sin extensión."""
    nombre = str(nombre).strip()
    nombre = re.sub(r"\.(mp4|mov|m4v|webm|mkv)$", "", nombre, flags=re.I)
    return nombre.lower()


def normalizar_hashtags(hashtags):
    salida = []
    for h in hashtags or []:
        h = str(h).strip()
        if h and not h.startswith("#"):
            h = "#" + h
        if h:
            salida.append(h)
    return salida


def cargar(carpeta):
    """Lee textos/semana-*.json. Devuelve ({(video, red): Texto}, [errores])."""
    carpeta = pathlib.Path(carpeta)
    textos, errores = {}, []
    archivos = sorted(carpeta.glob("semana-*.json"))
    for archivo in archivos:
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errores.append(f"{archivo.name}: JSON inválido ({exc})")
            continue
        entradas = datos.get("publicaciones", []) if isinstance(datos, dict) else datos
        if not isinstance(entradas, list):
            errores.append(f"{archivo.name}: se esperaba una lista de publicaciones")
            continue
        for i, entrada in enumerate(entradas, 1):
            donde = f"{archivo.name} #{i}"
            if not isinstance(entrada, dict):
                errores.append(f"{donde}: no es un objeto")
                continue
            faltan = [k for k in ("video", "red", "texto") if not entrada.get(k)]
            if faltan:
                errores.append(f"{donde}: faltan {', '.join(faltan)}")
                continue
            red = ALIAS_RED.get(str(entrada["red"]).strip().lower())
            if not red:
                errores.append(f"{donde}: red desconocida {entrada['red']!r}")
                continue
            hashtags = entrada.get("hashtags") or []
            if isinstance(hashtags, str):
                hashtags = hashtags.split()
            texto = Texto(id_video(entrada["video"]), red, str(entrada["texto"]).strip(),
                          normalizar_hashtags(hashtags), archivo.name)
            clave = (texto.video, red)
            if clave in textos:
                errores.append(f"{donde}: {texto.video}/{red} ya estaba en "
                               f"{textos[clave].archivo}; se usa este")
            textos[clave] = texto
    return textos, errores


def lineas(texto):
    return [l for l in texto.splitlines() if l.strip()]


def validar(texto, reglas, prohibidas=None):
    """Errores del texto según las reglas de su red. Lista vacía = válido."""
    errores = []
    regla = reglas[texto.red]
    n_lineas = len(lineas(texto.texto))
    lo, hi = regla["lineas"]
    if not lo <= n_lineas <= hi:
        errores.append(f"{texto.red}: {n_lineas} líneas, deben ser de {lo} a {hi}")
    if "max_caracteres" in regla and len(texto.texto) > regla["max_caracteres"]:
        errores.append(f"{texto.red}: {len(texto.texto)} caracteres, el máximo es "
                       f"{regla['max_caracteres']}")
    if texto.red == "youtube" and re.search(r"[<>]", texto.texto):
        errores.append("youtube: el título no puede llevar < ni >")
    malos = [h for h in texto.hashtags if not HASHTAG.match(h)]
    if malos:
        errores.append(f"{texto.red}: hashtags inválidos {malos}")
    total = len(texto.hashtags) + len(HASHTAG_EN_TEXTO.findall(texto.texto))
    lo, hi = regla["hashtags"]
    if not lo <= total <= hi:
        errores.append(f"{texto.red}: {total} hashtags, deben ser de {lo} a {hi}")
    if len({plegar(h) for h in texto.hashtags}) != len(texto.hashtags):
        errores.append(f"{texto.red}: hashtags repetidos")
    if prohibidas:
        palabra = menciona_prohibida(texto.texto + " " + " ".join(texto.hashtags), prohibidas)
        if palabra:
            errores.append(f"{texto.red}: menciona {palabra!r}, y en los videos de apps no "
                           "se nombran tiendas, sus enlaces ni precio")
    return errores


def prohibidas_para(video, texto, apps):
    """Lo prohibido de la app del video y de cada app que el texto nombre."""
    plano = " " + plegar(texto.texto + " " + " ".join(texto.hashtags)) + " "
    salida = []
    for app in apps:
        nombre = plegar(app["nombre"])
        if getattr(video, "app", None) == app["id"] or f" {nombre} " in plano \
                or f"#{nombre.replace(' ', '')}" in plano.replace(" #", "#"):
            salida += app["prohibido"]
    return salida


def indice_valido(textos, reglas, videos, apps):
    """{(video, red): Texto} solo con los textos válidos, y {(video, red): errores}."""
    por_id = {v.id: v for v in videos}
    validos, invalidos = {}, {}
    for clave, texto in textos.items():
        video = por_id.get(texto.video)
        errores = validar(texto, reglas, prohibidas_para(video, texto, apps))
        if errores:
            invalidos[clave] = errores
        else:
            validos[clave] = texto
    return validos, invalidos


def componer(texto):
    """Lo que se manda a cada red."""
    tags = " ".join(texto.hashtags)
    if texto.red == "youtube":
        # #Shorts va en la descripción: así el título queda como lo escribió Marca.
        descripcion = tags if "#shorts" in tags.lower() else f"{tags} #Shorts".strip()
        return {"titulo": texto.texto.strip(), "descripcion": descripcion}
    cuerpo = texto.texto.strip()
    return {"texto": f"{cuerpo}\n\n{tags}" if tags else cuerpo}


def _oracion(texto):
    texto = texto.strip()
    if not texto:
        return texto
    texto = texto[0].upper() + texto[1:]
    return texto if texto[-1] in ".!?…" else texto + "."


def sugerir(red, frases, hashtags, cierre):
    """Texto automático a partir de lo que dijo Luis: solo sugerencia, nunca se publica."""
    frases = [_oracion(f) for f in frases if f.strip()] or [""]
    primera = frases[0]
    if red == "youtube":
        titulo = primera.rstrip(".")
        if len(titulo) > 99:
            titulo = titulo[:98].rsplit(" ", 1)[0] + "…"
        return {"texto": titulo, "hashtags": hashtags[:3]}
    if red == "linkedin":
        cuerpo = frases[:4]
        while len(cuerpo) < 3:
            cuerpo.append(_oracion(cierre))
        return {"texto": "\n".join(cuerpo), "hashtags": hashtags[:2]}
    return {"texto": f"{primera}\n{_oracion(cierre)}", "hashtags": hashtags[:4]}
