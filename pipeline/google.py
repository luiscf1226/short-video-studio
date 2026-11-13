"""Google Drive y YouTube por REST.

Dos credenciales:
  - cuenta de servicio (GOOGLE_SERVICE_ACCOUNT_JSON), solo lectura: detecta y
    descarga los videos nuevos. Luis comparte la carpeta con ella como Lector.
  - OAuth de Luis (GOOGLE_OAUTH_CLIENT_ID / _SECRET / _REFRESH_TOKEN): sube a
    "Editados" y a YouTube. Las cuentas de servicio no tienen cuota de
    almacenamiento y no pueden subir archivos al Drive personal de Luis.
"""
import json
import os
import pathlib
import re

import requests

DRIVE = "https://www.googleapis.com/drive/v3"
SUBIDA_DRIVE = "https://www.googleapis.com/upload/drive/v3/files"
YOUTUBE = "https://www.googleapis.com/youtube/v3"
SUBIDA_YOUTUBE = "https://www.googleapis.com/upload/youtube/v3/videos"
CARPETA = "application/vnd.google-apps.folder"
ALCANCES_OAUTH = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class GoogleError(RuntimeError):
    pass


class Credencial:
    def __init__(self, creds):
        self._creds = creds

    @classmethod
    def cuenta_de_servicio(cls):
        from google.oauth2 import service_account

        info = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not info:
            return None
        creds = service_account.Credentials.from_service_account_info(
            json.loads(info), scopes=["https://www.googleapis.com/auth/drive.readonly"])
        return cls(creds)

    @classmethod
    def oauth(cls):
        from google.oauth2.credentials import Credentials

        nombres = ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
                   "GOOGLE_OAUTH_REFRESH_TOKEN"]
        valores = [os.environ.get(n) for n in nombres]
        if not all(valores):
            return None
        cliente, secreto, refresh = valores
        return cls(Credentials(None, refresh_token=refresh, client_id=cliente,
                               client_secret=secreto,
                               token_uri="https://oauth2.googleapis.com/token",
                               scopes=ALCANCES_OAUTH))

    def cabeceras(self):
        from google.auth.transport.requests import Request

        if not self._creds.valid:
            try:
                self._creds.refresh(Request())
            except Exception as exc:  # el mensaje de google-auth no trae el token
                raise GoogleError(
                    "No se pudo renovar la credencial de Google. Si es la de OAuth, el "
                    "refresh token caducó o fue revocado: hay que sacar uno nuevo con "
                    f"scripts/sacar_refresh_token.py ({type(exc).__name__})") from None
        return {"Authorization": f"Bearer {self._creds.token}"}


def _revisar(r, que):
    if r.status_code >= 400:
        raise GoogleError(f"{que}: HTTP {r.status_code} {r.text[:400]}")
    return r


# ---------------------------------------------------------------- Drive

def listar_videos(cred, carpeta_id):
    archivos, pagina = [], None
    while True:
        params = {
            "q": f"'{carpeta_id}' in parents and trashed = false and mimeType contains 'video/'",
            "fields": "nextPageToken, files(id, name, md5Checksum, createdTime, size, mimeType)",
            "pageSize": 100, "orderBy": "createdTime",
            "supportsAllDrives": "true", "includeItemsFromAllDrives": "true",
        }
        if pagina:
            params["pageToken"] = pagina
        r = _revisar(requests.get(f"{DRIVE}/files", params=params, headers=cred.cabeceras(),
                                  timeout=60), f"listar la carpeta {carpeta_id}")
        datos = r.json()
        archivos += datos.get("files", [])
        pagina = datos.get("nextPageToken")
        if not pagina:
            return archivos


def descargar(cred, archivo_id, destino):
    destino = pathlib.Path(destino)
    with requests.get(f"{DRIVE}/files/{archivo_id}", params={"alt": "media",
                      "supportsAllDrives": "true"}, headers=cred.cabeceras(), stream=True,
                      timeout=600) as r:
        _revisar(r, f"descargar {archivo_id}")
        with open(destino, "wb") as f:
            for bloque in r.iter_content(1 << 20):
                f.write(bloque)
    return destino


def carpeta_hija(cred, padre_id, nombre, crear=True):
    """Id de la subcarpeta `nombre` dentro de `padre_id`; la crea si falta."""
    nombre_q = nombre.replace("'", "\\'")
    params = {"q": f"'{padre_id}' in parents and name = '{nombre_q}' and mimeType = '{CARPETA}' "
                   "and trashed = false",
              "fields": "files(id)", "supportsAllDrives": "true",
              "includeItemsFromAllDrives": "true"}
    r = _revisar(requests.get(f"{DRIVE}/files", params=params, headers=cred.cabeceras(),
                              timeout=60), f"buscar la carpeta {nombre}")
    encontradas = r.json().get("files", [])
    if encontradas:
        return encontradas[0]["id"]
    if not crear:
        return None
    r = _revisar(requests.post(f"{DRIVE}/files", params={"supportsAllDrives": "true"},
                               json={"name": nombre, "mimeType": CARPETA, "parents": [padre_id]},
                               headers=cred.cabeceras(), timeout=60), f"crear {nombre}")
    return r.json()["id"]


def buscar_archivo(cred, carpeta_id, origen):
    """Id del archivo de la carpeta que se subió desde el crudo `origen`, o None."""
    origen_q = origen.replace("\\", "\\\\").replace("'", "\\'")
    params = {"q": f"'{carpeta_id}' in parents and trashed = false and "
                   f"appProperties has {{ key='origen' and value='{origen_q}' }}",
              "fields": "files(id)", "supportsAllDrives": "true",
              "includeItemsFromAllDrives": "true"}
    r = _revisar(requests.get(f"{DRIVE}/files", params=params, headers=cred.cabeceras(),
                              timeout=60), f"buscar el editado de {origen}")
    encontrados = r.json().get("files", [])
    return encontrados[0]["id"] if encontrados else None


