"""Corrida diaria y edición local.

  python -m pipeline editar crudo.mp4 --salida build/prueba
  python -m pipeline correr --modo dry_run                 # edita y lista, no toca nada
  python -m pipeline correr --modo borrador                # borradores en Buffer, YouTube privado
  python -m pipeline correr --modo programar               # cola de Buffer + publishAt en YouTube
  python -m pipeline correr --modo dry_run --videos-locales carpeta/   # sin Drive

Programa SOLO el día objetivo (por defecto, mañana en America/Tegucigalpa).
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import secrets
import sys
import traceback
from zoneinfo import ZoneInfo

from . import buffer as buf
from . import google, publico
from .calendario import Video, dia_semana, planear_dia, proyectar
from .config import RAIZ, cargar_calendario, cargar_estilo
from .edicion import editar
from .estado import Estado
from .textos import cargar, componer, id_video, indice_valido, sugerir

MODOS = ("dry_run", "borrador", "programar")


class Resumen:
    def __init__(self, modo, objetivo):
        self.modo, self.objetivo = modo, objetivo
        self.editados, self.errores, self.avisos, self.acciones = [], [], [], []
        self.secciones = []

    def error(self, texto):
        self.errores.append(texto)
        print(f"ERROR {texto}", file=sys.stderr)

    def aviso(self, texto):
        self.avisos.append(texto)
        print(f"AVISO {texto}")

    def accion(self, texto):
        self.acciones.append(texto)
        print(texto)

    def markdown(self):
        dia = dia_semana(self.objetivo)
        l = [f"# Publicación diaria · {self.modo}",
             f"Día objetivo: **{dia} {self.objetivo.isoformat()}**", ""]
        if self.modo == "dry_run":
            l += ["> Dry-run: se editó y se lista lo que se programaría. No se tocó Buffer, "
                  "YouTube ni Drive, y el estado no cambió.", ""]
        if self.errores:
            l += ["## Errores", *[f"- {e}" for e in self.errores], ""]
        if self.avisos:
            l += ["## Avisos", *[f"- {a}" for a in self.avisos], ""]
        l += ["## Acciones", *([f"- {a}" for a in self.acciones] or ["- (ninguna)"]), ""]
        if self.editados:
            l += ["## Videos editados", ""]
            for e in self.editados:
                l += [f"### {e['id']}",
                      f"- {e['duracion_original']}s → **{e['duracion_final']}s**, "
                      f"{e['resolucion']}, {e['tramos']} tramos",
                      "- Quitado: " + ", ".join(f"{k} {v}s" for k, v in e["quitado"].items()),
                      f"- Gancho: «{e['gancho']}»"]
                l += [f"- Aviso: {a}" for a in e["avisos"]]
                l += ["", "Sugerencias de texto (no se publican; copiarlas a textos/ si sirven):",
                      "```json", json.dumps(e["sugerencias"], ensure_ascii=False, indent=1),
                      "```", ""]
        for titulo, lineas in self.secciones:
            l += [f"## {titulo}", *lineas, ""]
        return "\n".join(l)


def _fecha_local(iso, tz):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(tz).date()


def fecha_prevista(nombre):
    """El día para el que se hizo un video de app: bible-ai-2026-11-17-mar-x.mp4."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", nombre)
    try:
        return dt.date.fromisoformat(m.group(1)) if m else None
    except ValueError:
        return None


def _seguro(texto):
    """Nombre de archivo local sin barras ni espacios."""
    return re.sub(r"[^\w.-]+", "-", texto).strip("-") or "video"


def _id_unico(nombre, drive_id, existentes):
    vid = id_video(nombre)
    return vid if vid not in existentes else f"{vid}-{drive_id[:6].lower()}"


def _sugerencias(resultado, estilo, cal):
    cierre = estilo["cierre"]["texto"]
    tags = estilo["sugerencias"]["hashtags"]
    return {red: sugerir(red, resultado["frases"], tags, cierre) for red in cal["redes"]}


# ------------------------------------------------------------------- pasos

