"""Recorte inteligente a 9:16: sigue la cara de Luis.

Lee el video a 2 cuadros por segundo en baja resolución, detecta la cara más
grande en cada uno y, para cada tramo, centra la ventana 9:16 en la mediana
de esas posiciones. Dentro de un tramo la ventana no se mueve (nada de
temblores); si la cara se movió poco entre tramos, se queda donde estaba.
Sin cara, centra.
"""
import statistics
import subprocess

ANCHO_ANALISIS = 480
CUADROS_POR_SEG = 2


def rastrear_caras(video, ancho, alto):
    """[(segundo, cx, cy)] con cx, cy de 0 a 1."""
    import cv2
    import numpy as np

    alto_a = int(round(ANCHO_ANALISIS * alto / ancho / 2)) * 2
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf",
         f"fps={CUADROS_POR_SEG},scale={ANCHO_ANALISIS}:{alto_a}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    tam = ANCHO_ANALISIS * alto_a
    caras, n = [], 0
    while True:
        datos = proc.stdout.read(tam)
        if len(datos) < tam:
            break
        gris = np.frombuffer(datos, np.uint8).reshape(alto_a, ANCHO_ANALISIS)
        encontradas = detector.detectMultiScale(gris, scaleFactor=1.1, minNeighbors=5,
                                                minSize=(28, 28))
        if len(encontradas):
            x, y, w, h = max(encontradas, key=lambda r: r[2] * r[3])
            caras.append((n / CUADROS_POR_SEG, (x + w / 2) / ANCHO_ANALISIS,
                          (y + h / 2) / alto_a))
        n += 1
    proc.wait()
    return caras


def ventanas(tramos, caras, ancho, alto, salida_ancho, salida_alto):
    """Un recorte (w, h, x, y) en píxeles del original para cada tramo."""
    proporcion = salida_ancho / salida_alto
    if ancho / alto > proporcion:
        base_h, base_w = alto, alto * proporcion
    else:
        base_w, base_h = ancho, ancho / proporcion
    todas_x = [c[1] for c in caras]
    todas_y = [c[2] for c in caras]
    global_x = statistics.median(todas_x) if todas_x else 0.5
    global_y = statistics.median(todas_y) if todas_y else 0.42
    recortes, previo = [], None
    for tramo in tramos:
        dentro = [c for c in caras if tramo.inicio - 0.5 <= c[0] <= tramo.fin + 0.5]
        cx = statistics.median([c[1] for c in dentro]) if dentro else global_x
        cy = statistics.median([c[2] for c in dentro]) if dentro else global_y
        if previo and abs(cx - previo[0]) < 0.06 and abs(cy - previo[1]) < 0.06:
            cx, cy = previo
        previo = (cx, cy)
        w, h = base_w / tramo.zoom, base_h / tramo.zoom
        w, h = int(w) // 2 * 2, int(h) // 2 * 2
        # La cara un poco arriba del centro: deja aire para los subtítulos.
        x = min(max(cx * ancho - w / 2, 0), ancho - w)
        y = min(max(cy * alto - h * 0.40, 0), alto - h)
        recortes.append((w, h, int(x) // 2 * 2, int(y) // 2 * 2))
    return recortes
