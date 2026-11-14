# Publicación diaria sin laptop

Luis graba y sube el video crudo a la carpeta de Drive **Videos del domingo**.
Cada noche, el workflow [`publicacion-diaria.yml`](../.github/workflows/publicacion-diaria.yml)
hace esto:

1. **Detecta** los videos nuevos de esa carpeta con una cuenta de servicio de
   solo lectura. Lo ya procesado queda en `estado.json`, en la rama `estado`, así
   que nada se edita ni se programa dos veces.
2. **Edita** cada video (`pipeline/edicion/`):
   - recorta el silencio inicial, un "hola" o un saludo, las muletillas y las
     tomas repetidas (se queda con la última);
   - acorta toda pausa de más de 0,35 s;
   - hace un corte o un zoom suave cada 3 a 5 s;
   - encuadra en 9:16 (1080×1920) siguiendo la cara;
   - pone arriba, durante los primeros segundos, la primera frase como gancho;
   - quema subtítulos en español con la palabra clave en color;
   - cierra con "Sígueme para más";
   - recorta a 60 s como máximo y avisa.
3. **Guarda** el MP4 en la subcarpeta **Editados** y le da un enlace público de
   descarga directa para Buffer.
4. **Programa solo el día siguiente**: TikTok, Instagram y LinkedIn van a la cola
   de horarios de Buffer (plan gratis). YouTube Shorts se sube directo con la
   YouTube Data API, privado y con `publishAt`.
5. Escribe un **resumen** en la pestaña de la corrida y lo sube con los MP4 como
   artifact, disponible 7 días.

## Calendario y estilo

Los dos archivos de configuración ya tienen los valores definitivos:

- [`config/calendario.yaml`](../config/calendario.yaml) define el reparto por día:
  - TikTok, Reels y Shorts: lunes, miércoles y viernes son de Luis; martes,
    jueves, sábado y domingo, de una app;
  - LinkedIn: lunes, miércoles y viernes, solo con videos de Luis;
  - si un día de Luis no hay video suyo, sale uno de app; si no hay ninguno, ese
    día no sale nada;
  - un video nunca se repite en la misma red.

  También están ahí los ids de los canales de Buffer, las apps y su CTA (Bible
  AI: "Descarga la app") y los límites de los textos.
- [`config/estilo.yaml`](../config/estilo.yaml) lo llena Marca: fuente, colores,
  posición de subtítulos, gancho, cierre, cortes y música (ninguna por defecto).

## Textos (Marca)

Los textos de las publicaciones salen de `textos/semana-NN.json`. Ver el modelo
en [`textos/_ejemplo.json`](../textos/_ejemplo.json). Cada entrada lleva estos
campos:

- `video`: el nombre del archivo en Drive, sin `.mp4`;
- `red`: `tiktok`, `instagram`, `youtube` o `linkedin`;
- `texto`;
- `hashtags`.

Si un video no tiene texto válido para una red, **no se programa en esa red** y
el resumen de la corrida lo lista. El texto que genera el pipeline es solo una
sugerencia en el resumen y nunca se publica.

| Red | Texto | Hashtags |
|---|---|---|
| TikTok, Instagram | 1 o 2 líneas | 3 a 5 |
| YouTube Shorts | título de una línea, menos de 100 caracteres (`#Shorts` va en la descripción) | 0 a 5 |
| LinkedIn | 3 a 5 líneas | 0 a 3 |

Los videos de apps y los textos que nombran una app no pueden mencionar tiendas
(App Store, Play Store, Google Play), sus enlaces ni precio (gratis, $, lempiras).
Un texto que los mencione se rechaza.

## Orden de prueba: nada sale solo sin el OK de Luis

| Paso | Cómo | Qué hace |
|---|---|---|
| 1. Dry-run | Actions → Publicación diaria → Run workflow (dry_run marcado, viene así) | Detecta y edita los videos y lista lo que programaría mañana más una proyección de 7 días. No toca Buffer, YouTube ni Drive, y no guarda estado. Los MP4 quedan en el artifact. |
| 2. Borrador | Run workflow con dry_run desmarcado y borrador marcado | Sube a Editados, crea **borradores** en Buffer (no cuentan para el límite ni se publican) y sube a YouTube como **privado sin fecha**. Luis revisa todo. |
| 3. Automático | Luis da el OK → environment `videos` → variable `MODO_AUTOMATICO` = `programar` | El cron de cada noche programa el día siguiente en la cola de Buffer y con `publishAt` en YouTube. |

Mientras `MODO_AUTOMATICO` no exista (o diga `dry_run`), el cron solo hace
dry-run. Con `borrador`, el cron hace borradores. Un borrador de prueba no cuenta
como publicado: ese video se puede programar después.

### Garantías