def subir(cred, ruta, carpeta_id, nombre=None, tipo="video/mp4", origen=None):
    """Sube `ruta`. `origen` (id del crudo en Drive) queda marcado para reconocerlo."""
    ruta = pathlib.Path(ruta)
    meta = {"name": nombre or ruta.name, "parents": [carpeta_id]}
    if origen:
        meta["appProperties"] = {"origen": origen}
    r = _revisar(requests.post(
        SUBIDA_DRIVE, params={"uploadType": "resumable", "supportsAllDrives": "true"},
        json=meta, headers={**cred.cabeceras(), "X-Upload-Content-Type": tipo,
                            "X-Upload-Content-Length": str(ruta.stat().st_size)},
        timeout=60), f"iniciar la subida de {ruta.name}")
    with open(ruta, "rb") as f:
        r = _revisar(requests.put(r.headers["Location"], data=f,
                                  headers={"Content-Type": tipo}, timeout=1800),
                     f"subir {ruta.name}")
    return r.json()["id"]


def hacer_publico(cred, archivo_id):
    """Cualquiera con el enlace puede leerlo (no aparece en búsquedas)."""
    _revisar(requests.post(f"{DRIVE}/files/{archivo_id}/permissions",
                           params={"supportsAllDrives": "true"},
                           json={"role": "reader", "type": "anyone"},
                           headers=cred.cabeceras(), timeout=60), f"publicar {archivo_id}")
    return url_directa(archivo_id)


def url_directa(archivo_id):
    return f"https://drive.usercontent.google.com/download?id={archivo_id}&export=download&confirm=t"


def verificar_url_publica(url):
    """Que la URL entregue el MP4 sin sesión: 200/206, sin HTML, con caja 'ftyp'."""
    try:
        with requests.get(url, headers={"Range": "bytes=0-1023"}, stream=True, timeout=60,
                          allow_redirects=True) as r:
            cabeza = next(r.iter_content(1024), b"")
            tipo = r.headers.get("Content-Type", "")
            if r.status_code not in (200, 206):
                return f"HTTP {r.status_code}"
            if "html" in tipo or b"ftyp" not in cabeza[:64]:
                return f"no entrega un MP4 directo (Content-Type {tipo or '?'})"
    except requests.RequestException as exc:
        return f"no responde ({type(exc).__name__})"
    return None


# ---------------------------------------------------------------- YouTube

def etiqueta(video_id):
    """Marca invisible para reconocer un video ya subido (idempotencia)."""
    return "ssv-" + re.sub(r"[^a-z0-9-]", "-", video_id.lower())[:60]


def buscar_subido(cred, marca, revisar=50):
    """Id del video del canal que lleva la etiqueta `marca`, entre los últimos subidos."""
    r = _revisar(requests.get(f"{YOUTUBE}/channels", params={"part": "contentDetails",
                              "mine": "true"}, headers=cred.cabeceras(), timeout=60),
                 "leer el canal de YouTube")
    canales = r.json().get("items", [])
    if not canales:
        raise GoogleError("La cuenta de OAuth no tiene canal de YouTube")
    lista = canales[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    r = _revisar(requests.get(f"{YOUTUBE}/playlistItems", params={
        "part": "contentDetails", "playlistId": lista, "maxResults": revisar},
        headers=cred.cabeceras(), timeout=60), "listar los videos subidos")
    ids = [i["contentDetails"]["videoId"] for i in r.json().get("items", [])]
    if not ids:
        return None
    r = _revisar(requests.get(f"{YOUTUBE}/videos", params={"part": "snippet",
                              "id": ",".join(ids)}, headers=cred.cabeceras(), timeout=60),
                 "leer etiquetas")
    for item in r.json().get("items", []):
        if marca in item["snippet"].get("tags", []):
            return item["id"]
    return None


def subir_youtube(cred, ruta, titulo, descripcion, categoria, marca, publicar_en=None):
    """Sube privado; con `publicar_en` (ISO UTC) YouTube lo publica solo a esa hora."""
    ruta = pathlib.Path(ruta)
    estado = {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    if publicar_en:
        estado["publishAt"] = publicar_en
    cuerpo = {"snippet": {"title": titulo, "description": descripcion, "categoryId": categoria,
                          "tags": [marca], "defaultLanguage": "es",
                          "defaultAudioLanguage": "es"},
              "status": estado}
    r = _revisar(requests.post(
        SUBIDA_YOUTUBE, params={"uploadType": "resumable", "part": "snippet,status"},
        json=cuerpo, headers={**cred.cabeceras(), "X-Upload-Content-Type": "video/mp4",
                              "X-Upload-Content-Length": str(ruta.stat().st_size)},
        timeout=60), "iniciar la subida a YouTube")
    with open(ruta, "rb") as f:
        r = _revisar(requests.put(r.headers["Location"], data=f,
                                  headers={"Content-Type": "video/mp4"}, timeout=1800),
                     "subir a YouTube")
    return r.json()["id"]


def programar_existente(cred, video_id, publicar_en):
    """Le pone fecha de publicación a un video privado que ya está en el canal
    (p. ej. el que subió la prueba en modo borrador)."""
    _revisar(requests.put(f"{YOUTUBE}/videos", params={"part": "status"}, json={
        "id": video_id, "status": {"privacyStatus": "private", "publishAt": publicar_en,
                                   "selfDeclaredMadeForKids": False}},
        headers=cred.cabeceras(), timeout=60), f"programar {video_id}")
