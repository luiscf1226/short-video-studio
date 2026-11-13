"""Reglas del calendario con config/calendario.yaml tal cual (los valores definitivos)."""
import datetime as dt

import pytest

from pipeline.calendario import Video, dia_semana, planear_dia, proyectar
from pipeline.config import cargar_calendario

CAL = cargar_calendario()
LUNES = dt.date(2026, 11, 16)          # lunes
SEMANA = [LUNES + dt.timedelta(days=i) for i in range(7)]
BUFFER_Y_YT = {"tiktok", "instagram", "youtube"}


def luis(n, dias_antes=3):
    return Video(f"luis-{n}", "luis", LUNES - dt.timedelta(days=dias_antes))


def app(n, dias_antes=2, nombre="bible-ai"):
    return Video(f"app-{n}", "app", LUNES - dt.timedelta(days=dias_antes), nombre)


def con_texto(*_):
    return True


def por_red(asignaciones):
    return {a.red: a.video.id for a in asignaciones}


def test_config_definitiva():
    assert [dia_semana(f) for f in SEMANA] == ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
    assert CAL["semana"] == {"lun": "luis", "mar": "app", "mie": "luis", "jue": "app",
                             "vie": "luis", "sab": "app", "dom": "app"}
    assert CAL["redes"]["linkedin"]["dias"] == ["lun", "mie", "vie"]
    assert CAL["redes"]["linkedin"]["tipos"] == ["luis"]
    assert CAL["redes"]["tiktok"]["canal_id"] == "6af7789762b70b94b02105ef"
    assert CAL["redes"]["instagram"]["canal_id"] == "6af7767362b70b94b020f42e"
    assert CAL["redes"]["linkedin"]["canal_id"] == "6af7774862b70b94b020fb4e"
    assert CAL["redes"]["youtube"]["destino"] == "youtube"
    assert CAL["buffer"]["organizacion"] == "6af7756b1bc8ca525703e254"
    assert CAL["buffer"]["limite_cola_por_canal"] == 10


def test_semana_completa_4_apps_y_3_luis():
    pool = [luis(i) for i in range(3)] + [app(i) for i in range(4)]
    plan = proyectar(CAL, LUNES, 7, pool, {}, con_texto)
    tipos = []
    for fecha, asignaciones, omisiones in plan:
        assert not omisiones, (fecha, omisiones)
        cortos = {a.video.tipo for a in asignaciones if a.red in BUFFER_Y_YT}
        assert len(cortos) == 1
        tipos.append(cortos.pop())
        # Las tres redes cortas usan el mismo video ese día.
        assert len({a.video.id for a in asignaciones if a.red in BUFFER_Y_YT}) == 1
    assert tipos == ["luis", "app", "luis", "app", "luis", "app", "app"]
    linkedin = [(f, a.video.id) for f, asig, _ in plan for a in asig if a.red == "linkedin"]
    assert [dia_semana(f) for f, _ in linkedin] == ["lun", "mie", "vie"]
    assert all(v.startswith("luis-") for _, v in linkedin)


def test_lunes_sin_video_de_luis_usa_uno_de_app():
    asignaciones, omisiones = planear_dia(CAL, LUNES, [app(1)], {}, con_texto)
    assert por_red(asignaciones) == {"tiktok": "app-1", "instagram": "app-1", "youtube": "app-1"}
    assert all(a.respaldo for a in asignaciones)
    # LinkedIn solo acepta videos de Luis: ese día no sale nada ahí.
    assert [(o.red, o.motivo) for o in omisiones] == [
        ("linkedin", "no hay video de luis con texto")]


def test_dia_sin_ningun_video_no_publica_nada():
    asignaciones, omisiones = planear_dia(CAL, LUNES, [], {}, con_texto)
    assert asignaciones == []
    assert {o.red for o in omisiones} == {"tiktok", "instagram", "youtube", "linkedin"}


def test_dia_de_app_sin_app_no_usa_video_de_luis():
    martes = SEMANA[1]
    asignaciones, omisiones = planear_dia(CAL, martes, [luis(1)], {}, con_texto)
    assert asignaciones == []
    assert {o.red for o in omisiones} == BUFFER_Y_YT      # LinkedIn no publica los martes