- **Límite de Buffer gratis:** antes de crear cada publicación, el workflow cuenta
  las programadas del canal. Si la nueva dejaría la cola por encima de 10, no la
  crea y avisa.
- **Solo mañana:** antes de crear, calcula con los horarios del canal dónde
  caería `addToQueue` (el próximo horario libre). Si no cae mañana, no la crea y
  avisa, en vez de dejarla en otro día.
- **Idempotente:** `estado.json` registra cada publicación por día y red. Si el
  estado se perdiera, el workflow también busca en Buffer una publicación pendiente
  con el mismo texto. En YouTube busca el video por una etiqueta propia
  (`ssv-<video>`). Correrlo dos veces no duplica nada.
- **Sin estado, no sigue:** si la rama `estado` no se puede leer (red o permisos),
  la corrida falla en vez de empezar de cero y reprogramar lo que ya salió.
- **`concurrency`:** nunca corren dos a la vez.

### Horarios de la cola de Buffer

El workflow corre a las 21:00 de Honduras y pide `addToQueue`. Para que lo que
entra caiga mañana, cada canal necesita su horario configurado en Buffer
(Settings → Posting Schedule):

- TikTok e Instagram: un horario por día, antes de las 21:00 (por ejemplo, 12:00);
- LinkedIn: lunes, miércoles y viernes.

Si el próximo horario libre no cae mañana (por ejemplo, porque Luis programó
algo a mano para ese horario), ese día no se programa y el resumen lo dice.

## Lo que Luis tiene que crear

### Environment y secretos (GitHub)

Ir al repo `luiscf1226/short-video-studio` → Settings → Environments → New
environment → `videos`. Ahí se cargan estos secretos y variables:

| Nombre | Tipo | De dónde sale |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | secreto | El JSON de la llave de la cuenta de servicio (ver abajo), pegado entero |
| `GOOGLE_OAUTH_CLIENT_ID` | secreto | El cliente OAuth "App de escritorio"; lo guarda `scripts/sacar_refresh_token.py` |
| `GOOGLE_OAUTH_CLIENT_SECRET` | secreto | El mismo cliente; lo guarda el script |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | secreto | El script, sin mostrarlo en pantalla |
| `BUFFER_API_KEY` | secreto | https://publish.buffer.com/settings/api → crear llave (el plan gratis permite 1) |
| `MODO_AUTOMATICO` | variable | `dry_run` al principio, `borrador` para probar y `programar` con el OK de Luis |
| `OPENAI_API_KEY` | secreto, opcional | Solo si `transcripcion.proveedor: openai` |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | secretos, opcionales | Solo si `url_publica.proveedor: s3` (por ejemplo, Cloudflare R2 → R2 → Manage API tokens) |

