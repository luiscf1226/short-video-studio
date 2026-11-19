"""Videos ya terminados del repo público redes-media (config `redes_media`).

No se editan: cada MP4 de la carpeta sale tal cual, con la URL raw de GitHub, que
ya es pública y es la que Buffer descarga. Se lee con un clon sin blobs (solo
commits y árboles), así no hace falta llave ni se gasta el límite de la API.
"""
import datetime as dt
import fnmatch
import pathlib
import subprocess
import tempfile
from urllib.parse import quote

import requests

from .calendario import Video
from .textos import id_video


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout


def excluido(nombre, patrones):
    return any(fnmatch.fnmatch(nombre.lower(), p.lower()) for p in patrones or [])


def listar(conf, tz, origen=None):
    """[Video] de tipo app con la URL raw; `disponible` es el día del último commit del archivo."""
    repo, rama, carpeta = conf["repo"], conf["rama"], conf["carpeta"].strip("/")
    origen = origen or f"https://github.com/{repo}.git"
    with tempfile.TemporaryDirectory() as tmp:
        clon = pathlib.Path(tmp) / "repo"
        try:
            subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
                            "--single-branch", "--branch", rama, origen, str(clon)],
                           check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"no se pudo clonar {repo} ({rama}): {exc.stderr.strip()[:200]}")
        videos = []
        rutas = _git(clon, "ls-tree", "-z", "--name-only", "HEAD", f"{carpeta}/").split("\0")
        for ruta in filter(None, rutas):
            nombre = ruta.rsplit("/", 1)[-1]
            if not nombre.lower().endswith(".mp4") or excluido(nombre, conf.get("excluir")):
                continue
            fecha = _git(clon, "log", "-1", "--format=%cI", "HEAD", "--", ruta).strip()
            disponible = dt.datetime.fromisoformat(fecha).astimezone(tz).date()
            url = f"https://raw.githubusercontent.com/{repo}/{rama}/{quote(ruta)}"
            videos.append(Video(id_video(nombre), "app", disponible, conf["app"], url))
    return sorted(videos, key=lambda v: v.id)


def descargar(url, destino):
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for parte in r.iter_content(1 << 20):
                f.write(parte)
    return destino
