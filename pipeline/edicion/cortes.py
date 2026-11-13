"""Qué se queda del video: lógica pura sobre la transcripción palabra por palabra.

Entrada: palabras [{text, start, end}] en segundos del ORIGINAL, los silencios
que midió ffmpeg y la duración. Salida: un `Plan` con los tramos que se
quedan (ya partidos cada 3-5 s con su zoom), el mapa de tiempos y el gancho.
"""
import difflib
import re
from dataclasses import dataclass, field

from ..config import plegar

FIN_FRASE = re.compile(r"[.!?…]$")
PAUSA_ESCRITA = re.compile(r"[,.;:!?…]$")
DEBILES = {"a", "al", "de", "del", "el", "la", "los", "las", "lo", "un", "una", "y", "o", "que",
           "en", "con", "por", "para", "sin", "como", "cuando", "donde", "mi", "tu", "su", "se",
           "les", "me", "te", "nos", "todos", "todas", "muy", "mas", "pero", "es", "son"}


@dataclass
class Tramo:
    inicio: float           # segundos del original
    fin: float
    zoom: float = 1.0
    salida: float = 0.0     # dónde empieza en el video editado

    @property
    def duracion(self):
        return self.fin - self.inicio


@dataclass
class Plan:
    tramos: list
    palabras: list                     # palabras que quedan, en tiempo de SALIDA
    gancho: str
    gancho_fin: float                  # cuándo termina de decirse el gancho (salida)
    duracion_original: float
    duracion_final: float
    quitado: dict = field(default_factory=dict)   # motivo -> segundos
    avisos: list = field(default_factory=list)
    frases: list = field(default_factory=list)


def _frases(palabras, pausa=0.5):
    """Índices [i, j) de cada frase: se corta en pausas o en punto final."""
    frases, inicio = [], 0
    for i in range(1, len(palabras) + 1):
        fin = i == len(palabras)
        if not fin:
            hueco = palabras[i]["start"] - palabras[i - 1]["end"]
            fin = hueco >= pausa or FIN_FRASE.search(palabras[i - 1]["text"]) is not None
        if fin:
            frases.append((inicio, i))
            inicio = i
    return frases


def _saludo(plegadas, saludos):
    """Cuántas palabras iniciales son un saludo ("hola a todos" -> 3)."""
    mejor = 0
    for saludo in saludos:
        partes = plegar(saludo).split()
        n = len(partes)
        if n and plegadas[:n] == partes:
            mejor = max(mejor, n)
    return mejor


def _muletillas(palabras, plegadas, estilo):
    """Índices de palabras que son muletilla."""
    cortes = estilo["cortes"]
    siempre = {plegar(m) for m in cortes["muletillas_siempre"]}
    en_pausa = sorted((plegar(m).split() for m in cortes["muletillas_en_pausa"]),
                      key=len, reverse=True)
    pausa = cortes["pausa_muletilla"]
    n = len(palabras)
    marcadas = set()

    def aislada(i, j):
        """La muletilla [i, j) está suelta: con pausa (o coma) antes Y después.

        "Bueno, vamos" y "Eh, este... el truco" se cortan; "Este truco",
        "me quedo con este." y "Bueno es mejor" no, porque la palabra va
        pegada a la frase por uno de los dos lados.
        """
        antes = palabras[i]["start"] - palabras[i - 1]["end"] if i > 0 else 99
        pausa_antes = antes >= pausa or (i > 0 and PAUSA_ESCRITA.search(palabras[i - 1]["text"]))
        if j >= n:
            return False
        despues = palabras[j]["start"] - palabras[j - 1]["end"]
        pausa_despues = despues >= pausa or PAUSA_ESCRITA.search(palabras[j - 1]["text"])
        return bool(pausa_antes and pausa_despues)

    i = 0
    while i < n:
        if plegadas[i] in siempre:
            marcadas.add(i)
            i += 1
            continue
        for partes in en_pausa:
            j = i + len(partes)
            if plegadas[i:j] == partes and aislada(i, j):
                marcadas.update(range(i, j))
                i = j - 1
                break
        i += 1
    return marcadas


