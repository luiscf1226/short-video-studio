# Guía de llaves: YouTube, Drive, Buffer y videos de la app

Esta guía es para conectar todo el flujo de videos: los de la app que se hacen
solos, Google Drive, Buffer y YouTube. No hace falta programar: solo hacer
clic, copiar y pegar. Toma unos **15 minutos**. La auditoría de YouTube
(paso 6) es aparte y Google tarda días.

**Regla de oro:** las llaves solo se pegan en GitHub, en el environment
**`videos`** del repo **short-video-studio**. Nunca en un chat, un correo, un
documento ni en el código. Si una llave se pega en otro lado por error, hay
que borrarla y sacar otra.

Todo vive en un solo repo (short-video-studio). El repo de la app
(bible-ai-honduras) **no** necesita llaves para esto.

Ten abiertas dos pestañas: esta guía y la de GitHub del paso 1.

---

## Paso 1. Crear el environment `videos` en GitHub (1 minuto)

1. Abre https://github.com/luiscf1226/short-video-studio/settings/environments
2. Clic en **New environment**, escribe `videos` y clic en **Configure environment**.
3. Deja esa pestaña abierta. Cada vez que esta guía diga **«guárdalo en GitHub»**:
   en esa página, dentro de **Environment secrets**, clic en **Add environment
   secret**, escribe el **nombre exacto** (está en la tabla del final) y pega el
   valor. Luego **Add secret**.

4. Recomendado: en **Deployment branches and tags**, elige **Selected branches**
   y agrega `main`. Así solo el código ya revisado puede usar las llaves.

---

## Paso 2. Proyecto de Google Cloud (2 minutos)

Entra siempre con **la cuenta de Google de Luis**: la del canal de YouTube y la
dueña de la carpeta «Videos del domingo».

1. Crea el proyecto: https://console.cloud.google.com/projectcreate
   - Nombre: `videos-luis`. Clic en **Crear**. No pide tarjeta.
   - Arriba a la izquierda, verifica que esté elegido `videos-luis`.
2. Activa las dos APIs (en cada link, clic en **Habilitar**):
   - YouTube: https://console.cloud.google.com/apis/library/youtube.googleapis.com
   - Drive: https://console.cloud.google.com/apis/library/drive.googleapis.com

---

## Paso 3. Pantalla de consentimiento (2 minutos)

Es la pantalla que Google muestra cuando Luis da permiso.

1. **Branding:** https://console.cloud.google.com/auth/branding
   - Si dice **Get started**, clic ahí.
   - Nombre de la app: `Videos de Luis`. Correo de soporte: el de Luis.
   - Audiencia: **External**. Correo de contacto: el de Luis.
   - Acepta y clic en **Create**.
2. **Permisos (Data Access):** https://console.cloud.google.com/auth/scopes
   - Clic en **Add or remove scopes**. Abajo, en **Manually add scopes**, pega
     estas 3 líneas:
     ```
     https://www.googleapis.com/auth/youtube.upload
     https://www.googleapis.com/auth/youtube.readonly
     https://www.googleapis.com/auth/drive
     ```
   - Clic en **Add to table**, luego **Update** y luego **Save**.
3. **Que el token no caduque a los 7 días:** https://console.cloud.google.com/auth/audience
   - Clic en **Publish app** y confirma. Tiene que decir **In production**.
   - Si se queda en **Testing**, Google apaga el permiso cada 7 días y la
     publicación deja de funcionar sola. No hace falta pedir la verificación
     de Google: es una app de uso personal (menos de 100 usuarios).

---

## Paso 4. Client ID, client secret y refresh token de YouTube (3 minutos)

### 4a. Client ID y client secret

1. Abre https://console.cloud.google.com/auth/clients y clic en **Create client**.
2. Tipo de aplicación: **Web application**. Nombre: `Videos de Luis`.
3. En **Authorized redirect URIs**, clic en **Add URI** y pega exactamente:
   `https://developers.google.com/oauthplayground`
4. Clic en **Create**. Aparecen el **Client ID** y el **Client secret**.
5. Guárdalos en GitHub (environment `videos`):
   - `GOOGLE_OAUTH_CLIENT_ID` = el Client ID
   - `GOOGLE_OAUTH_CLIENT_SECRET` = el Client secret

### 4b. Refresh token para la publicación diaria

1. Abre https://developers.google.com/oauthplayground
2. Arriba a la derecha, clic en el engranaje ⚙️:
   - Marca **Use your own OAuth credentials**.
   - Pega el Client ID y el Client secret. Cierra el engranaje.
3. A la izquierda, en la cajita **Input your own scopes**, pega esta línea
   completa:
   ```
   https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/drive
   ```
4. Clic en **Authorize APIs** y entra con la cuenta de Luis.
   - Google avisa **«Google no verificó esta app»**. Es normal: la app es de Luis.
     Clic en **Avanzado** y luego en **Ir a Videos de Luis**.
   - **Marca todas las casillas** y clic en **Continuar**.