def videos_de_luis(ctx):
    cal, estado, r = ctx["cal"], ctx["estado"], ctx["r"]
    existentes = {v.id for v in estado.pool()}
    if ctx["locales"]:
        nuevos = [{"id": f"local-{p.name}", "name": p.name, "ruta": p,
                   "createdTime": dt.datetime.now(dt.timezone.utc).isoformat()}
                  for p in sorted(pathlib.Path(ctx["locales"]).glob("*.mp4"))]
    elif ctx["sa"]:
        nuevos = google.listar_videos(ctx["sa"], cal["drive"]["carpeta_luis"])
    else:
        r.aviso("Sin GOOGLE_SERVICE_ACCOUNT_JSON: no se buscaron videos nuevos en Drive")
        return
    nuevos = [f for f in nuevos if not ctx["estado"].ya_procesado(f["id"])]
    agotados = [f for f in nuevos if estado.intentos(f["id"]) >= 3]
    for f in agotados:
        r.aviso(f"{f['name']} falló 3 veces y ya no se reintenta: revisar el archivo en Drive")
    nuevos = [f for f in nuevos if f not in agotados]
    maximo = cal["drive"]["max_videos_por_corrida"]
    if len(nuevos) > maximo:
        r.aviso(f"Hay {len(nuevos)} videos nuevos; esta corrida edita {maximo} y deja el resto "
                "para la próxima")
    for f in nuevos[:maximo]:
        vid = _id_unico(f["name"], f["id"], existentes)
        carpeta = ctx["trabajo"] / _seguro(vid)
        carpeta.mkdir(parents=True, exist_ok=True)
        print(f"Editando {f['name']} -> {vid}")
        try:
            crudo = f.get("ruta") or google.descargar(
                ctx["sa"], f["id"], carpeta / (_seguro(vid) + (pathlib.Path(f["name"]).suffix or ".mp4")))
            res = editar(crudo, carpeta, ctx["estilo"])
            res["id"] = vid
            res["sugerencias"] = _sugerencias(res, ctx["estilo"], cal)
            r.editados.append(res)
            final = pathlib.Path(res["final"])
            ctx["archivos"][vid] = final
            hoy = ctx["hoy"]
            if not ctx["escribir"]:
                ctx["hipoteticos"].append(Video(vid, "luis", hoy, None, "(dry-run)"))
                continue
            editados = google.carpeta_hija(ctx["oauth"], cal["drive"]["carpeta_luis"],
                                           cal["drive"]["subcarpeta_editados"])
            # Si un intento anterior ya lo subió (y falló después), se reusa.
            editado_id = google.buscar_archivo(ctx["oauth"], editados, f["id"]) \
                or google.subir(ctx["oauth"], final, editados, f"{vid}.mp4", origen=f["id"])
            url = publico.publicar(cal, ctx["oauth"], editado_id, final,
                                   f"{vid}-{secrets.token_hex(6)}.mp4")
            estado.registrar_luis(f["id"], {
                "id": vid, "nombre": f["name"], "md5": f.get("md5Checksum"), "estado": "listo",
                "disponible": hoy.isoformat(), "editado_drive_id": editado_id, "url": url,
                "duracion_original": res["duracion_original"],
                "duracion_final": res["duracion_final"], "gancho": res["gancho"],
                "avisos": res["avisos"], "sugerencias": res["sugerencias"]})
            estado.guardar()
            existentes.add(vid)
            r.accion(f"Editado {f['name']} → Drive/Editados/{vid}.mp4")
        except Exception as exc:
            r.error(f"No se pudo editar {f['name']}: {exc}")
            traceback.print_exc()
            if ctx["escribir"]:
                estado.registrar_luis(f["id"], {"id": vid, "nombre": f["name"], "estado": "fallo",
                                                "intentos": estado.intentos(f["id"]) + 1,
                                                "error": str(exc)[:500]})
                estado.guardar()


def videos_de_apps(ctx):
    cal, estado, r = ctx["cal"], ctx["estado"], ctx["r"]
    tz = ctx["tz"]
    existentes = {v.id for v in estado.pool()}
    for app in cal["apps"]:
        if not app["activa"]:
            continue
        if not app["carpeta_drive"]:
            r.aviso(f"{app['nombre']}: falta carpeta_drive en config/calendario.yaml; sin sus "
                    "videos los días de app no publican nada")
            continue
        if not ctx["sa"]:
            continue
        for f in google.listar_videos(ctx["sa"], app["carpeta_drive"]):
            if f["id"] in estado.datos["apps"]:
                continue
            vid = _id_unico(f["name"], f["id"], existentes)
            disponible = fecha_prevista(f["name"]) or _fecha_local(f["createdTime"], tz)
            if not ctx["escribir"]:
                ctx["hipoteticos"].append(Video(vid, "app", disponible, app["id"], "(dry-run)",
                                                f["id"]))
                continue
            try:
                ruta = None
                if cal["url_publica"]["proveedor"] == "s3":
                    ruta = google.descargar(ctx["sa"], f["id"], ctx["trabajo"] / f"{_seguro(vid)}.mp4")
                url = publico.publicar(cal, ctx["oauth"], f["id"], ruta,
                                       f"{vid}-{secrets.token_hex(6)}.mp4")
                estado.registrar_app(f["id"], {"id": vid, "app": app["id"], "nombre": f["name"],
                                               "disponible": disponible.isoformat(), "url": url})
                estado.guardar()
                existentes.add(vid)
                r.accion(f"Video de {app['nombre']} disponible: {vid}")
            except Exception as exc:
                r.error(f"{app['nombre']}: no se pudo preparar {f['name']}: {exc}")