def test_nunca_repite_un_video_en_la_misma_red():
    pool = [luis(1), app(1)]
    usados = {"tiktok": {"luis-1"}, "instagram": {"luis-1"}, "youtube": {"luis-1"},
              "linkedin": {"luis-1"}}
    asignaciones, omisiones = planear_dia(CAL, LUNES, pool, usados, con_texto)
    # luis-1 ya salió: el lunes cae al respaldo de app, y LinkedIn se queda sin nada.
    assert por_red(asignaciones) == {"tiktok": "app-1", "instagram": "app-1", "youtube": "app-1"}
    assert [o.red for o in omisiones] == ["linkedin"]


def test_proyeccion_de_semanas_no_repite_y_se_vacia():
    pool = [luis(1), app(1), app(2)]
    plan = proyectar(CAL, LUNES, 14, pool, {}, con_texto)
    vistos = {}
    for fecha, asignaciones, _ in plan:
        for a in asignaciones:
            assert a.video.id not in vistos.setdefault(a.red, set()), (fecha, a.red, a.video.id)
            vistos[a.red].add(a.video.id)
    # 3 videos para 14 días: cada red corta publica exactamente 3 veces y luego nada.
    for red in BUFFER_Y_YT:
        assert len(vistos[red]) == 3
    assert vistos["linkedin"] == {"luis-1"}


def test_video_sin_texto_no_se_programa_y_se_reporta():
    pool = [luis(1), luis(2, dias_antes=1)]
    sin_tiktok = lambda video, red: not (video == "luis-1" and red == "tiktok")
    asignaciones, omisiones = planear_dia(CAL, LUNES, pool, {}, sin_tiktok)
    elegidos = por_red(asignaciones)
    assert elegidos["tiktok"] == "luis-2"            # el siguiente que sí tiene texto
    # Las demás redes prefieren el mismo video del día; luis-1 queda para después.
    assert elegidos["instagram"] == elegidos["youtube"] == elegidos["linkedin"] == "luis-2"
    plan = proyectar(CAL, LUNES, 3, pool, {}, sin_tiktok)
    miercoles = por_red(plan[2][1])
    assert miercoles["instagram"] == "luis-1" and "tiktok" not in miercoles
    assert plan[2][2][0].sin_texto == ["luis-1"]


def test_sin_texto_en_ningun_video_omite_y_lista_cuales():
    sin_nada = lambda video, red: False
    _, omisiones = planear_dia(CAL, LUNES, [luis(1), app(1)], {}, sin_nada)
    tiktok = next(o for o in omisiones if o.red == "tiktok")
    assert tiktok.sin_texto == ["app-1", "luis-1"]


def test_apps_inactivas_y_viejas_no_cuentan():
    evo = app(1, nombre="evo-ai")                                  # inactiva por defecto
    vieja = app(2, dias_antes=CAL["orden"]["app_max_dias"] + 2)
    martes = SEMANA[1]
    asignaciones, _ = planear_dia(CAL, martes, [evo, vieja], {}, con_texto)
    assert asignaciones == []
    activa = {**CAL, "apps": [{"id": "evo-ai", "activa": True}]}
    asignaciones, _ = planear_dia(activa, martes, [evo], {}, con_texto)
    assert por_red(asignaciones)["tiktok"] == "app-1"


def test_video_del_futuro_no_se_usa():
    futuro = Video("luis-9", "luis", LUNES + dt.timedelta(days=1))
    asignaciones, _ = planear_dia(CAL, LUNES, [futuro], {}, con_texto)
    assert asignaciones == []


@pytest.mark.parametrize("dia", range(7))
def test_un_solo_video_por_red_y_dia(dia):
    pool = [luis(i) for i in range(5)] + [app(i) for i in range(5)]
    asignaciones, _ = planear_dia(CAL, SEMANA[dia], pool, {}, con_texto)
    redes = [a.red for a in asignaciones]
    assert len(redes) == len(set(redes))