Además, en `config/calendario.yaml` va `apps[bible-ai].carpeta_drive`: el id de
la carpeta de Drive donde bible-ai-honduras deja sus videos. Ver
[Videos de apps](#videos-de-apps).

### Cuenta de servicio (lectura de Drive)

1. Entrar a https://console.cloud.google.com y crear un proyecto, por ejemplo
   `videos-luis`. No necesita facturación.
2. Ir a APIs y servicios → Biblioteca y habilitar **Google Drive API**.
3. Ir a IAM y administración → Cuentas de servicio → Crear cuenta de servicio
   (por ejemplo, `lector-videos`). No necesita roles.
4. En la cuenta → Claves → Agregar clave → JSON. Se descarga el archivo; su
   contenido completo va en `GOOGLE_SERVICE_ACCOUNT_JSON`. Después, borrar el
   archivo de la computadora.
5. En Drive, compartir **Videos del domingo** y la carpeta **Bible AI · videos
   para publicar** con el correo de la cuenta de servicio
   (`...@...iam.gserviceaccount.com`) como **Lector**. La segunda la crea la
   primera corrida de bible-ai-honduras.

La cuenta de servicio no puede subir a Editados. Según la documentación de
Drive, las cuentas de servicio no tienen cuota de almacenamiento: "Service
accounts don't have storage quota and can't own files", y deben "use OAuth 2.0
to upload items on behalf of a human user". Por eso las escrituras usan el OAuth
de Luis.

### OAuth de Luis (YouTube y escritura en Drive)

Se hace una sola vez, en el mismo proyecto de Google Cloud:

1. **Activar las APIs.** Ir a APIs y servicios → Biblioteca y habilitar
   **YouTube Data API v3**. Drive ya quedó habilitada.
2. **Pantalla de consentimiento.** Ir a Google Auth Platform → Branding y poner
   nombre de la app (por ejemplo, "Videos de Luis"), correo de soporte y correo
   de contacto.
3. **Audience.** Elegir tipo de usuario **External**, y en Test users agregar la
   cuenta de Google de Luis (la del canal de YouTube).
4. **Data Access.** Agregar estos alcances:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube.readonly`
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/drive.file` (el token de bible-ai)
5. **Publicar la app.** Ir a Audience → **Publish app** → confirmar, hasta que
   diga **In production**. Este paso es el que evita que el token caduque a los 7
   días (ver punto a más abajo). No hace falta pedir verificación: es de uso
   personal.
6. **Cliente.** Ir a Google Auth Platform → Clients → Create client → tipo
   **Desktop app** → Create → **Download JSON**.
7. **Sacar el token y guardarlo.** En la computadora de Luis, con `gh auth login`
   hecho:

   ```bash
   python3 scripts/sacar_refresh_token.py ~/Descargas/client_secret_XXXX.json
   ```

   Se abre el navegador. Luis entra con la cuenta del canal. Google muestra "Google
   no verificó esta app" (es su propia app): Avanzado → Ir a Videos de Luis →
   marcar **todas** las casillas → Continuar. El script guarda
   `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` y
   `GOOGLE_OAUTH_REFRESH_TOKEN` en el environment `videos` con
   `gh secret set` por stdin. El token no se imprime ni queda en ningún archivo.
   Para el repo de bible-ai, que es público, se saca un token aparte con el
   permiso mínimo (`drive.file`: solo toca lo que su script crea):

   ```bash
   python3 scripts/sacar_refresh_token.py ~/Descargas/client_secret_XXXX.json \
       --solo-drive-file --repo luiscf1226/bible-ai-honduras --env videos
   ```

   Es el mismo cliente; cada corrida del script genera otro refresh token.
8. **Borrar el JSON.** Borrar el JSON del cliente de Descargas.

## Respuestas sobre YouTube (documentación leída el 13/11/2026)

**a) Testing y caducidad.** Si la app queda en "Testing", el refresh token
caduca a los 7 días. La documentación dice: "A Google Cloud Platform project with
an OAuth consent screen configured for an external user type and a publishing
status of 'Testing' is issued a refresh token expiring in 7 days"
([OAuth 2.0](https://developers.google.com/identity/protocols/oauth2#expiration)).
La excepción solo cubre nombre, correo y perfil, no YouTube ni Drive.

Para evitarlo, hay que pasar la app a **In production** (paso 5). Al usar
alcances sensibles sin verificar, Google muestra la advertencia de app no
verificada. Para uso personal (menos de 100 usuarios) no hace falta
verificación: "you and your limited number of users can continue using the app
without going through verification"
([cuándo no se necesita verificación](https://support.google.com/cloud/answer/13464323)).

El token también deja de servir en estos casos:
- 6 meses sin uso (el cron diario lo usa);
- si Luis revoca el acceso;
- si se pasa de 100 tokens por cliente.

Si pasa, la corrida falla con un mensaje claro y basta con volver a correr el
script.

**b) ¿Privado forzado sin auditoría?** Hay que contar con que sí. La regla de
YouTube (desde el 28/07/2020) dice que lo que se sube con `videos.insert` desde un
proyecto de Google Cloud **sin auditar** queda bloqueado como privado ("Locked as
private"), aunque se pida `publishAt`. Una revisión anterior leyó que la página
de [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert)
ya no lo dice, pero el 14/11/2026 no se pudo volver a abrir para confirmarlo, así
que la guía asume lo peor.

Qué hacer:
- **Mientras no haya auditoría:** el flujo sube el Short privado con su
  `publishAt`. Si YouTube Studio lo muestra como bloqueado, Luis lo cambia a
  **Público** a mano en Studio (un clic por día). Nada se publica solo.
- **Para quitar el bloqueo:** pedir la auditoría (gratis) en el formulario
  [YouTube API Services – Audit and Quota Extension](https://support.google.com/youtube/contact/yt_api_form).
  Tarda días o semanas. Ver `docs/guia-llaves.md`.

La prueba en borrador lo deja claro: si el video de prueba sale como "Bloqueado
como privado" en Studio, el proyecto todavía no está auditado.

**c) Cuota.** Por defecto, cada proyecto tiene "100 `videos.insert` calls, and
10,000 units per day combined for all other endpoints"
([costos de cuota](https://developers.google.com/youtube/v3/determine_quota_cost)).
La subida tiene su propio cupo: 100 al día, a 1 unidad cada una. Este flujo
gasta por día:

- 1 subida;
- unas 3 unidades de lecturas, para la búsqueda que evita duplicados;
- 50 unidades solo cuando reprograma un video ya subido en borrador.

Alcanza de sobra.

`publishAt` solo se acepta con `privacyStatus: private`, y así se sube. Fuente:
[recurso videos](https://developers.google.com/youtube/v3/docs/videos).

## Buffer: qué acepta video por la API

La API de Buffer está disponible en el plan gratis: 1 llave y 1.000 solicitudes
por canal al mes. Este flujo usa unas 3 por canal y día.

La documentación lista TikTok, Instagram, LinkedIn y YouTube como plataformas
soportadas. `createPost` acepta `assets: [{video: {url}}]`. No encontré ninguna
restricción de video por canal en las páginas de posts
([posts-and-scheduling](https://developers.buffer.com/guides/posts-and-scheduling.html),
[VideoAssetInput](https://developers.buffer.com/types/VideoAssetInput.html)).

Dos condiciones a confirmar en la prueba en borrador:

- **Instagram:** la cuenta `luiscf1226.ai` debe ser de **empresa o creador**. Buffer
  no publica en automático en perfiles personales
  ([precios, tabla de canales](https://buffer.com/pricing)). Se manda como Reel
  (`metadata.instagram.type: reel`).
- **URL del video:** Buffer no tiene endpoint de subida y dice que los enlaces
  "share" de Drive no sirven
  ([hosting-media](https://developers.buffer.com/guides/hosting-media.html)).
  Por eso no se usa el enlace "compartir": se usa la descarga directa
  `drive.usercontent.google.com/download?id=…`. Antes de programar, el workflow
  comprueba que esa URL entregue el MP4 sin sesión. Si Buffer igual la
  rechazara, se cambia `url_publica.proveedor` a `s3` con un bucket público (por
  ejemplo, Cloudflare R2, con 10 GB gratis, aunque pide registrar un medio de
  pago).

YouTube no pasa por Buffer: el plan gratis tiene 3 canales y ya están ocupados.

## Transcripción: por qué faster-whisper

La transcripción usa `faster-whisper` (modelo `small`) en el propio runner:

- **Costo:** USD 0. No necesita llave y el audio no sale de GitHub.
- **Velocidad:** en 2 núcleos edita 51 s de video crudo en unos 64 s.
- **Palabra por palabra:** da los tiempos de cada palabra, que es lo que
  necesitan los cortes y los subtítulos.
- **Muletillas:** recibe un prompt con muletillas para que no las borre de la
  transcripción.

La alternativa configurable es `whisper-1` de OpenAI, a USD 0,006 por minuto.
Con 13 videos de 2 minutos al mes serían unos USD 0,16, pero suma otra cuenta y
otra llave.

## Costo mensual estimado: USD 0

| Pieza | Uso | Costo |
|---|---|---|
| GitHub Actions (repo privado) | ~30 corridas de 3-4 min + ~13 ediciones de 2-3 min ≈ 150-200 min | 0: GitHub Free incluye USD 12 de cómputo al mes (= 2.000 min Linux a USD 0,006/min) ([facturación de Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)) |
| Artifacts y caché | MP4 de la semana por 7 días; modelo Whisper ~470 MB en caché | 0: GitHub Free incluye 500 MB de artifacts y 10 GB de caché |
| Buffer | 3 canales, ≤10 programadas por canal, API | 0: plan Free ([buffer.com/pricing](https://buffer.com/pricing)) |
| YouTube Data API | 1 subida al día | 0: cuota gratuita |
| Google Drive | ~13 videos editados al mes (~20 MB c/u) | 0: dentro de los 15 GB de la cuenta |
| Whisper | local | 0 (OpenAI sería ~USD 0,16) |

## Videos de apps

El workflow de bible-ai-honduras (PR #273) arma los 7 videos de la semana y los
manda por correo. El PR aparte en ese repo hace dos cosas:

- **Drive:** sube los videos a su carpeta **Bible AI · videos para publicar**,
  con nombres `bible-ai-<fecha>-<dia>-<id>.mp4`.
  - La fecha es el día para el que se hizo cada video. Este flujo la usa para
    sacarlo ese día; los de días de Luis solo entran como respaldo.
  - Los de tipo `instalar` no se suben: graban la página de descarga, que
    muestra la tienda y el precio.
- **Cierre:** cambia a "Descarga la app", sin precio ni tiendas.

Este flujo lee esa carpeta (`apps[bible-ai].carpeta_drive`). El `video` que va
en `textos/semana-NN.json` es el nombre del archivo sin `.mp4`.

Una cosa para decidir: el cierre de esos videos sigue mostrando el QR y la
dirección de la página de descarga propia
(`luiscf1226.github.io/bible-ai-honduras`). No es una tienda, pero esa página sí
muestra el botón del App Store y dice que la app es gratis.

## Correr en local

```bash
pip install -r requirements.txt          # y ffmpeg con libass
python -m pipeline editar crudo.mp4 --salida build/prueba
python -m pipeline correr --modo dry_run --videos-locales carpeta_con_mp4/ --fecha 2026-11-16
python -m pytest -q tests
```