def _archivo_local(ctx, video):
    if video.id in ctx["archivos"]:
        return ctx["archivos"][video.id]
    destino = ctx["trabajo"] / f"{_seguro(video.id)}.mp4"
    if not destino.exists():
        google.descargar(ctx["sa"], video.drive_id, destino)
    ctx["archivos"][video.id] = destino
    return destino


def publicar_buffer(ctx, a, texto):
    cal, estado, r, modo = ctx["cal"], ctx["estado"], ctx["r"], ctx["modo"]
    conf = cal["redes"][a.red]
    borrador = modo == "borrador"
    cliente = ctx["buffer"]
    canal = cliente.canal(conf["canal_id"])
    problemas = buf.revisar_canal(canal, a.red)
    if problemas:
        r.error(f"{a.red}: no se programa: {'; '.join(problemas)}")
        return
    pendientes = cliente.pendientes(conf["canal_id"])
    cuerpo = componer(texto)["texto"]
    existente = buf.ya_existe(pendientes, cuerpo, borrador)
    if existente:
        estado.registrar_publicacion(ctx["objetivo"], a.red, a.video.id, "buffer", modo,
                                     existente["id"], {"recuperado": True})
        estado.guardar()
        r.accion(f"{a.red}: ya estaba en Buffer ({existente['status']}); no se duplica")
        return
    en_cola = len(buf.programadas(pendientes))
    limite = cal["buffer"]["limite_cola_por_canal"]
    if not borrador and en_cola + 1 > limite:
        r.aviso(f"{a.red}: la cola tiene {en_cola} programadas y el límite es {limite}; "
                f"no se programa {a.video.id}")
        return
    if not borrador:
        # addToQueue usa el próximo horario libre: si no cae en el día objetivo, no se crea.
        ahora = ctx.get("ahora") or dt.datetime.now(ctx["tz"])
        hueco = buf.siguiente_horario(canal, pendientes, ahora)
        if hueco is None:
            r.error(f"{a.red}: el canal no tiene horarios en la cola de Buffer (Posting "
                    "Schedule); no se programa")
            return
        if hueco.astimezone(ctx["tz"]).date() != ctx["objetivo"]:
            r.aviso(f"{a.red}: el próximo horario libre de la cola es "
                    f"{hueco.astimezone(ctx['tz']):%Y-%m-%d %H:%M}, no el {ctx['objetivo']}; "
                    f"no se programa {a.video.id}. Revisar la cola y los horarios del canal")
            return
    post = cliente.crear(conf["canal_id"], a.red, cuerpo, a.video.url, borrador)
    estado.registrar_publicacion(ctx["objetivo"], a.red, a.video.id, "buffer", modo, post["id"],
                                 {"dueAt": post.get("dueAt")})
    estado.guardar()
    if borrador:
        r.accion(f"{a.red}: borrador creado en Buffer con {a.video.id}")
        return
    cuando = post.get("dueAt")
    r.accion(f"{a.red}: {a.video.id} en la cola de Buffer ({cuando or 'sin hora'}); "
             f"quedan {en_cola + 1}/{limite}")
    if cuando and _fecha_local(cuando, ctx["tz"]) != ctx["objetivo"]:
        r.aviso(f"{a.red}: Buffer lo puso el {_fecha_local(cuando, ctx['tz'])}, no el "
                f"{ctx['objetivo']}. Revisar los horarios de la cola de ese canal: el workflow "
                "corre después del último horario del día y espera la cola vacía")


