"""Estado persistente: qué videos ya se editaron y qué ya se programó.

Vive en la rama `estado` del repo (estado.json); el workflow la trae al
empezar y la empuja después de cada cambio, así una segunda corrida no
repite nada.
"""
import datetime as dt
import json
import pathlib

from .calendario import Video

VACIO = {"version": 1, "luis": {}, "apps": {}, "publicaciones": []}


class Estado:
    def __init__(self, ruta, datos=None):
        self.ruta = pathlib.Path(ruta)
        self.datos = datos or json.loads(json.dumps(VACIO))

    @classmethod
    def cargar(cls, ruta):
        ruta = pathlib.Path(ruta)
        if ruta.exists():
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            for clave, valor in VACIO.items():
                datos.setdefault(clave, json.loads(json.dumps(valor)))
            return cls(ruta, datos)
        return cls(ruta)

    def guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.datos, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        tmp.replace(self.ruta)

    # ---- videos ----
    def ya_procesado(self, drive_id):
        return self.datos["luis"].get(drive_id, {}).get("estado") == "listo"

    def intentos(self, drive_id):
        return self.datos["luis"].get(drive_id, {}).get("intentos", 0)

    def registrar_luis(self, drive_id, info):
        previo = self.datos["luis"].get(drive_id, {})
        self.datos["luis"][drive_id] = {**previo, **info}

    def registrar_app(self, drive_id, info):
        self.datos["apps"][drive_id] = {**self.datos["apps"].get(drive_id, {}), **info}

    def pool(self):
        videos = []
        for drive_id, v in self.datos["luis"].items():
            if v.get("estado") == "listo":
                videos.append(Video(v["id"], "luis", dt.date.fromisoformat(v["disponible"]),
                                    None, v.get("url", ""), v.get("editado_drive_id", "")))
        for drive_id, v in self.datos["apps"].items():
            videos.append(Video(v["id"], "app", dt.date.fromisoformat(v["disponible"]),
                                v["app"], v.get("url", ""), drive_id))
        return videos

    # ---- publicaciones ----
    def usados(self):
        """Videos que ya salieron (o van a salir) en cada red. Los borradores de
        prueba no cuentan: ese video todavía puede programarse de verdad."""
        usados = {}
        for p in self.datos["publicaciones"]:
            if p["modo"] != "borrador":
                usados.setdefault(p["red"], set()).add(p["video"])
        return usados

    def publicacion(self, fecha, red, modo):
        for p in self.datos["publicaciones"]:
            if p["fecha"] == fecha.isoformat() and p["red"] == red and p["modo"] == modo:
                return p
        return None

    def registrar_publicacion(self, fecha, red, video_id, destino, modo, ref, extra=None):
        self.datos["publicaciones"].append({
            "fecha": fecha.isoformat(), "red": red, "video": video_id, "destino": destino,
            "modo": modo, "ref": ref,
            "creado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            **(extra or {}),
        })
