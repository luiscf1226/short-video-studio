"""La URL pública desde la que Buffer descarga el video al publicarlo.

Buffer no tiene endpoint de subida: necesita una URL HTTPS directa al archivo,
sin inicio de sesión, que siga viva hasta que la publicación salga.

  drive  el MP4 queda con "cualquiera con el enlace" y se usa la descarga
         directa de drive.usercontent.google.com (gratis; se verifica antes).
  s3     un bucket S3 compatible con lectura pública, p. ej. Cloudflare R2.
"""
import os

from . import google


def publicar(cal, oauth, archivo_drive_id, ruta_local, nombre):
    proveedor = cal["url_publica"]["proveedor"]
    if proveedor == "drive":
        url = google.hacer_publico(oauth, archivo_drive_id)
    else:
        url = _s3(cal, ruta_local, nombre)
    problema = google.verificar_url_publica(url)
    if problema:
        raise RuntimeError(f"La URL pública de {nombre} no sirve para Buffer: {problema}. "
                           "Probar url_publica.proveedor: s3 en config/calendario.yaml")
    return url


def _s3(cal, ruta_local, nombre):
    import boto3

    base = cal["url_publica"]["s3_url_base"].rstrip("/")
    faltan = [n for n in ("S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")
              if not os.environ.get(n)]
    if faltan or not base:
        raise RuntimeError(f"url_publica s3: faltan {', '.join(faltan) or 's3_url_base'}")
    cliente = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"],
                           aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
                           aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])
    cliente.upload_file(str(ruta_local), os.environ["S3_BUCKET"], nombre,
                        ExtraArgs={"ContentType": "video/mp4"})
    return f"{base}/{nombre}"