def _tartamudeos(palabras, plegadas, fuera):
    marcadas = set()
    vivos = [i for i in range(len(palabras)) if i not in fuera]
    for a, b in zip(vivos, vivos[1:]):
        if plegadas[a] and plegadas[a] == plegadas[b] \
                and palabras[b]["start"] - palabras[a]["end"] < 0.7:
            marcadas.add(a)
    return marcadas


def _es_toma_repetida(primera, segunda, terminada, umbral):
    """¿`segunda` vuelve a decir `primera`? Tres casos:

      - intento abandonado: la primera es el comienzo exacto de la segunda
        ("Hoy les voy a" / "Hoy les voy a enseñar cómo...");
      - la misma frase dicha otra vez, casi igual (parecido >= 0.8);
      - un intento que no terminó (sin punto) y arranca casi igual.

    Dos frases completas que solo comparten el arranque ("La IA te ayuda a
    escribir. La IA te ayuda a programar.") no son tomas repetidas.
    """
    if len(primera) < 2 or len(segunda) < 2 or primera[:2] != segunda[:2]:
        return False
    if segunda[:len(primera)] == primera:
        return True
    if difflib.SequenceMatcher(None, primera, segunda).ratio() >= 0.8:
        return True
    if not terminada:
        return difflib.SequenceMatcher(None, primera, segunda[:len(primera)]).ratio() >= umbral
    return False


def _tomas_repetidas(palabras, plegadas, fuera, umbral):
    """Frases que se vuelven a empezar: se quita el intento y se queda la última."""
    frases = _frases(palabras)
    marcadas = set()
    contenido = [[plegadas[k] for k in range(i, j) if k not in fuera and plegadas[k]]
                 for i, j in frases]
    for a in range(len(frases)):
        primera = contenido[a]
        if len(primera) < 2:
            continue
        terminada = FIN_FRASE.search(palabras[frases[a][1] - 1]["text"]) is not None
        for b in range(a + 1, min(a + 3, len(frases))):
            if _es_toma_repetida(primera, contenido[b], terminada, umbral):
                # Todo desde el intento fallido hasta que empieza la toma buena.
                marcadas.update(range(frases[a][0], frases[b][0]))
                break
    return marcadas


def _termina(fin, silencios):
    """Dónde se apaga de verdad la voz: si el audio queda en silencio un poco
    después de lo que dice Whisper, el final real es ese."""
    cerca = [s for s, _ in silencios if fin - 0.25 <= s <= fin + 0.4]
    return max([fin] + cerca)


def _empieza(inicio, silencios):
    """Dónde arranca de verdad la voz: el final del silencio previo, si es antes."""
    cerca = [e for _, e in silencios if inicio - 0.4 <= e <= inicio + 0.25]
    return min([inicio] + cerca)


def _unir(rangos, junto=0.02):
    rangos = sorted((s, e) for s, e in rangos if e > s)
    salida = []
    for s, e in rangos:
        if salida and s <= salida[-1][1] + junto:
            salida[-1][1] = max(salida[-1][1], e)
        else:
            salida.append([s, e])
    return [tuple(r) for r in salida]


def _invertir(quitar, total, minimo=0.12):
    quedan, cursor = [], 0.0
    for s, e in quitar:
        s, e = max(0.0, min(s, total)), max(0.0, min(e, total))
        if s > cursor:
            quedan.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < total:
        quedan.append((cursor, total))
    return [(round(s, 3), round(e, 3)) for s, e in quedan if e - s >= minimo]


def _partir(rangos, palabras, minimo, maximo):
    """Parte cada tramo largo en pedazos de `minimo`-`maximo` s, entre palabras."""
    objetivo = (minimo + maximo) / 2
    salida = []
    for s, e in rangos:
        cortes = [s]
        while e - cortes[-1] > maximo:
            desde = cortes[-1]
            huecos = [(palabras[k]["end"] + palabras[k + 1]["start"]) / 2
                      for k in range(len(palabras) - 1)
                      if desde + minimo <= palabras[k]["end"]
                      and palabras[k + 1]["start"] <= desde + maximo
                      and palabras[k + 1]["start"] < e]
            if huecos:
                corte = min(huecos, key=lambda t: abs(t - desde - objetivo))
            else:
                corte = desde + objetivo
            if e - corte < minimo * 0.5:
                break
            cortes.append(corte)
        cortes.append(e)
        salida.extend(zip(cortes, cortes[1:]))
    return salida


