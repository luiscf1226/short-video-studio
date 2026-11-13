"""Decisiones de corte sobre una transcripción sintética, con config/estilo.yaml."""
from pipeline.config import cargar_estilo
from pipeline.edicion.cortes import planear

ESTILO = cargar_estilo()


def guion(*partes):
    """("texto", pausa_despues) -> palabras con tiempos, 0.3 s por palabra."""
    palabras, t = [], 1.0               # arranca con 1 s de silencio
    for texto, pausa in partes:
        for w in texto.split():
            palabras.append({"text": w, "start": round(t, 3), "end": round(t + 0.3, 3)})
            t += 0.32
        t += pausa
    return palabras, t + 1.5


def dichas(plan):
    return " ".join(w["text"] for w in plan.palabras)


def test_quita_saludo_silencio_muletillas_y_toma_repetida():
    palabras, total = guion(
        ("Hola a todos.", 1.0),
        ("Hoy les voy a", 0.9),
        ("Hoy les voy a mostrar este video increíble.", 1.5),
        ("Eh,", 0.6),
        ("este", 0.5),
        ("el truco es grabar una vez.", 2.0),
        ("O sea, no repetir nada.", 0.1),
    )
    plan = planear(palabras, [], total, ESTILO)
    assert dichas(plan) == ("Hoy les voy a mostrar este video increíble. el truco es grabar "
                            "una vez. no repetir nada.")
    # "este video" se queda; el "este" suelto entre pausas se va.
    assert set(plan.quitado) >= {"saludo", "muletillas", "tomas repetidas", "silencios"}
    # El video empieza con la primera frase, sin silencio ni saludo.
    assert plan.palabras[0]["start"] < 0.1
    # Ninguna pausa que quede supera el máximo de la config.
    for a, b in zip(plan.palabras, plan.palabras[1:]):
        assert b["start"] - a["end"] <= ESTILO["cortes"]["silencio_maximo"] + 1e-6


def test_gancho_de_5_a_8_palabras():
    palabras, total = guion(("Hoy les voy a enseñar cómo publicar todos los días.", 0.5),
                            ("Sin laptop.", 0.5))
    plan = planear(palabras, [], total, ESTILO)
    assert plan.gancho == "HOY LES VOY A ENSEÑAR CÓMO PUBLICAR…"
    corto, total = guion(("Mira esto.", 0.5), ("Es muy fácil de hacer.", 0.5))
    assert planear(corto, [], total, ESTILO).gancho == "MIRA ESTO. ES MUY FÁCIL DE HACER."


def test_silencio_medido_dentro_de_una_palabra_tambien_se_corta():
    palabras, total = guion(("Una frase larga que dura un rato.", 0.2))
    palabras[2]["end"] += 2.0           # Whisper estiró la palabra sobre un silencio
    for w in palabras[3:]:
        w["start"] += 2.0
        w["end"] += 2.0
    silencio = (palabras[2]["start"] + 0.3, palabras[2]["end"])
    plan = planear(palabras, [silencio], total + 2.0, ESTILO)
    assert plan.duracion_final < 4.5


def test_tope_de_60_segundos_corta_en_final_de_frase_y_avisa():
    frases = [(f"Punto {i}: esta idea sirve para el video.", 0.2) for i in range(30)]
    palabras, total = guion(*frases)
    plan = planear(palabras, [], total, ESTILO)
    assert plan.duracion_final <= 60
    assert dichas(plan).endswith("video.")
    assert any("recortó" in a for a in plan.avisos)


def test_frases_casi_iguales_seguidas_son_una_toma_repetida():
    palabras, total = guion(("Esto se publica solo cada día.", 0.8),
                            ("Esto se publica solo todos los días.", 0.5))
    plan = planear(palabras, [], total, ESTILO)
    assert dichas(plan) == "Esto se publica solo todos los días."


def test_ritmo_cambio_cada_3_a_5_segundos_con_zoom_alterno():
    palabras, total = guion(*[("uno dos tres cuatro cinco seis siete ocho nueve diez", 0.1)] * 4)
    plan = planear(palabras, [], total, ESTILO)
    lo, hi = ESTILO["ritmo"]["cambio_cada"]
    for tramo in plan.tramos[:-1]:
        assert lo - 0.2 <= tramo.duracion <= hi + 0.2, tramo
    zooms = [t.zoom for t in plan.tramos]
    assert all(a != b for a, b in zip(zooms, zooms[1:]))
