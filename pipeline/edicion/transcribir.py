"""Transcripción palabra por palabra.

Por defecto faster-whisper en el propio runner (sin llave, sin costo). Como
alternativa, whisper-1 de OpenAI (USD 0.006 por minuto) con OPENAI_API_KEY.
Las dos reciben un prompt con muletillas para que no las borren.
"""
import json
import os

import requests


def transcribir(audio, conf):
    if conf["proveedor"] == "openai":
        return _openai(audio, conf)
    return _faster_whisper(audio, conf)


def _faster_whisper(audio, conf):
    from faster_whisper import WhisperModel

    modelo = WhisperModel(conf["modelo"], device="cpu", compute_type="int8")
    segmentos, _ = modelo.transcribe(
        _muestras(audio), language=conf["idioma"], word_timestamps=True,
        initial_prompt=conf["prompt"], condition_on_previous_text=False,
        beam_size=5, vad_filter=False)
    palabras = []
    for seg in segmentos:
        for w in seg.words or []:
            texto = w.word.strip()
            if texto:
                palabras.append({"text": texto, "start": round(w.start, 3),
                                 "end": round(w.end, 3)})
    return palabras


def _muestras(audio):
    """WAV mono 16 kHz -> float32. Así faster-whisper no decodifica con PyAV, cuyas
    versiones nuevas rompen su `decode_audio`."""
    import wave

    import numpy as np

    with wave.open(str(audio), "rb") as w:
        if w.getframerate() != 16000 or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("se esperaba WAV mono de 16 kHz y 16 bits")
        datos = w.readframes(w.getnframes())
    return np.frombuffer(datos, np.int16).astype(np.float32) / 32768.0


def _openai(audio, conf):
    clave = os.environ.get("OPENAI_API_KEY")
    if not clave:
        raise RuntimeError("transcripcion.proveedor es 'openai' y falta OPENAI_API_KEY")
    with open(audio, "rb") as f:
        r = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {clave}"},
            files={"file": ("audio.wav", f, "audio/wav")},
            data=[("model", "whisper-1"), ("language", conf["idioma"]),
                  ("prompt", conf["prompt"]), ("response_format", "verbose_json"),
                  ("timestamp_granularities[]", "word"),
                  ("timestamp_granularities[]", "segment")],
            timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI respondió {r.status_code}: {r.text[:300]}")
    datos = r.json()
    return [{"text": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)}
            for w in datos.get("words", []) if w["word"].strip()]


def guardar(palabras, ruta):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(palabras, f, ensure_ascii=False, indent=1)