def _mapear(inicio, fin, tramos):
    """Tiempo del original -> tiempo de salida, con lo que sobrevivió de la palabra."""
    tocados = [t for t in tramos if min(fin, t.fin) - max(inicio, t.inicio) > 0]
    if not tocados:
        return None
    a, b = tocados[0], tocados[-1]
    s = a.salida + max(inicio, a.inicio) - a.inicio
    e = b.salida + min(fin, b.fin) - b.inicio
    return round(s, 3), round(max(e, s + 0.08), 3)


def planear(palabras, silencios, total, estilo):
    cortes = estilo["cortes"]
    formato = estilo["formato"]
    gancho_conf = estilo["gancho"]
    palabras = [w for w in palabras if w["end"] > w["start"] and w["start"] < total]
    if not palabras:
        raise ValueError("La transcripción no tiene palabras: ¿el video tiene voz?")
    plegadas = [plegar(w["text"]) for w in palabras]
    quitado = {}
    fuera = {}

    def marcar(indices, motivo):
        for i in indices:
            fuera.setdefault(i, motivo)

    marcar(range(_saludo(plegadas, gancho_conf["saludos_a_recortar"])), "saludo")
    marcar(_muletillas(palabras, plegadas, estilo), "muletillas")
    if cortes["tomas_repetidas"]:
        marcar(_tomas_repetidas(palabras, plegadas, fuera, cortes["similitud_toma"]),
               "tomas repetidas")
    marcar(_tartamudeos(palabras, plegadas, fuera), "repeticiones")

    # Si lo que queda empieza con un saludo (p. ej. tras quitar un "eh"), también va.
    vivos = [i for i in range(len(palabras)) if i not in fuera]
    n_saludo = _saludo([plegadas[i] for i in vivos], gancho_conf["saludos_a_recortar"])
    marcar(vivos[:n_saludo], "saludo")
    vivos = [i for i in range(len(palabras)) if i not in fuera]
    if not vivos:
        raise ValueError("Después de los cortes no queda ninguna palabra")

    for i, motivo in fuera.items():
        quitado[motivo] = quitado.get(motivo, 0) + palabras[i]["end"] - palabras[i]["start"]

    # Entre dos palabras que se quedan, todo lo que sobre de `silencio_maximo`
    # se va y queda una pausa natural: más margen después de la palabra (Whisper
    # suele marcar el final antes de que se apague la última consonante) que
    # antes de la siguiente.
    quitar = []
    pausa = cortes["pausa_que_queda"]
    despues, antes = pausa * 0.6, pausa * 0.4
    maximo = cortes["silencio_maximo"]
    primero, ultimo = palabras[vivos[0]], palabras[vivos[-1]]
    quitar.append((0.0, max(0.0, _empieza(primero["start"], silencios) - antes)))
    quitar.append((_termina(ultimo["end"], silencios) + 0.3, total))
    for a, b in zip(vivos, vivos[1:]):
        hueco = palabras[b]["start"] - palabras[a]["end"]
        if hueco > maximo or b != a + 1:
            s = _termina(palabras[a]["end"], silencios) + despues
            e = _empieza(palabras[b]["start"], silencios) - antes
            if e - s > 0.04:
                quitar.append((s, e))
    # Silencios medidos en el audio: atrapan pausas que Whisper pegó a una palabra.
    for s, e in silencios:
        if e - s > maximo + pausa:
            quitar.append((s + despues, e - antes))
    rangos = _invertir(_unir(quitar), total)

    duracion_final = sum(e - s for s, e in rangos)
    quitado["silencios"] = total - duracion_final - sum(quitado.values())
    avisos = []
    tope = formato["duracion_maxima"]
    if duracion_final > tope:
        rangos, recorte = _recortar(rangos, palabras, vivos, tope)
        avisos.append(f"Duraba {duracion_final:.1f}s después de los cortes; se recortó a "
                      f"{recorte:.1f}s (máximo {tope}s). Revisar el final.")
        quitado["recorte por duración"] = duracion_final - recorte
        duracion_final = recorte
    lo, hi = formato["duracion_ideal"]
    if duracion_final < lo:
        avisos.append(f"Dura {duracion_final:.1f}s, menos que el ideal de {lo}-{hi}s.")
    elif duracion_final > hi:
        avisos.append(f"Dura {duracion_final:.1f}s, más que el ideal de {lo}-{hi}s.")

    minimo, maximo_ritmo = estilo["ritmo"]["cambio_cada"]
    zooms = estilo["ritmo"]["zooms"]
    tramos, cursor = [], 0.0
    for k, (s, e) in enumerate(_partir(rangos, [palabras[i] for i in vivos],
                                       minimo, maximo_ritmo)):
        tramos.append(Tramo(round(s, 3), round(e, 3), zooms[k % len(zooms)], round(cursor, 3)))
        cursor += e - s

    salida = []
    for i in vivos:
        w = palabras[i]
        tiempos = _mapear(w["start"], w["end"], tramos)
        if tiempos:
            salida.append({"text": w["text"], "start": tiempos[0], "end": tiempos[1]})

    gancho, gancho_fin = _gancho(salida, gancho_conf)
    frases = [" ".join(salida[k]["text"] for k in range(i, j)) for i, j in _frases(salida)]
    return Plan(tramos, salida, gancho, gancho_fin, round(total, 2), round(duracion_final, 2),
                {k: round(v, 1) for k, v in quitado.items()}, avisos, frases)


