"""La prueba de llaves: sin red, con clientes falsos. Nunca escribe."""
from pipeline import llaves
from pipeline.config import cargar_calendario

SECRETOS = ["GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_OAUTH_REFRESH_TOKEN", "BUFFER_API_KEY"]


def _sin_secretos(monkeypatch):
    for n in SECRETOS:
        monkeypatch.delenv(n, raising=False)


def test_sin_secretos_falla_y_dice_cuales(monkeypatch):
    _sin_secretos(monkeypatch)
    rev = llaves.comprobar({**cargar_calendario(), "fuente": "drive"})
    texto = rev.markdown()
    assert len(rev.fallas) == 3
    for nombre in ["GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_OAUTH_REFRESH_TOKEN", "BUFFER_API_KEY"]:
        assert nombre in texto


def test_con_redes_media_no_pide_la_cuenta_de_servicio(monkeypatch):
    _sin_secretos(monkeypatch)
    rev = llaves.comprobar(cargar_calendario())
    texto = rev.markdown()
    assert len(rev.fallas) == 2
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" not in texto
    for nombre in ["GOOGLE_OAUTH_REFRESH_TOKEN", "BUFFER_API_KEY"]:
        assert nombre in texto


def test_json_de_cuenta_de_servicio_roto(monkeypatch):
    _sin_secretos(monkeypatch)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{no es json")
    rev = llaves.Revision()
    llaves.cuenta_de_servicio(rev, cargar_calendario())
    assert rev.fallas and "no es válido" in rev.fallas[0][2]


class BufferFalso:
    def __init__(self, canales):
        self.canales = canales

    def canal(self, canal_id):
        return self.canales.get(canal_id)


def test_buffer_revisa_cada_canal(monkeypatch):
    cal = cargar_calendario()
    redes = {r: c for r, c in cal["redes"].items() if c["destino"] == "buffer"}
    canales = {c["canal_id"]: {"id": c["canal_id"], "name": r, "service": r} for r, c in redes.items()}
    # Instagram desconectado: tiene que salir como falla.
    ig = redes["instagram"]["canal_id"]
    canales[ig]["isDisconnected"] = True
    rev = llaves.Revision()
    llaves.buffer(rev, cal, cliente=BufferFalso(canales))
    estados = {q: e for e, q, _ in rev.filas}
    assert estados["Buffer · tiktok"] == "ok"
    assert estados["Buffer · linkedin"] == "ok"
    assert estados["Buffer · instagram"] == "falla"


def test_markdown_no_trae_secretos(monkeypatch):
    _sin_secretos(monkeypatch)
    monkeypatch.setenv("BUFFER_API_KEY", "clave-super-secreta")
    rev = llaves.Revision()
    rev.falla("Buffer · tiktok", "Buffer HTTP 401: unauthorized")
    assert "clave-super-secreta" not in rev.markdown()


def test_carpeta_de_app_usa_la_subcarpeta_de_videos_del_domingo(monkeypatch):
    from pipeline import google

    cal = cargar_calendario()
    app = next(a for a in cal["apps"] if a["id"] == "bible-ai")
    llamadas = []

    def hija(cred, padre, nombre, crear=True):
        llamadas.append((padre, nombre, crear))
        return "sub123"

    monkeypatch.setattr(google, "carpeta_hija", hija)
    assert google.carpeta_de_app(object(), cal, {**app, "carpeta_drive": ""}) == "sub123"
    # Solo busca: nunca la crea la cuenta de servicio (no puede escribir).
    assert llamadas == [(cal["drive"]["carpeta_luis"], app["subcarpeta"], False)]
    assert google.carpeta_de_app(object(), cal, {**app, "carpeta_drive": "otra"}) == "otra"