5. Clic en **Exchange authorization code for tokens**.
6. Copia el **Refresh token** y guárdalo en GitHub como
   `GOOGLE_OAUTH_REFRESH_TOKEN`.

Es un solo token para todo: subir los Shorts, guardar los editados y subir los
videos de la app a Drive.

**¿Cuándo deja de servir el token?** Si la app vuelve a **Testing**, si pasan 6
meses sin usarlo (la corrida diaria lo usa), si Luis quita el acceso o si cambia
la contraseña de Google. En esos casos, repite 4b y reemplaza el secreto.

---

## Paso 5. Acceso a la carpeta «Videos del domingo» (2 minutos)

La publicación lee los videos con una **cuenta de servicio**: un usuario robot
que solo puede **ver** la carpeta. Para guardar los editados en «Editados» usa
el permiso de Luis del paso 4b.

1. Abre https://console.cloud.google.com/iam-admin/serviceaccounts (proyecto
   `videos-luis`) y clic en **Crear cuenta de servicio**.
   - Nombre: `lector-videos`. Clic en **Crear y continuar** y luego en **Listo**.
     No necesita roles.
2. Clic en la cuenta nueva → pestaña **Claves** → **Agregar clave** → **Crear
   clave nueva** → **JSON** → **Crear**. Se descarga un archivo `.json`.
3. Abre ese archivo con el Bloc de notas (o TextEdit), copia **todo** el
   contenido, de la primera `{` a la última `}`, y guárdalo en GitHub como
   `GOOGLE_SERVICE_ACCOUNT_JSON`.
4. **Borra el archivo** de Descargas y vacía la papelera.
5. Copia el correo de la cuenta de servicio (termina en
   `@videos-luis.iam.gserviceaccount.com`; aparece en la lista del paso 1).
6. Abre la carpeta «Videos del domingo»:
   https://drive.google.com/drive/folders/1kK0XBp3EnNyqOWjHrXoPp_liVE7900fy
   - Clic en el nombre de la carpeta → **Compartir**.
   - Pega el correo de la cuenta de servicio. Elige **Lector**.
   - Desmarca **Notificar** y clic en **Compartir**.

**Videos de la app:** no hay que hacer nada más. El workflow «Videos de la
app» crea la carpeta «Bible AI · videos para publicar» **dentro** de «Videos
del domingo», así que la cuenta de servicio ya la ve.

---

## Paso 6. La auditoría de YouTube (los videos quedan privados)

YouTube **bloquea como privados** los videos que se suben por la API desde un
proyecto que **no pasó su auditoría**. Esto pasa aunque el proyecto esté en
producción y aunque el video tenga fecha de publicación.

