# Guía de llaves: YouTube, Drive y Buffer

Esta guía es para conectar la publicación diaria con YouTube, Google Drive y
Buffer. No hace falta programar: solo hacer clic, copiar y pegar. Toma unos
**10 minutos**. La auditoría de YouTube (paso 6) es aparte y Google tarda días.

**Regla de oro:** las llaves solo se pegan en GitHub, en el environment
**`videos`**. Nunca en un chat, un correo, un documento ni en el código. Si una
llave se pega en otro lado por error, hay que borrarla y sacar otra.

Ten abiertas dos pestañas: esta guía y la de GitHub del paso 1.

---

## Paso 1. Crear el environment `videos` en GitHub (1 minuto)

1. Abre https://github.com/luiscf1226/short-video-studio/settings/environments
2. Clic en **New environment**, escribe `videos` y clic en **Configure environment**.
3. Deja esa pestaña abierta. Cada vez que esta guía diga **«guárdalo en GitHub»**:
   en esa página, dentro de **Environment secrets**, clic en **Add environment
   secret**, escribe el **nombre exacto** (está en la tabla del final) y pega el
   valor. Luego **Add secret**.

Haz lo mismo en el repo de la app, que también usa un environment `videos`:
https://github.com/luiscf1226/bible-ai-honduras/settings/environments (si
`videos` ya existe, solo ábrelo).

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
     estas 4 líneas:
     ```
     https://www.googleapis.com/auth/youtube.upload
     https://www.googleapis.com/auth/youtube.readonly
     https://www.googleapis.com/auth/drive
     https://www.googleapis.com/auth/drive.file
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
5. Guárdalos en GitHub, en **los dos repos** (environment `videos`):
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
6. Copia el **Refresh token** y guárdalo en GitHub, **solo en
   short-video-studio**, como `GOOGLE_OAUTH_REFRESH_TOKEN`.

### 4c. Refresh token para la app (solo su carpeta)

El repo de la app es público, así que su token solo puede tocar los videos que
ese repo sube, nada más del Drive de Luis.

1. En el Playground, clic en **Step 1** otra vez. En la cajita pega solo:
   ```
   https://www.googleapis.com/auth/drive.file
   ```
2. **Authorize APIs** → la misma cuenta → marca todo → **Continuar**.
3. **Exchange authorization code for tokens**. En el cuadro de la derecha,
   revisa que la línea `"scope"` diga **solo** `.../auth/drive.file`. Si trae más
   permisos, quita el acceso en https://myaccount.google.com/permissions
   («Videos de Luis» → Quitar acceso) y repite 4b y 4c.
4. Copia el **Refresh token** y guárdalo en GitHub, **solo en
   bible-ai-honduras**, como `GOOGLE_OAUTH_REFRESH_TOKEN`.

> Cada repo tiene su propio refresh token. Los dos comparten el mismo Client ID
> y Client secret.

**¿Cuándo deja de servir el token?** Si la app vuelve a **Testing**, si pasan 6
meses sin usarlo (la corrida diaria lo usa), si Luis quita el acceso o si cambia
la contraseña de Google. En esos casos, repite 4b (o 4c) y reemplaza el secreto.

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
   contenido, de la primera `{` a la última `}`, y guárdalo en GitHub (solo
   short-video-studio) como `GOOGLE_SERVICE_ACCOUNT_JSON`.
4. **Borra el archivo** de Descargas y vacía la papelera.
5. Copia el correo de la cuenta de servicio (termina en
   `@videos-luis.iam.gserviceaccount.com`; aparece en la lista del paso 1).
6. Abre la carpeta «Videos del domingo»:
   https://drive.google.com/drive/folders/1kK0XBp3EnNyqOWjHrXoPp_liVE7900fy
   - Clic en el nombre de la carpeta → **Compartir**.
   - Pega el correo de la cuenta de servicio. Elige **Lector**.
   - Desmarca **Notificar** y clic en **Compartir**.

**Videos de la app (más adelante):** la primera vez que corra el lote de
bible-ai-honduras con su token, se crea en el Drive de Luis la carpeta «Bible AI ·
videos para publicar». Compártela igual, como **Lector**, con el mismo correo.
Luego copia su id (lo que va después de `folders/` en la dirección) y pégalo en
`config/calendario.yaml`, en `carpeta_drive:` de Bible AI. Se puede editar
desde GitHub con el lápiz ✏️. Mientras no esté, los días de app no publican
nada, y el resumen lo avisa.

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
3. Copia la llave y guárdala en GitHub (solo short-video-studio) como
   `BUFFER_API_KEY`.
4. En Buffer, revisa que TikTok, Instagram y LinkedIn estén conectados. Cada
   canal necesita al menos un horario en **Settings → Posting Schedule**, antes
   de las 21:00. Instagram tiene que ser una cuenta de **empresa o creador**.

---

## Tabla final de secrets

**Repo `luiscf1226/short-video-studio` → environment `videos`**

| Nombre exacto | Tipo | Qué es | Paso |
|---|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Secret | Todo el archivo JSON de la cuenta de servicio | 5 |
| `GOOGLE_OAUTH_CLIENT_ID` | Secret | Client ID | 4a |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Secret | Client secret | 4a |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | Secret | Refresh token de YouTube + Drive | 4b |
| `BUFFER_API_KEY` | Secret | Llave de la API de Buffer | 7 |
| `MODO_AUTOMATICO` | **Variable** (pestaña *Environment variables*, no Secrets) | `dry_run` al principio; `borrador` para probar; `programar` solo con el OK de Luis | — |

**Repo `luiscf1226/bible-ai-honduras` → environment `videos`**

| Nombre exacto | Tipo | Qué es | Paso |
|---|---|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | Secret | El mismo Client ID | 4a |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Secret | El mismo Client secret | 4a |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | Secret | Refresh token **solo `drive.file`** | 4c |

(Los otros secretos de ese environment, como `ELEVENLABS_API_KEY` y los del
correo, son del lote semanal y están en `docs/plan-nube.md` de ese repo.)

---

## Paso 8. Probar que quedó bien (dry-run de Actions, 2 minutos)

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

> El botón **Run workflow** aparece después de mergear el PR a `main`.

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
python3 scripts/sacar_refresh_token.py ~/Descargas/client_secret_XXXX.json \
    --solo-drive-file --repo luiscf1226/bible-ai-honduras --env videos
python -m pipeline llaves   # la misma prueba de llaves, con los secretos en variables de entorno
```
</details>