def publicar_youtube(ctx, a, texto):
    cal, estado, r, modo = ctx["cal"], ctx["estado"], ctx["r"], ctx["modo"]
    conf = cal["redes"][a.red]
    datos = componer(texto)
    marca = google.etiqueta(a.video.id)
    hora = dt.time.fromisoformat(conf["hora_publicacion"])
    momento = dt.datetime.combine(ctx["objetivo"], hora, ctx["tz"])
    publicar_en = None
    if modo == "programar":
        if momento <= dt.datetime.now(ctx["tz"]) + dt.timedelta(minutes=15):
            r.aviso(f"youtube: las {conf['hora_publicacion']} del {ctx['objetivo']} ya pasaron; "
                    "no se programa para no publicar fuera de horario")
            return
        publicar_en = momento.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    existente = google.buscar_subido(ctx["oauth"], marca)
    if existente:
        if publicar_en:
            google.programar_existente(ctx["oauth"], existente, publicar_en)
            r.accion(f"youtube: {a.video.id} ya estaba subido ({existente}); se programó para "
                     f"{momento:%Y-%m-%d %H:%M}")
        else:
            r.accion(f"youtube: {a.video.id} ya estaba subido ({existente}); no se duplica")
        estado.registrar_publicacion(ctx["objetivo"], a.red, a.video.id, "youtube", modo,
                                     existente, {"publishAt": publicar_en, "recuperado": True})
        estado.guardar()
        return
    ruta = _archivo_local(ctx, a.video)
    yt_id = google.subir_youtube(ctx["oauth"], ruta, datos["titulo"], datos["descripcion"],
                                 conf["categoria"], marca, publicar_en)
    estado.registrar_publicacion(ctx["objetivo"], a.red, a.video.id, "youtube", modo, yt_id,
                                 {"publishAt": publicar_en})
    estado.guardar()
    if publicar_en:
        r.accion(f"youtube: {a.video.id} subido ({yt_id}), sale el {momento:%Y-%m-%d %H:%M}")
    else:
        r.accion(f"youtube: {a.video.id} subido como privado ({yt_id}) para revisar")


def sin_texto(cal, pool, usados, tiene_texto, desde):
    """[(video, [redes])]: cada video que podría salir en una red pero no tiene texto.
    Los de apps vencidos (más de `app_max_dias` al día `desde`) ya no cuentan."""
    salida = []
    for video in sorted(pool, key=lambda v: (v.disponible, v.id)):
        if video.tipo == "app" and (desde - video.disponible).days > cal["orden"]["app_max_dias"]:
            continue
        redes = [red for red, conf in cal["redes"].items()
                 if video.tipo in conf["tipos"] and video.id not in usados.get(red, set())
                 and not tiene_texto(video.id, red)]
        if video.tipo == "app" and not any(a["id"] == video.app and a["activa"]
                                           for a in cal["apps"]):
            continue
        if redes:
            salida.append((video, redes))
    return salida


# ------------------------------------------------------------------- correr

