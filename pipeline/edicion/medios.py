"""ffmpeg / ffprobe."""
import json
import re
import subprocess


class FfmpegError(RuntimeError):
    pass


def ffmpeg(args, silencioso=True):
    cmd = ["ffmpeg", "-y", "-hide_banner"] + (["-loglevel", "error"] if silencioso else []) + args
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise FfmpegError(p.stderr.strip()[-3000:])
    return p.stderr


def info(ruta):
    """Ancho y alto como se VEN (con la rotación del teléfono), duración y audio."""
    p = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                        str(ruta)], capture_output=True, text=True)
    if p.returncode != 0:
        raise FfmpegError(f"ffprobe no pudo leer {ruta}: {p.stderr.strip()}")
    datos = json.loads(p.stdout)
    video = next((s for s in datos["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in datos["streams"] if s.get("codec_type") == "audio"), None)
    if not video:
        raise FfmpegError(f"{ruta} no tiene pista de video")
    ancho, alto = int(video["width"]), int(video["height"])
    rotacion = 0
    for side in video.get("side_data_list", []):
        if "rotation" in side:
            rotacion = int(float(side["rotation"]))
    rotacion = rotacion or int(video.get("tags", {}).get("rotate", 0) or 0)
    if abs(rotacion) % 180 == 90:
        ancho, alto = alto, ancho
    return {"ancho": ancho, "alto": alto, "duracion": float(datos["format"]["duration"]),
            "audio": audio is not None, "tamano": int(datos["format"].get("size", 0))}


def extraer_audio(video, destino):
    ffmpeg(["-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            str(destino)])


def silencios(audio, umbral_db, minimo):
    """Intervalos [(inicio, fin)] donde el audio está por debajo de `umbral_db`."""
    log = ffmpeg(["-i", str(audio), "-af", f"silencedetect=n={umbral_db}dB:d={minimo}",
                  "-f", "null", "-"], silencioso=False)
    inicios = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    fines = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return [(max(0.0, s), e) for s, e in zip(inicios, fines)]


def cuadro(video, segundo, destino, ancho=None):
    filtro = ["-vf", f"scale={ancho}:-2"] if ancho else []
    ffmpeg(["-ss", f"{segundo:.2f}", "-i", str(video), "-frames:v", "1", *filtro, str(destino)])
