"""Carga y valida config/estilo.yaml y config/calendario.yaml."""
import pathlib
import re
import unicodedata

import yaml

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
REDES = ["tiktok", "instagram", "youtube", "linkedin"]
TIPOS = ["luis", "app"]


class ConfigError(Exception):
    pass


def plegar(texto):
    """Minúsculas, sin tildes ni puntuación: así se comparan las palabras."""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w$\s]", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _leer(ruta):
    ruta = pathlib.Path(ruta)
    if not ruta.exists():
        raise ConfigError(f"No existe {ruta}")
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ConfigError(f"{ruta} no es un diccionario YAML")
    return datos


def _requerir(datos, claves, archivo):
    faltan = []
    for clave in claves:
        nodo = datos
        for parte in clave.split("."):
            if not isinstance(nodo, dict) or parte not in nodo:
                faltan.append(clave)
                break
            nodo = nodo[parte]
    if faltan:
        raise ConfigError(f"{archivo}: faltan las claves {', '.join(faltan)}")


def _color(valor, donde):
    if not isinstance(valor, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", valor):
        raise ConfigError(f"estilo.yaml: {donde} debe ser un color '#RRGGBB', no {valor!r}")


CLAVES_ESTILO = [
    "formato.ancho", "formato.alto", "formato.fps", "formato.duracion_ideal",
    "formato.duracion_maxima",
    "gancho.duracion", "gancho.palabras_min", "gancho.palabras_max", "gancho.mayusculas",
    "gancho.tamano", "gancho.color", "gancho.borde", "gancho.grosor_borde",
    "gancho.margen_superior", "gancho.saludos_a_recortar",
    "cortes.silencio_maximo", "cortes.pausa_que_queda", "cortes.umbral_silencio_db",
    "cortes.muletillas_siempre", "cortes.muletillas_en_pausa", "cortes.pausa_muletilla",
    "cortes.tomas_repetidas", "cortes.similitud_toma",
    "ritmo.cambio_cada", "ritmo.zooms",
    "subtitulos.fuente", "subtitulos.archivo_fuente", "subtitulos.modo",
    "subtitulos.palabras_por_frase", "subtitulos.tamano", "subtitulos.mayusculas",
    "subtitulos.color", "subtitulos.color_clave", "subtitulos.borde", "subtitulos.grosor_borde",
    "subtitulos.margen_inferior", "subtitulos.margen_izquierdo", "subtitulos.margen_derecho",
    "subtitulos.palabras_clave",
    "cierre.texto", "cierre.duracion", "cierre.tamano", "cierre.color", "cierre.fondo",
    "cierre.margen_superior",
    "musica.archivo", "musica.volumen_db", "audio.lufs",
    "transcripcion.proveedor", "transcripcion.modelo", "transcripcion.idioma",
    "transcripcion.prompt", "sugerencias.hashtags",
]


def cargar_estilo(ruta=RAIZ / "config/estilo.yaml"):
    e = _leer(ruta)
    _requerir(e, CLAVES_ESTILO, "estilo.yaml")
    for donde in ["gancho.color", "gancho.borde", "subtitulos.color", "subtitulos.color_clave",
                  "subtitulos.borde", "cierre.color", "cierre.fondo"]:
        seccion, clave = donde.split(".")
        _color(e[seccion][clave], donde)
    lo, hi = e["formato"]["duracion_ideal"]
    if not 0 < lo <= hi <= e["formato"]["duracion_maxima"]:
        raise ConfigError("estilo.yaml: duracion_ideal debe caber dentro de duracion_maxima")
    a, b = e["ritmo"]["cambio_cada"]
    if not 0 < a <= b:
        raise ConfigError("estilo.yaml: ritmo.cambio_cada debe ser [min, max]")
    if e["subtitulos"]["modo"] not in ("palabra", "frase"):
        raise ConfigError("estilo.yaml: subtitulos.modo es 'palabra' o 'frase'")
    if e["transcripcion"]["proveedor"] not in ("faster-whisper", "openai"):
        raise ConfigError("estilo.yaml: transcripcion.proveedor es 'faster-whisper' u 'openai'")
    return e


def menciona_prohibida(texto, prohibidas):
    """Devuelve la primera palabra prohibida que aparece en el texto, o None.

    Las palabras se comparan enteras, sin tildes ni mayúsculas; las entradas con
    punto (apps.apple.com) se buscan tal cual, como parte de un enlace.
    """
    plano = " " + plegar(texto) + " "
    for palabra in prohibidas:
        p = plegar(palabra)
        if "." in str(palabra) or p == "$":
            if str(palabra).lower() in texto.lower():
                return palabra
        elif f" {p} " in plano:
            return palabra
    return None


def cargar_calendario(ruta=RAIZ / "config/calendario.yaml"):
    c = _leer(ruta)
    _requerir(c, ["zona_horaria", "semana", "respaldo", "redes", "apps", "orden.luis",
                  "orden.app", "orden.app_max_dias", "buffer.organizacion",
                  "buffer.limite_cola_por_canal", "drive.carpeta_luis",
                  "drive.subcarpeta_editados", "drive.max_videos_por_corrida",
                  "url_publica.proveedor", "reglas_textos"], "calendario.yaml")
    if sorted(c["semana"]) != sorted(DIAS):
        raise ConfigError(f"calendario.yaml: 'semana' necesita los 7 días: {', '.join(DIAS)}")
    for dia, tipo in c["semana"].items():
        if tipo not in TIPOS:
            raise ConfigError(f"calendario.yaml: semana.{dia} es 'luis' o 'app', no {tipo!r}")
    for tipo, respaldos in c["respaldo"].items():
        if tipo not in TIPOS or any(r not in TIPOS for r in respaldos or []):
            raise ConfigError("calendario.yaml: 'respaldo' solo acepta los tipos luis y app")
    for red, conf in c["redes"].items():
        if red not in REDES:
            raise ConfigError(f"calendario.yaml: red desconocida {red!r}")
        _requerir(conf, ["destino", "dias", "tipos"], f"calendario.yaml redes.{red}")
        if conf["destino"] == "buffer" and not conf.get("canal_id"):
            raise ConfigError(f"calendario.yaml: redes.{red} sale por Buffer y le falta canal_id")
        if conf["destino"] == "youtube":
            _requerir(conf, ["hora_publicacion", "categoria"], f"calendario.yaml redes.{red}")
        if any(d not in DIAS for d in conf["dias"]):
            raise ConfigError(f"calendario.yaml: redes.{red}.dias tiene un día inválido")
        if red not in c["reglas_textos"]:
            raise ConfigError(f"calendario.yaml: faltan reglas_textos.{red}")
    for app in c["apps"]:
        _requerir(app, ["id", "nombre", "activa", "carpeta_drive", "cta", "prohibido"],
                  "calendario.yaml apps")
        palabra = menciona_prohibida(app["cta"], app["prohibido"])
        if palabra:
            raise ConfigError(f"calendario.yaml: el CTA de {app['nombre']} ({app['cta']!r}) "
                              f"menciona {palabra!r}")
    if c["url_publica"]["proveedor"] not in ("drive", "s3"):
        raise ConfigError("calendario.yaml: url_publica.proveedor es 'drive' o 's3'")
    return c


def color_ass(hex_color, alfa=0):
    """'#RRGGBB' -> '&HAABBGGRR' de ASS (alfa 0 = opaco)."""
    r, g, b = hex_color[1:3], hex_color[3:5], hex_color[5:7]
    return f"&H{alfa:02X}{b}{g}{r}".upper()