- **Mientras tanto:** la publicación sube cada Short como **privado** con su
  fecha. Si en YouTube Studio (https://studio.youtube.com → Contenido) aparece
  **«Bloqueado como privado»**, Luis lo cambia a **Público** a mano. Es un clic
  al día y nada sale sin que Luis lo vea.
- **Para quitar el bloqueo:** llena el formulario gratis de auditoría
  (*YouTube API Services – Audit and Quota Extension Form*):
  https://support.google.com/youtube/contact/yt_api_form
  - Indica que es para el canal propio de Luis, con 1 subida al día, y que el
    proyecto es `videos-luis`.
  - Google responde por correo en días o semanas.
- **Cómo saber si ya pasó:** después de la aprobación, un video subido en modo
  borrador ya no dice «Bloqueado como privado».

---

## Paso 7. Token de Buffer (1 minuto)

1. Entra a Buffer con la cuenta de Luis y abre
   https://publish.buffer.com/settings/api
   (o tu foto, arriba a la derecha → **Settings** → **API**).
2. Clic en **Create API key** (o **Generate**). El plan gratis permite 1 llave.
3. Copia la llave y guárdala en GitHub como `BUFFER_API_KEY`.
4. En Buffer, revisa que TikTok, Instagram y LinkedIn estén conectados. Cada
   canal necesita al menos un horario en **Settings → Posting Schedule**, antes
   de las 21:00. Instagram tiene que ser una cuenta de **empresa o creador**.

---

## Paso 8. Llaves de los videos de la app (2 minutos)

Los videos de la app se hacen solos cada domingo con la app real. Necesitan
dos llaves que ya se usaban para los videos semanales:

1. **ElevenLabs (las voces):** entra a https://elevenlabs.io/app/settings/api-keys
   → **Create API Key** → nombre `videos` → **Create**. Copia la llave y
   guárdala en GitHub como `ELEVENLABS_API_KEY`.
2. **Convex (las respuestas reales de la app):** entra a
   https://dashboard.convex.dev → proyecto de Bible AI → deployment de
   producción (`neighborly-kudu-508`) → **Settings** → **Generate Production
   Deploy Key**. Guárdala en GitHub como `CONVEX_DEPLOY_KEY`. Si ya existe una
   para `deploy-convex.yml` en bible-ai-honduras, puede ser la misma.
3. **Correo (opcional):** si Luis quiere recibir también la semana por Gmail,
   saca una contraseña de aplicación en https://myaccount.google.com/apppasswords
   y guarda `CORREO_USUARIO` (el Gmail), `CORREO_CLAVE` (la contraseña de
   aplicación) y `CORREO_PARA` (a quién le llega). Sin estos tres, los videos
   igual llegan a Drive.

---

## Tabla final de secrets

**Repo `luiscf1226/short-video-studio` → environment `videos`** (el único)

| Nombre exacto | Tipo | Qué es | Paso |
|---|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Secret | Todo el archivo JSON de la cuenta de servicio | 5 |
| `GOOGLE_OAUTH_CLIENT_ID` | Secret | Client ID | 4a |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Secret | Client secret | 4a |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | Secret | Refresh token de YouTube + Drive | 4b |
| `BUFFER_API_KEY` | Secret | Llave de la API de Buffer | 7 |
| `ELEVENLABS_API_KEY` | Secret | Voces de los videos de la app | 8 |
| `CONVEX_DEPLOY_KEY` | Secret | Respuestas reales de la app | 8 |
| `CORREO_USUARIO`, `CORREO_CLAVE`, `CORREO_PARA` | Secrets, **opcionales** | Mandar la semana por Gmail | 8 |
| `MODO_AUTOMATICO` | **Variable** (pestaña *Environment variables*, no Secrets) | `dry_run` al principio; `borrador` para probar; `programar` solo con el OK de Luis | — |

En bible-ai-honduras no hace falta ningún secret para esto. Si ya se habían
puesto `GOOGLE_OAUTH_*` en su environment `videos`, se pueden borrar.

---

## Paso 9. Probar que quedó bien (dry-run de Actions, 5 minutos)

El dry-run edita y muestra lo que programaría, **sin publicar nada** en ninguna
red. Además prueba cada llave **solo leyendo**.

1. Abre https://github.com/luiscf1226/short-video-studio/actions/workflows/publicacion-diaria.yml
2. Clic en **Run workflow**. Deja marcado **dry_run** y clic en el botón verde
   **Run workflow**.
3. Espera unos minutos y abre la corrida. En **Summary** aparece la tabla
   **«Prueba de llaves (solo lectura)»**:
   - ✅ en todas las filas: listo.
   - ❌ en alguna: la fila dice qué falta. La guía de problemas está abajo.
4. En la misma página está el resumen del dry-run: qué video saldría mañana en
   cada red y la proyección de 7 días.
5. Prueba también los videos de la app:
   https://github.com/luiscf1226/short-video-studio/actions/workflows/videos-app.yml
   → **Run workflow** con **dry_run** marcado. Tarda unos 30 minutos. Al final,
   en **Artifacts**, está `videos-app-…` con los 7 videos para verlos. No sube
   nada a Drive ni manda correo.

> El botón **Run workflow** aparece después de mergear el PR a `main`.
> La prueba de llaves todavía no revisa ElevenLabs ni Convex: si fallan, el
> dry-run de «Videos de la app» lo dice en rojo.

**Siguiente paso, con Luis:** correr con `dry_run` desmarcado y `borrador`
marcado. Así quedan borradores en Buffer y un Short privado sin fecha en
YouTube, para revisarlos. Solo cuando Luis dé el OK, la variable
`MODO_AUTOMATICO` pasa a `programar`.

### Si algo sale en ❌

| Dice | Qué hacer |
|---|---|
| `falta el secreto` | El nombre en GitHub no es exacto o está en otro environment. Revisa la tabla. |
| `el JSON no es válido` | Pega de nuevo **todo** el archivo de la cuenta de servicio (paso 5.3). |
| `no la ve (¿está compartida…?)` | Comparte la carpeta como **Lector** con el correo que aparece en la fila (paso 5.6). |
| `refresh token caducó o fue revocado` | La app está en Testing o se quitó el acceso. Revisa el paso 3.3 y repite el 4b. |
| `faltan youtube.upload` o `faltan drive` | En el paso 4b no se marcaron todas las casillas. Repite el 4b. |
| `la cuenta autorizada no tiene canal` | Se autorizó con otra cuenta de Google. Repite el 4b con la del canal. |
| `Buffer HTTP 401` | La llave de Buffer está mal copiada o fue borrada. Repite el paso 7. |
| `el canal está desconectado` o `la cola del canal está en pausa` | Reconecta el canal en Buffer o quita la pausa. |
| `no se pudo crear la clave` (paso 5.2) | La cuenta tiene una política que bloquea las claves. Pasa con cuentas de empresa: usa la cuenta personal de Luis. |

---

<details>
<summary>Para quien programa: sacar el token desde la terminal</summary>

En vez del Playground, `scripts/sacar_refresh_token.py` saca el token y lo
guarda con `gh secret set`, sin mostrarlo. Necesita un cliente OAuth de tipo
**Desktop app** (no Web) y `gh auth login`:

```bash
python3 scripts/sacar_refresh_token.py ~/Descargas/client_secret_XXXX.json
python -m pipeline llaves   # la misma prueba de llaves, con los secretos en variables de entorno
```
</details>
