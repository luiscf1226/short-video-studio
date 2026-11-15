#!/usr/bin/env python3
"""Saca el refresh token de OAuth de Luis y lo guarda como secreto de GitHub.

Corre en tu computadora (no en Actions). Abre el navegador para que Luis
autorice la app con su cuenta de Google (la del canal de YouTube y del Drive),
recibe el código en 127.0.0.1 y cambia el código por el refresh token.

El token NUNCA se imprime: va directo por stdin a `gh secret set`, o a un
archivo con permisos 600 si usas --archivo. Solo usa la biblioteca estándar.

  python3 scripts/sacar_refresh_token.py ~/Descargas/client_secret_XXXX.json
  python3 scripts/sacar_refresh_token.py client.json --solo-drive-file \
      --repo luiscf1226/bible-ai-honduras --env videos
  python3 scripts/sacar_refresh_token.py client.json --archivo ~/.config/videos/refresh_token

Requiere `gh` con sesión iniciada (gh auth login) salvo con --archivo.
"""
import argparse
import base64
import hashlib
import http.server
import json
import os
import pathlib
import secrets
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

# La publicación diaria: escribe en "Editados" (carpeta de Luis) y sube a YouTube.
ALCANCES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
# bible-ai-honduras: solo toca la carpeta y los videos que su script crea.
SOLO_DRIVE_FILE = ["https://www.googleapis.com/auth/drive.file"]
AUTORIZAR = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"


def cliente(ruta):
    datos = json.loads(pathlib.Path(ruta).expanduser().read_text())
    conf = datos.get("installed") or datos.get("web")
    if not conf or "installed" not in datos:
        sys.exit("El JSON no es de un cliente OAuth tipo 'App de escritorio' (falta 'installed').")
    return conf["client_id"], conf["client_secret"]


def pedir_codigo(client_id, alcances):
    verificador = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    reto = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).rstrip(b"=")
    estado = secrets.token_urlsafe(16)
    recibido = {}

    class Manejador(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            recibido.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("Listo. Ya puedes cerrar esta pestaña.".encode())

        def log_message(self, *args):  # sin logs: la URL trae el código
            pass

    servidor = http.server.HTTPServer(("127.0.0.1", 0), Manejador)
    redireccion = f"http://127.0.0.1:{servidor.server_port}"
    url = AUTORIZAR + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redireccion, "response_type": "code",
        "scope": " ".join(alcances), "access_type": "offline", "prompt": "consent",
        "code_challenge": reto.decode(), "code_challenge_method": "S256", "state": estado,
    })
    hilo = threading.Thread(target=servidor.handle_request, daemon=True)
    hilo.start()
    print("Abriendo el navegador para autorizar. Si no se abre, copia esta URL:\n")
    print(url + "\n")
    webbrowser.open(url)
    hilo.join(timeout=600)
    servidor.server_close()
    if recibido.get("state") != estado:
        sys.exit("La respuesta no coincide con la solicitud (state). Intenta de nuevo.")
    if "code" not in recibido:
        sys.exit(f"Google no devolvió un código: {recibido.get('error', 'sin respuesta')}")
    return recibido["code"], verificador, redireccion


def canjear(client_id, client_secret, codigo, verificador, redireccion, alcances):
    cuerpo = urllib.parse.urlencode({
        "client_id": client_id, "client_secret": client_secret, "code": codigo,
        "code_verifier": verificador, "grant_type": "authorization_code",
        "redirect_uri": redireccion}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN, data=cuerpo), timeout=60) as r:
            datos = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"Google rechazó el código: HTTP {exc.code}")
    if "refresh_token" not in datos:
        sys.exit("Google no entregó refresh token. Quita el acceso de la app en "
                 "https://myaccount.google.com/permissions y vuelve a correr el script.")
    concedidos = set(datos.get("scope", "").split())
    faltan = set(alcances) - concedidos
    if faltan:
        sys.exit(f"Faltan permisos (hay que marcar todas las casillas): {', '.join(faltan)}")
    sobran = concedidos - set(alcances)
    if alcances == SOLO_DRIVE_FILE and sobran:
        # Este token va a un repo público: tiene que ser exactamente drive.file.
        sys.exit(f"El token trae permisos de más ({', '.join(sorted(sobran))}). Quita el acceso "
                 "en https://myaccount.google.com/permissions y vuelve a correr el script.")
    return datos["refresh_token"]


def guardar_en_github(nombre, valor, repo, env):
    p = subprocess.run(["gh", "secret", "set", nombre, "--repo", repo, "--env", env],
                       input=valor, text=True, capture_output=True)
    if p.returncode != 0:
        sys.exit(f"gh no pudo guardar {nombre}: {p.stderr.strip()}")
    print(f"  {nombre} guardado en {repo} (environment {env})")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente_json", help="el JSON del cliente OAuth 'App de escritorio'")
    ap.add_argument("--repo", default="luiscf1226/short-video-studio")
    ap.add_argument("--env", default="videos")
    ap.add_argument("--archivo", help="guardar el token en este archivo (600) en vez de GitHub")
    ap.add_argument("--solo-drive-file", action="store_true",
                    help="token mínimo para bible-ai-honduras: solo lo que su script crea")
    args = ap.parse_args()

    alcances = SOLO_DRIVE_FILE if args.solo_drive_file else ALCANCES
    client_id, client_secret = cliente(args.cliente_json)
    codigo, verificador, redireccion = pedir_codigo(client_id, alcances)
    refresh = canjear(client_id, client_secret, codigo, verificador, redireccion, alcances)

    if args.archivo:
        ruta = pathlib.Path(args.archivo).expanduser()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(refresh)
        print(f"Refresh token guardado en {ruta} (permisos 600). No lo subas a ningún repo.")
        return
    guardar_en_github("GOOGLE_OAUTH_CLIENT_ID", client_id, args.repo, args.env)
    guardar_en_github("GOOGLE_OAUTH_CLIENT_SECRET", client_secret, args.repo, args.env)
    guardar_en_github("GOOGLE_OAUTH_REFRESH_TOKEN", refresh, args.repo, args.env)
    print("Listo. El token no se mostró en pantalla ni quedó en ningún archivo.")


if __name__ == "__main__":
    main()