def _recortar(rangos, palabras, vivos, tope):
    """Corta en el último final de frase que quepa en `tope` segundos."""
    acumulado, mapa = 0.0, []
    for s, e in rangos:
        mapa.append((s, e, acumulado))
        acumulado += e - s

    def salida(t):
        for s, e, base in mapa:
            if s <= t <= e:
                return base + t - s
        return None

    candidatos = []
    for pos, i in enumerate(vivos):
        w = palabras[i]
        t = salida(w["end"])
        if t is None or t + 0.15 > tope:
            continue
        siguiente = palabras[vivos[pos + 1]] if pos + 1 < len(vivos) else None
        fin_frase = FIN_FRASE.search(w["text"]) or siguiente is None \
            or siguiente["start"] - w["end"] >= 0.4
        candidatos.append((bool(fin_frase), t, w["end"]))
    frase = [c for c in candidatos if c[0]]
    elegido = (frase or candidatos)[-1]
    # Un respiro después de la última palabra, sin llegar a la siguiente.
    siguiente = [palabras[i]["start"] for i in vivos if palabras[i]["start"] >= elegido[2]]
    limite = min([elegido[2] + 0.15] + [t - 0.02 for t in siguiente[:1]])
    nuevos = [(s, min(e, limite)) for s, e in rangos if s < limite]
    return nuevos, sum(e - s for s, e in nuevos)


def _gancho(salida, conf):
    """La primera frase dicha, de `palabras_min` a `palabras_max` palabras."""
    lo, hi = conf["palabras_min"], conf["palabras_max"]
    frases = _frases(salida)
    if not frases:
        return "", conf["duracion"]
    fin = frases[0][1]
    k = 1
    while fin < lo and k < len(frases):
        fin = frases[k][1]
        k += 1
    fin = min(fin, len(salida))
    truncado = fin > hi
    if truncado:
        # Que no termine en "a", "de", "cómo"...: se recorta hasta una palabra con peso.
        fin = hi
        while fin > lo and plegar(salida[fin - 1]["text"]) in DEBILES:
            fin -= 1
    palabras = salida[:fin]
    texto = " ".join(w["text"] for w in palabras)
    texto = re.sub(r"[,;:]+$", "", texto.strip())
    if truncado:
        texto = texto.rstrip(".") + "…"
    if conf["mayusculas"]:
        texto = texto.upper()
    return texto, palabras[-1]["end"] if palabras else conf["duracion"]
