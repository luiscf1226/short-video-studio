"""Buffer: límite de 10 en la cola, idempotencia y borradores. Sin red: cliente falso."""
import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from pipeline.__main__ import Resumen, publicar_buffer
from pipeline.buffer import revisar_canal
from pipeline.calendario import Asignacion, Video
from pipeline.config import cargar_calendario
from pipeline.estado import Estado
from pipeline.textos import Texto

CAL = cargar_calendario()
MANANA = dt.date(2026, 11, 16)
TZ = ZoneInfo(CAL["zona_horaria"])
TEXTO = Texto("luis-1", "tiktok", "Publico todos los días.", ["#ia", "#hn", "#tech"])
CUERPO = "Publico todos los días.\n\n#ia #hn #tech"


class BufferFalso:
    def __init__(self, pendientes=None, servicio="tiktok", due="2026-11-16T18:00:00Z"):
        self.posts = list(pendientes or [])
        self.servicio, self.due = servicio, due
        self.creados = []

    def canal(self, canal_id):
        return {"id": canal_id, "service": self.servicio, "isQueuePaused": False,
                "isDisconnected": False, "isLocked": False}

    def pendientes(self, canal_id):
        return list(self.posts)

    def crear(self, canal_id, red, texto, url, borrador):
        post = {"id": f"p{len(self.creados) + 1}", "text": texto,
                "status": "draft" if borrador else "scheduled",
                "dueAt": None if borrador else self.due}
        self.creados.append((canal_id, red, texto, url, borrador))
        self.posts.append(post)
        return post


def contexto(tmp_path, cliente, modo="programar"):
    return {"cal": CAL, "estado": Estado(tmp_path / "estado.json"), "r": Resumen(modo, MANANA),
            "modo": modo, "buffer": cliente, "objetivo": MANANA, "tz": TZ}


def asignacion():
    return Asignacion(MANANA, "tiktok", Video("luis-1", "luis", MANANA, url="https://x/v.mp4"))


def test_programa_en_la_cola_del_canal_configurado(tmp_path):
    cliente = BufferFalso()
    ctx = contexto(tmp_path, cliente)
    publicar_buffer(ctx, asignacion(), TEXTO)
    assert cliente.creados == [("6af7789762b70b94b02105ef", "tiktok", CUERPO,
                                "https://x/v.mp4", False)]
    assert ctx["estado"].usados() == {"tiktok": {"luis-1"}}
    assert not ctx["r"].avisos and not ctx["r"].errores


@pytest.mark.parametrize("en_cola,programa", [(8, True), (9, True), (10, False), (12, False)])
def test_no_pasa_de_10_programadas(tmp_path, en_cola, programa):
    otros = [{"id": f"o{i}", "status": "scheduled", "text": f"otro {i}"} for i in range(en_cola)]
    borradores = [{"id": f"b{i}", "status": "draft", "text": f"b {i}"} for i in range(5)]
    cliente = BufferFalso(otros + borradores)
    ctx = contexto(tmp_path, cliente)
    publicar_buffer(ctx, asignacion(), TEXTO)
    assert bool(cliente.creados) is programa
    if not programa:
        assert "límite es 10" in ctx["r"].avisos[0]
        assert ctx["estado"].usados() == {}


def test_dos_corridas_no_duplican(tmp_path):
    cliente = BufferFalso()
    publicar_buffer(contexto(tmp_path, cliente), asignacion(), TEXTO)
    # Segunda corrida con el estado perdido: igual encuentra la publicación en Buffer.
    ctx = contexto(tmp_path, cliente)
    publicar_buffer(ctx, asignacion(), TEXTO)
    assert len(cliente.creados) == 1
    assert "no se duplica" in ctx["r"].acciones[0]
    assert ctx["estado"].publicacion(MANANA, "tiktok", "programar")["recuperado"]


def test_borrador_no_cuenta_como_publicado_ni_bloquea_la_programacion(tmp_path):
    cliente = BufferFalso()
    ctx = contexto(tmp_path, cliente, "borrador")
    publicar_buffer(ctx, asignacion(), TEXTO)
    assert cliente.creados[0][4] is True                       # saveToDraft
    assert ctx["estado"].usados() == {}                         # el video sigue disponible
    ctx2 = contexto(tmp_path, cliente, "programar")
    ctx2["estado"] = ctx["estado"]
    publicar_buffer(ctx2, asignacion(), TEXTO)                  # el borrador no lo frena
    assert [c[4] for c in cliente.creados] == [True, False]


def test_avisa_si_buffer_lo_pone_otro_dia(tmp_path):
    cliente = BufferFalso(due="2026-11-17T18:00:00Z")
    ctx = contexto(tmp_path, cliente)
    publicar_buffer(ctx, asignacion(), TEXTO)
    assert "no el 2026-11-16" in ctx["r"].avisos[0]


def test_canal_equivocado_o_en_pausa_no_programa(tmp_path):
    cliente = BufferFalso(servicio="instagram")
    ctx = contexto(tmp_path, cliente)
    publicar_buffer(ctx, asignacion(), TEXTO)
    assert not cliente.creados and "no de tiktok" in ctx["r"].errores[0]
    assert revisar_canal({"service": "tiktok", "isQueuePaused": True}, "tiktok") == [
        "la cola del canal está en pausa"]
