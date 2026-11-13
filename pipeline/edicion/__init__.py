"""Edición automática: video crudo -> MP4 9:16 con cortes, subtítulos, gancho y cierre."""
import json
import pathlib
import shutil
from dataclasses import asdict

from ..config import RAIZ
from . import cortes, encuadre, medios, subtitulos, transcribir

FADE = 0.025


def editar(fuente, carpeta, estilo, palabras=None, log=print):
    """Edita `fuente` en `carpeta`. Devuelve un dict con rutas, duraciones y avisos.

    `palabras` permite saltar la transcripción (pruebas o reintentos).
    """
    fuente = pathlib.Path(fuente)
    carpeta = pathlib.Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    formato = estilo["formato"]
    ancho_out, alto_out, fps = formato["ancho"], formato["alto"], formato["fps"]
    datos = medios.info(fuente)
    if not datos["audio"]:
        raise RuntimeError(f"{fuente.name} no tiene audio: no hay nada que transcribir")

    audio = carpeta / "audio.wav"
    medios.extraer_audio(fuente, audio)
    if palabras is None:
        log(f"  transcribiendo con {estilo['transcripcion']['proveedor']} "
            f"({estilo['transcripcion']['modelo']}) ...")
        palabras = transcribir.transcribir(audio, estilo["transcripcion"])
    transcribir.guardar(palabras, carpeta / "palabras.json")
    silencios = medios.silencios(audio, estilo["cortes"]["umbral_silencio_db"],
                                 estilo["cortes"]["silencio_maximo"])

    plan = cortes.planear(palabras, silencios, datos["duracion"], estilo)
    log(f"  {datos['duracion']:.1f}s -> {plan.duracion_final:.1f}s en {len(plan.tramos)} tramos")

    caras = encuadre.rastrear_caras(fuente, datos["ancho"], datos["alto"])
    recortes = encuadre.ventanas(plan.tramos, caras, datos["ancho"], datos["alto"],
                                 ancho_out, alto_out)

    partes_dir = carpeta / "partes"
    if partes_dir.exists():
        shutil.rmtree(partes_dir)
    partes_dir.mkdir()
    partes = []
    for i, (tramo, (w, h, x, y)) in enumerate(zip(plan.tramos, recortes)):
        parte = partes_dir / f"p{i:03d}.mp4"
        dur = tramo.duracion
        medios.ffmpeg([
            "-ss", f"{tramo.inicio:.3f}", "-i", str(fuente), "-t", f"{dur:.3f}",
            "-vf", f"crop={w}:{h}:{x}:{y},scale={ancho_out}:{alto_out}:flags=lanczos,"
                   f"setsar=1,fps={fps}",
            "-af", f"afade=t=in:st=0:d={FADE},afade=t=out:st={max(0, dur - FADE):.3f}:d={FADE}",
            "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-video_track_timescale", "90000", str(parte)])
        partes.append(parte)
    lista = partes_dir / "lista.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes), encoding="utf-8")
    bruto = carpeta / "cortado.mp4"
    medios.ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(bruto)])
    duracion = medios.info(bruto)["duracion"]

    ass = carpeta / "subtitulos.ass"
    ass.write_text(subtitulos.generar(plan, estilo, duracion, ancho_out, alto_out),
                   encoding="utf-8")
    fuentes = (RAIZ / estilo["subtitulos"]["archivo_fuente"]).parent
    final = carpeta / f"{fuente.stem}-editado.mp4"
    _render_final(bruto, ass, fuentes, final, estilo)

    salida = medios.info(final)
    resultado = {
        "fuente": str(fuente),
        "final": str(final),
        "duracion_original": round(datos["duracion"], 2),
        "duracion_final": round(salida["duracion"], 2),
        "resolucion": f"{salida['ancho']}x{salida['alto']}",
        "tramos": len(plan.tramos),
        "caras_detectadas": len(caras),
        "gancho": plan.gancho,
        "frases": plan.frases,
        "quitado": plan.quitado,
        "avisos": plan.avisos,
    }
    (carpeta / "resultado.json").write_text(
        json.dumps({**resultado, "tramos_detalle": [asdict(t) for t in plan.tramos]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(partes_dir)
    audio.unlink(missing_ok=True)
    bruto.unlink(missing_ok=True)
    return resultado


def _escapar(ruta):
    return str(pathlib.Path(ruta).resolve()).replace("\\", "/").replace(":", r"\:") \
        .replace("'", r"\'")


def _render_final(video, ass, fuentes, destino, estilo):
    lufs = estilo["audio"]["lufs"]
    musica = estilo["musica"]["archivo"]
    vf = f"subtitles=filename='{_escapar(ass)}':fontsdir='{_escapar(fuentes)}'"
    cmd = ["-i", str(video)]
    if musica:
        ruta = RAIZ / musica
        if not ruta.exists():
            raise RuntimeError(f"estilo.yaml: no existe la música {musica}")
        cmd += ["-stream_loop", "-1", "-i", str(ruta), "-filter_complex",
                f"[0:v]{vf}[v];[1:a]volume={estilo['musica']['volumen_db']}dB[m];"
                f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
                f"loudnorm=I={lufs}:TP=-1.5:LRA=11[a]", "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-vf", vf, "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11"]
    cmd += ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-level", "4.1", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            "-movflags", "+faststart", str(destino)]
    medios.ffmpeg(cmd)
