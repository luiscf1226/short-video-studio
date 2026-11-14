"""Comprueba las llaves sin publicar nada: solo lecturas.

  python -m pipeline llaves

Revisa, con los secretos del environment:
  - la cuenta de servicio ve "Videos del domingo" (y las carpetas de las apps);
  - el OAuth de Luis renueva, tiene los permisos de subir a YouTube y de Drive,
    ve su canal y ve "Videos del domingo";
  - la llave de Buffer lee cada canal y el canal está listo para programar.

Nunca imprime una llave ni un token: solo nombres de carpetas y canales.
Sale con 1 si algo falla, para que la corrida de Actions quede en rojo.
"""
import json
import os

import requests

from . import buffer as buf
from . import google

YT_UPLOAD = "https://www.googleapis.com/auth/youtube.upload"
DRIVE_TODO = "https://www.googleapis.com/auth/drive"


class Revision:
    def __init__(self):
        self.filas = []  # (estado, que, detalle); estado: ok, falla, aviso

    def ok(self, que, detalle=""):
        self.filas.append(("ok", que, detalle))

    def falla(self, que, detalle):
        self.filas.append(("falla", que, detalle))

    def aviso(self, que, detalle):
        self.filas.append(("aviso", que, detalle))

    @property
    def fallas(self):
        return [f for f in self.filas if f[0] == "falla"]

    def markdown(self):
        icono = {"ok": "✅", "falla": "❌", "aviso": "⚠️"}
        l = ["# Prueba de llaves (solo lectura)", "",
             "| | Qué | Resultado |", "|---|---|---|"]
        l += [f"| {icono[e]} | {q} | {d} |" for e, q, d in self.filas]
        l += ["", "Todo en ✅: las llaves quedaron bien." if not self.fallas else
              f"Hay {len(self.fallas)} problema(s): ver `docs/guia-llaves.md`."]
        return "\n".join(l)


def _carpeta(cred, carpeta_id):
    """Nombre de la carpeta, si la credencial la ve."""
    r = requests.get(f"{google.DRIVE}/files/{carpeta_id}",
                     params={"fields": "id,name,mimeType", "supportsAllDrives": "true"},
                     headers=cred.cabeceras(), timeout=60)
    if r.status_code == 404:
        raise google.GoogleError("no la ve (¿está compartida con esta cuenta?)")
    google._revisar(r, "leer la carpeta")
    datos = r.json()
    if datos.get("mimeType") != google.CARPETA:
        raise google.GoogleError("ese id no es una carpeta")
    return datos["name"]


def _alcances(cred):
    """Permisos que de verdad tiene el token de acceso (tokeninfo de Google)."""
    token = cred.cabeceras()["Authorization"].split(" ", 1)[1]
    r = requests.post("https://oauth2.googleapis.com/tokeninfo",
                      data={"access_token": token}, timeout=30)
    google._revisar(r, "leer los permisos del token")
    return set(r.json().get("scope", "").split())


def _canal_youtube(cred):
    r = requests.get(f"{google.YOUTUBE}/channels", params={"part": "snippet", "mine": "true"},
                     headers=cred.cabeceras(), timeout=60)
    google._revisar(r, "leer el canal de YouTube")
    items = r.json().get("items", [])
    if not items:
        raise google.GoogleError("la cuenta autorizada no tiene canal de YouTube")
    return items[0]["snippet"]["title"]


def cuenta_de_servicio(rev, cal):
    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        rev.falla("GOOGLE_SERVICE_ACCOUNT_JSON", "falta el secreto")
        return
    try:
        sa = google.Credencial.cuenta_de_servicio()
        correo = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]).get("client_email", "?")
    except (ValueError, KeyError) as exc:
        rev.falla("GOOGLE_SERVICE_ACCOUNT_JSON", f"el JSON no es válido ({type(exc).__name__}); "
                  "hay que pegar el archivo completo")
        return
    carpetas = [("Videos del domingo", cal["drive"]["carpeta_luis"])]
    for app in cal["apps"]:
        if not app.get("activa"):
            continue
        try:
            carpeta_id = google.carpeta_de_app(sa, cal, app)
        except (google.GoogleError, requests.RequestException):
            carpeta_id = None  # la falla de acceso ya sale en la fila de Videos del domingo
        if carpeta_id:
            carpetas.append((f"carpeta de {app['nombre']}", carpeta_id))
        else:
            rev.aviso(f"carpeta de {app['nombre']}",
                      f"todavía no existe «{app.get('subcarpeta', '')}» en Videos del domingo: "
                      "la crea el workflow «Videos de la app» la primera vez que sube")
    for que, carpeta_id in carpetas:
        try:
            rev.ok(f"Cuenta de servicio ve {que}", f"«{_carpeta(sa, carpeta_id)}» ({correo})")
        except (google.GoogleError, requests.RequestException) as exc:
            rev.falla(f"Cuenta de servicio ve {que}", f"{exc} — compartirla como Lector con {correo}")


def oauth(rev, cal):
    oa = google.Credencial.oauth()
    if oa is None:
        faltan = [n for n in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
                              "GOOGLE_OAUTH_REFRESH_TOKEN") if not os.environ.get(n)]
        rev.falla("OAuth de YouTube y Drive", f"faltan los secretos: {', '.join(faltan)}")
        return
    try:
        concedidos = _alcances(oa)
    except (google.GoogleError, requests.RequestException) as exc:
        rev.falla("OAuth de YouTube y Drive", str(exc))
        return
    faltan = [a.rsplit("/", 1)[1] for a in (YT_UPLOAD, DRIVE_TODO) if a not in concedidos]
    if faltan:
        rev.falla("Permisos del OAuth", f"faltan {', '.join(faltan)}: volver a sacar el token "
                  "marcando todas las casillas")
    else:
        rev.ok("Permisos del OAuth", "subir a YouTube y Drive")
    for que, fn in [("Canal de YouTube", lambda: f"«{_canal_youtube(oa)}»"),
                    ("OAuth ve Videos del domingo",
                     lambda: f"«{_carpeta(oa, cal['drive']['carpeta_luis'])}»")]:
        try:
            rev.ok(que, fn())
        except (google.GoogleError, requests.RequestException) as exc:
            rev.falla(que, str(exc))


def buffer(rev, cal, cliente=None):
    clave = os.environ.get("BUFFER_API_KEY")
    if not clave and cliente is None:
        rev.falla("BUFFER_API_KEY", "falta el secreto")
        return
    cliente = cliente or buf.Buffer(clave, cal["buffer"]["organizacion"])
    for red, conf in cal["redes"].items():
        if conf.get("destino") != "buffer":
            continue
        try:
            canal = cliente.canal(conf["canal_id"])
        except (buf.BufferError, requests.RequestException) as exc:
            rev.falla(f"Buffer · {red}", str(exc)[:200])
            continue
        problemas = buf.revisar_canal(canal, red)
        if problemas:
            rev.falla(f"Buffer · {red}", "; ".join(problemas))
        else:
            rev.ok(f"Buffer · {red}", f"«{canal.get('name', '?')}»")


def comprobar(cal):
    rev = Revision()
    cuenta_de_servicio(rev, cal)
    oauth(rev, cal)
    buffer(rev, cal)
    return rev
