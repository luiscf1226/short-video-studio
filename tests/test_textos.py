"""Validación de textos/semana-NN.json con las reglas definitivas."""
import datetime as dt
import json

from pipeline.calendario import Video
from pipeline.config import cargar_calendario, menciona_prohibida
from pipeline.textos import Texto, cargar, componer, indice_valido, sugerir, validar

REGLAS = cargar_calendario()["reglas_textos"]
APPS = cargar_calendario()["apps"]
PROHIBIDAS = APPS[0]["prohibido"]
TAGS3 = ["#ia", "#tecnologia", "#honduras"]


def errores(red, texto, hashtags, prohibidas=None):
    return validar(Texto("v1", red, texto, hashtags), REGLAS, prohibidas)


def test_tiktok_e_instagram_1_o_2_lineas_y_3_a_5_hashtags():
    for red in ("tiktok", "instagram"):
        assert errores(red, "Publico todos los días sin laptop.", TAGS3) == []
        assert errores(red, "Línea uno\nLínea dos", TAGS3 + ["#a", "#b"]) == []
        assert errores(red, "Uno\nDos\nTres", TAGS3)                      # 3 líneas
        assert errores(red, "Uno", ["#ia", "#x"])                         # 2 hashtags
        assert errores(red, "Uno", TAGS3 + ["#a", "#b", "#c"])            # 6 hashtags
        assert errores(red, "Uno #extra #otro #mas", TAGS3)               # 6 contando el texto


def test_shorts_titulo_de_menos_de_100():
    assert errores("youtube", "x" * 99, []) == []
    assert errores("youtube", "x" * 100, [])
    assert errores("youtube", "Título\nsegunda línea", [])
    assert errores("youtube", "Título <raro>", [])


def test_linkedin_3_a_5_lineas_y_0_a_3_hashtags():
    assert errores("linkedin", "Uno\nDos\nTres", []) == []
    assert errores("linkedin", "1\n2\n3\n4\n5", TAGS3) == []
    assert errores("linkedin", "Uno\nDos", [])
    assert errores("linkedin", "1\n2\n3\n4\n5\n6", [])
    assert errores("linkedin", "Uno\nDos\nTres", TAGS3 + ["#cuatro"])


def test_hashtags_invalidos_o_repetidos():
    assert errores("tiktok", "Uno", ["#ia", "#dos palabras", "#x"])
    assert errores("tiktok", "Uno", ["#ia", "#IA", "#x"])


def test_bible_ai_cta_y_sin_tiendas_enlaces_ni_precio():
    assert APPS[0]["id"] == "bible-ai" and APPS[0]["cta"] == "Descarga la app"
    assert menciona_prohibida("Descarga la app", PROHIBIDAS) is None
    assert menciona_prohibida("Descárgala en la Play Store", PROHIBIDAS) == "play store"
    assert menciona_prohibida("En la APP STORE", PROHIBIDAS) == "app store"
    assert menciona_prohibida("https://apps.apple.com/hn/app/3c", PROHIBIDAS) == "apps.apple.com"
    assert menciona_prohibida("play.google.com/store/apps", PROHIBIDAS) == "play.google.com"
    assert menciona_prohibida("Cuesta $2", PROHIBIDAS) == "cuesta"
    assert menciona_prohibida("Solo $2", PROHIBIDAS) == "$"
    assert menciona_prohibida("Es gratis", PROHIBIDAS) == "gratis"
    assert menciona_prohibida("Un versículo para hoy", PROHIBIDAS) is None
    assert errores("tiktok", "Bájala gratis hoy", TAGS3, PROHIBIDAS)


def test_texto_de_luis_que_nombra_bible_ai_tambien_se_valida():
    textos = {("luis-1", "tiktok"): Texto("luis-1", "tiktok", "Probé Bible AI, es gratis", TAGS3),
              ("luis-2", "tiktok"): Texto("luis-2", "tiktok", "Mi rutina con IA, es gratis",
                                          TAGS3)}
    videos = [Video("luis-1", "luis", dt.date(2026, 11, 1)),
              Video("luis-2", "luis", dt.date(2026, 11, 1))]
    validos, invalidos = indice_valido(textos, REGLAS, videos, APPS)
    assert set(validos) == {("luis-2", "tiktok")}
    assert set(invalidos) == {("luis-1", "tiktok")}


def test_carga_e_indice(tmp_path):
    (tmp_path / "semana-47.json").write_text(json.dumps([
        {"video": "V01-Skills.mp4", "red": "TikTok", "texto": "Hola", "hashtags": "ia tecno hn"},
        {"video": "bible-ai-s12-mar", "red": "reels", "texto": "Gratis en la tienda",
         "hashtags": TAGS3},
        {"video": "v01-skills", "red": "linkedin", "texto": "Solo una línea"},
        {"video": "x", "red": "facebook", "texto": "y"},
        {"red": "tiktok", "texto": "sin video"},
    ]), encoding="utf-8")
    (tmp_path / "_ejemplo.json").write_text("[]", encoding="utf-8")       # no se lee
    textos, errs = cargar(tmp_path)
    assert set(textos) == {("v01-skills", "tiktok"), ("bible-ai-s12-mar", "instagram"),
                           ("v01-skills", "linkedin")}
    assert textos[("v01-skills", "tiktok")].hashtags == ["#ia", "#tecno", "#hn"]
    assert len(errs) == 2
    videos = [Video("v01-skills", "luis", dt.date(2026, 11, 1)),
              Video("bible-ai-s12-mar", "app", dt.date(2026, 11, 1), "bible-ai")]
    validos, invalidos = indice_valido(textos, REGLAS, videos, APPS)
    assert set(validos) == {("v01-skills", "tiktok")}
    assert any("tiendas" in e for e in invalidos[("bible-ai-s12-mar", "instagram")])
    assert any("líneas" in e for e in invalidos[("v01-skills", "linkedin")])


def test_componer_por_red():
    assert componer(Texto("v", "tiktok", "Hola", TAGS3)) == {
        "texto": "Hola\n\n#ia #tecnologia #honduras"}
    assert componer(Texto("v", "linkedin", "a\nb\nc", [])) == {"texto": "a\nb\nc"}
    yt = componer(Texto("v", "youtube", "Mi título", ["#ia"]))
    assert yt == {"titulo": "Mi título", "descripcion": "#ia #Shorts"}


def test_sugerencias_cumplen_los_limites():
    frases = ["hoy les voy a enseñar cómo publicar todos los días sin depender de la laptop.",
              "el truco es que la nube edita por vos.", "corta los silencios."]
    tags = ["#ia", "#tecnologia", "#productividad", "#honduras"]
    for red in REGLAS:
        s = sugerir(red, frases, tags, "Sígueme para más")
        texto = Texto("v", red, s["texto"], s["hashtags"])
        assert validar(texto, REGLAS) == [], (red, s)
        assert ".." not in s["texto"] and s["texto"][0].isupper()