def correr(args):
    estilo, cal = cargar_estilo(), cargar_calendario()
    tz = ZoneInfo(cal["zona_horaria"])
    hoy = dt.datetime.now(tz).date()
    objetivo = dt.date.fromisoformat(args.fecha) if args.fecha else hoy + dt.timedelta(days=1)
    modo = args.modo
    escribir = modo != "dry_run"
    r = Resumen(modo, objetivo)
    trabajo = pathlib.Path(args.trabajo)
    trabajo.mkdir(parents=True, exist_ok=True)
    ctx = {"estilo": estilo, "cal": cal, "tz": tz, "hoy": hoy, "objetivo": objetivo,
           "modo": modo, "escribir": escribir, "r": r, "trabajo": trabajo,
           "estado": Estado.cargar(args.estado), "locales": args.videos_locales,
           "sa": google.Credencial.cuenta_de_servicio(), "oauth": None, "buffer": None,
           "hipoteticos": [], "archivos": {}}
    if escribir:
        ctx["oauth"] = google.Credencial.oauth()
        clave = os.environ.get("BUFFER_API_KEY")
        faltan = [n for n, v in [("GOOGLE_OAUTH_*", ctx["oauth"]), ("BUFFER_API_KEY", clave),
                                 ("GOOGLE_SERVICE_ACCOUNT_JSON", ctx["sa"])] if not v]
        if faltan:
            r.error(f"Modo {modo} necesita los secretos: {', '.join(faltan)}")
            return r
        ctx["buffer"] = buf.Buffer(clave, cal["buffer"]["organizacion"])

    try:
        videos_de_luis(ctx)
        videos_de_apps(ctx)
    except Exception as exc:
        r.error(f"Drive: {exc}")

    pool = ctx["estado"].pool() + ctx["hipoteticos"]
    textos, errores_textos = cargar(args.textos)
    validos, invalidos = indice_valido(textos, cal["reglas_textos"], pool, cal["apps"])
    for e in errores_textos:
        r.aviso(f"textos: {e}")
    for (vid, red), errores in sorted(invalidos.items()):
        r.aviso(f"Texto inválido de {vid} en {red}: {'; '.join(errores)}. No se programa ahí.")
    tiene_texto = lambda vid, red: (vid, red) in validos
    usados = ctx["estado"].usados()
    asignaciones, omisiones = planear_dia(cal, objetivo, pool, usados, tiene_texto)

    for o in omisiones:
        detalle = f" Sin texto: {', '.join(o.sin_texto)}." if o.sin_texto else ""
        r.aviso(f"{o.red} el {objetivo}: no se publica nada ({o.motivo}).{detalle}")

    for a in asignaciones:
        destino = cal["redes"][a.red]["destino"]
        etiqueta = f"{a.red}: {a.video.id} ({a.video.tipo}{', respaldo' if a.respaldo else ''})"
        if not escribir:
            r.accion(f"programaría {etiqueta} vía {destino}")
            continue
        if ctx["estado"].publicacion(objetivo, a.red, modo):
            r.accion(f"{a.red}: ya se había hecho en una corrida anterior; no se repite")
            continue
        try:
            if destino == "buffer":
                publicar_buffer(ctx, a, validos[(a.video.id, a.red)])
            else:
                publicar_youtube(ctx, a, validos[(a.video.id, a.red)])
        except Exception as exc:
            r.error(f"{a.red}: {exc}")
            traceback.print_exc()

    plan = proyectar(cal, objetivo, 7, pool, usados, tiene_texto)
    lineas = ["| Día | TikTok | Instagram | YouTube | LinkedIn |", "|---|---|---|---|---|"]
    for fecha, asig, omis in plan:
        celdas = {a.red: a.video.id + (" (respaldo)" if a.respaldo else "") for a in asig}
        celdas.update({o.red: "—" for o in omis})
        lineas.append(f"| {dia_semana(fecha)} {fecha:%d/%m} | " + " | ".join(
            celdas.get(red, "") for red in ("tiktok", "instagram", "youtube", "linkedin")) + " |")
    r.secciones.append(("Proyección de 7 días con lo disponible hoy", lineas))
    faltan = sin_texto(cal, pool, usados, tiene_texto, objetivo)
    if faltan:
        apps = {a["id"]: a for a in cal["apps"]}
        lineas = []
        for video, redes in faltan:
            app = apps.get(video.app)
            extra = f" · {app['nombre']}: cierre sugerido «{app['cta']}»" if app else ""
            lineas.append(f"- `{video.id}`: falta {', '.join(redes)}{extra}")
        r.secciones.append(("Videos que no se programan por falta de texto "
                            "(textos/semana-NN.json)", lineas))
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="comando", required=True)
    ed = sub.add_parser("editar", help="editar un video local")
    ed.add_argument("video")
    ed.add_argument("--salida", default="build/editado")
    co = sub.add_parser("correr", help="la corrida diaria")
    co.add_argument("--modo", choices=MODOS, default="dry_run")
    co.add_argument("--fecha", help="día a programar, AAAA-MM-DD (por defecto mañana)")
    co.add_argument("--estado", default="estado/estado.json")
    co.add_argument("--trabajo", default="build/trabajo")
    co.add_argument("--videos-locales", help="carpeta con MP4 crudos (en vez de Drive)")
    co.add_argument("--resumen", default="build/resumen.md")
    co.add_argument("--textos", default=str(RAIZ / "textos"))
    args = ap.parse_args(argv)

    if args.comando == "editar":
        res = editar(args.video, args.salida, cargar_estilo())
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0

    if args.modo != "dry_run" and args.videos_locales:
        ap.error("--videos-locales solo se usa con --modo dry_run")
    r = correr(args)
    texto = r.markdown()
    pathlib.Path(args.resumen).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.resumen).write_text(texto, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    print("\n" + texto)
    return 1 if r.errores else 0


if __name__ == "__main__":
    sys.exit(main())
