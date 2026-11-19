"""Videos de redes-media: un repo git local hace de redes-media, sin red."""
import datetime as dt
import json
import os
import subprocess
from zoneinfo import ZoneInfo

from pipeline import __main__ as principal
from pipeline import redes_media
from pipeline.calendario import Video, planear_dia
from pipeline.config import cargar_calendario

CAL = cargar_calendario()
TZ = ZoneInfo(CAL["zona_horaria"])


def _commit(repo, archivos, fecha):
    for nombre, contenido in archivos.items():
        ruta = repo / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)
    env = {**os.environ, "GIT_AUTHOR_DATE": fecha, "GIT_COMMITTER_DATE": fecha,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-qm", "videos"], check=True, env=env)


def _repo(tmp_path):
    repo = tmp_path / "redes-media"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    _commit(repo, {"videos/rumbo.mp4": b"a", "videos/gta6-tegus.mp4": b"b",
                   "videos/LEEME.txt": b"c", "videos/Mundo Catrucho ñ.mp4": b"f",
                   "gta6/v1.mp4": b"d"}, "2026-11-18T22:00:00-06:00")
    _commit(repo, {"videos/Tuerce-Coop.MP4": b"e"}, "2026-11-19T03:30:00+00:00")
    return repo


def test_lista_los_mp4_de_la_carpeta_sin_los_excluidos(tmp_path):
    videos = redes_media.listar(CAL["redes_media"], TZ, origen=str(_repo(tmp_path)))
    assert videos == [
        Video("mundo catrucho ñ", "app", dt.date(2026, 11, 18), "redes-media",
              "https://raw.githubusercontent.com/luiscf1226/redes-media/main/videos/"
              "Mundo%20Catrucho%20%C3%B1.mp4"),
        Video("rumbo", "app", dt.date(2026, 11, 18), "redes-media",
              "https://raw.githubusercontent.com/luiscf1226/redes-media/main/videos/rumbo.mp4"),
        # 03:30 UTC del 19 son las 21:30 del 18 en Honduras.
        Video("tuerce-coop", "app", dt.date(2026, 11, 18), "redes-media",
              "https://raw.githubusercontent.com/luiscf1226/redes-media/main/videos/"
              "Tuerce-Coop.MP4"),
    ]


def test_un_video_de_redes_media_con_texto_se_programa_y_sin_texto_no():
    rumbo = Video("rumbo", "app", dt.date(2026, 11, 18), "redes-media", "https://x/rumbo.mp4")
    viernes = dt.date(2026, 11, 20)  # día de Luis: sale de respaldo
    asignaciones, omisiones = planear_dia(CAL, viernes, [rumbo], {},
                                          lambda vid, red: red == "tiktok")
    assert [(a.red, a.video.id, a.respaldo) for a in asignaciones] == [("tiktok", "rumbo", True)]
    assert {o.red for o in omisiones} == {"instagram", "youtube", "linkedin"}


def test_el_dry_run_toma_redes_media_sin_llaves(tmp_path, monkeypatch):
    for nombre in ("GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_OAUTH_CLIENT_ID", "BUFFER_API_KEY"):
        monkeypatch.delenv(nombre, raising=False)
    repo = _repo(tmp_path)
    listar = redes_media.listar
    monkeypatch.setattr(redes_media, "listar", lambda conf, tz: listar(conf, tz, origen=str(repo)))
    monkeypatch.setattr(principal.google, "verificar_url_publica", lambda url: None)
    textos = tmp_path / "textos"
    textos.mkdir()
    (textos / "semana-47.json").write_text(
        '[{"video": "rumbo", "red": "tiktok", "texto": "Rumbo, la app de viajes por Honduras.",'
        ' "hashtags": ["#honduras", "#viajes", "#app"]},'
        ' {"video": "viejo", "red": "tiktok", "texto": "Uno viejo de Drive.",'
        ' "hashtags": ["#honduras", "#viajes", "#app"]}]', encoding="utf-8")
    # Un video de Drive que quedó en el estado no entra con fuente redes_media.
    estado = tmp_path / "estado.json"
    estado.write_text(json.dumps({"apps": {"d1": {
        "id": "viejo", "app": "redes-media", "disponible": "2026-11-18", "url": "https://x"}}}))
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{no es json")  # no se usa
    salida = tmp_path / "resumen.md"
    codigo = principal.main(["correr", "--modo", "dry_run", "--fecha", "2026-11-20",
                             "--estado", str(estado), "--trabajo", str(tmp_path / "trabajo"),
                             "--textos", str(textos), "--resumen", str(salida)])
    resumen = salida.read_text(encoding="utf-8")
    assert codigo == 0, resumen
    assert "redes-media: 3 videos" in resumen and "ñ, rumbo, tuerce-coop" in resumen
    assert "gta6-tegus" not in resumen
    assert "programaría tiktok: rumbo (app, respaldo) vía buffer" in resumen
    assert "viejo" not in resumen
    assert json.loads(estado.read_text())["apps"]["d1"]["id"] == "viejo"  # sin tocar
