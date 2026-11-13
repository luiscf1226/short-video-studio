"""Cliente mínimo de la API GraphQL de Buffer (https://developers.buffer.com).

Solo lo necesario: leer un canal, leer sus publicaciones pendientes y crear
una publicación con video, en la cola de horarios (`addToQueue`) o como
borrador (`saveToDraft`).
"""
import requests

API = "https://api.buffer.com"
SERVICIO = {"tiktok": "tiktok", "instagram": "instagram", "linkedin": "linkedin"}
PENDIENTES = ["scheduled", "needs_approval", "sending", "draft"]


class BufferError(RuntimeError):
    pass


class Buffer:
    def __init__(self, clave, organizacion, sesion=None):
        self.organizacion = organizacion
        self.sesion = sesion or requests.Session()
        self.sesion.headers.update({"Authorization": f"Bearer {clave}",
                                    "Content-Type": "application/json"})

    def _gql(self, consulta, variables=None):
        r = self.sesion.post(API, json={"query": consulta, "variables": variables or {}},
                             timeout=60)
        if r.status_code == 429:
            raise BufferError(f"Buffer: límite de la API alcanzado; reintenta después de "
                              f"{r.headers.get('Retry-After', '?')} s")
        if r.status_code >= 400:
            raise BufferError(f"Buffer HTTP {r.status_code}: {r.text[:300]}")
        datos = r.json()
        if datos.get("errors"):
            raise BufferError("Buffer: " + "; ".join(e.get("message", "?") for e in datos["errors"]))
        return datos["data"]

    def canal(self, canal_id):
        q = """query($input: ChannelInput!) { channel(input: $input) {
                 id name service isQueuePaused isDisconnected isLocked } }"""
        return self._gql(q, {"input": {"id": canal_id}})["channel"]

    def pendientes(self, canal_id):
        """Publicaciones del canal que aún no salen (programadas y borradores)."""
        q = """query($input: PostsInput!, $after: String) {
                 posts(input: $input, first: 50, after: $after) {
                   edges { node { id status dueAt text } }
                   pageInfo { hasNextPage endCursor } } }"""
        entrada = {"organizationId": self.organizacion,
                   "filter": {"channelIds": [canal_id], "status": PENDIENTES}}
        nodos, cursor = [], None
        while True:
            datos = self._gql(q, {"input": entrada, "after": cursor})["posts"]
            nodos += [e["node"] for e in datos["edges"]]
            if not datos["pageInfo"]["hasNextPage"]:
                return nodos
            cursor = datos["pageInfo"]["endCursor"]

    def crear(self, canal_id, red, texto, url_video, borrador):
        entrada = {
            "channelId": canal_id,
            "text": texto,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": [{"video": {"url": url_video}}],
        }
        if borrador:
            entrada["saveToDraft"] = True
        if red == "instagram":
            entrada["metadata"] = {"instagram": {"type": "reel", "shouldShareToFeed": True}}
        q = """mutation($input: CreatePostInput!) { createPost(input: $input) {
                 ... on PostActionSuccess { post { id status dueAt } }
                 ... on LimitReachedError { message }
                 ... on MutationError { message } } }"""
        resultado = self._gql(q, {"input": entrada})["createPost"]
        if "post" not in resultado:
            raise BufferError(f"Buffer no creó la publicación: {resultado.get('message', '?')}")
        return resultado["post"]


def revisar_canal(canal, red):
    """Problemas que impiden programar en este canal, o lista vacía."""
    problemas = []
    if canal is None:
        return ["el canal no existe en Buffer (revisar canal_id)"]
    if canal.get("service") != SERVICIO.get(red):
        problemas.append(f"el canal es de {canal.get('service')}, no de {red}")
    if canal.get("isDisconnected"):
        problemas.append("el canal está desconectado en Buffer")
    if canal.get("isLocked"):
        problemas.append("el canal está bloqueado en Buffer (¿plan?)")
    if canal.get("isQueuePaused"):
        problemas.append("la cola del canal está en pausa")
    return problemas


def programadas(pendientes):
    """Las que cuentan para el límite del plan gratis (no los borradores)."""
    return [p for p in pendientes if p["status"] != "draft"]


def ya_existe(pendientes, texto, borrador):
    """La publicación con este texto que ya está en Buffer, del mismo tipo
    (un borrador de prueba no cuenta como programada)."""
    for p in pendientes:
        if (p.get("text") or "").strip() == texto.strip() and (p["status"] == "draft") == borrador:
            return p
    return None
