"""Qué video sale en qué red cada día. Lógica pura, sin red ni disco.

Reglas (config/calendario.yaml):
  - cada día tiene un tipo (luis o app); si no hay video de ese tipo se prueba
    el respaldo (luis -> app); si tampoco hay, ese día no sale nada en esa red;
  - cada red tiene sus días y los tipos que acepta (LinkedIn: solo luis);
  - un video nunca se repite en la misma red;
  - un video sin texto válido para esa red no se programa ahí.
"""
import datetime as dt
from dataclasses import dataclass, field

from .config import DIAS


@dataclass(frozen=True)
class Video:
    id: str
    tipo: str                    # "luis" | "app"
    disponible: dt.date          # desde cuándo está listo
    app: str | None = None       # "bible-ai", "evo-ai"...
    url: str = ""
    drive_id: str = ""


@dataclass
class Asignacion:
    fecha: dt.date
    red: str
    video: Video
    respaldo: bool = False


@dataclass
class Omision:
    fecha: dt.date
    red: str
    motivo: str
    sin_texto: list = field(default_factory=list)


def dia_semana(fecha):
    return DIAS[fecha.weekday()]


def _orden(videos, criterio):
    clave = lambda v: (v.disponible, v.id)
    return sorted(videos, key=clave, reverse=criterio == "recientes_primero")


def _disponibles(cal, tipo, red, fecha, pool, usados):
    apps_activas = {a["id"] for a in cal["apps"] if a.get("activa")}
    max_dias = cal["orden"]["app_max_dias"]
    salida = []
    for v in pool:
        if v.tipo != tipo or v.disponible > fecha or v.id in usados.get(red, set()):
            continue
        if tipo == "app":
            if v.app not in apps_activas or (fecha - v.disponible).days > max_dias:
                continue
        salida.append(v)
    return _orden(salida, cal["orden"][tipo])


def planear_dia(cal, fecha, pool, usados, tiene_texto):
    """Asignaciones y omisiones de un día.

    `usados`: {red: {video_id}} ya programados (no se modifica).
    `tiene_texto(video_id, red)`: si hay texto válido de Marca para esa red.
    """
    dia = dia_semana(fecha)
    tipo_del_dia = cal["semana"][dia]
    orden_tipos = [tipo_del_dia] + list(cal["respaldo"].get(tipo_del_dia) or [])
    asignaciones, omisiones = [], []
    elegidos_hoy = []           # para que todas las redes usen el mismo video si se puede

    for red, conf in cal["redes"].items():
        if dia not in conf["dias"]:
            continue
        sin_texto = []
        elegido = None
        for tipo in orden_tipos:
            if tipo not in conf["tipos"]:
                continue
            candidatos = _disponibles(cal, tipo, red, fecha, pool, usados)
            con_texto = []
            for v in candidatos:
                if tiene_texto(v.id, red):
                    con_texto.append(v)
                else:
                    sin_texto.append(v.id)
            if con_texto:
                ya = [v for v in elegidos_hoy if v in con_texto]
                elegido = Asignacion(fecha, red, ya[0] if ya else con_texto[0],
                                     respaldo=tipo != tipo_del_dia)
                break
        if elegido:
            asignaciones.append(elegido)
            if elegido.video not in elegidos_hoy:
                elegidos_hoy.append(elegido.video)
        else:
            tipos = [t for t in orden_tipos if t in conf["tipos"]]
            motivo = (f"no hay video de {' ni de '.join(tipos)} con texto"
                      if tipos else f"{red} no acepta videos de tipo {tipo_del_dia}")
            omisiones.append(Omision(fecha, red, motivo, sorted(set(sin_texto))))
    return asignaciones, omisiones


def proyectar(cal, desde, dias, pool, usados, tiene_texto):
    """Plan de varios días seguidos, consumiendo videos como si se programaran."""
    usados = {red: set(ids) for red, ids in usados.items()}
    plan = []
    for i in range(dias):
        fecha = desde + dt.timedelta(days=i)
        asignaciones, omisiones = planear_dia(cal, fecha, pool, usados, tiene_texto)
        for a in asignaciones:
            usados.setdefault(a.red, set()).add(a.video.id)
        plan.append((fecha, asignaciones, omisiones))
    return plan
