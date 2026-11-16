# Semana 47: cómo se grabaron los videos

Videos verticales de 1080×1920 a 30 fps, con pista de audio en silencio. Cada
uno es una grabación de la app real en un navegador con tamaño de teléfono
(Playwright, 405×720 pt a densidad 8/3). Encima solo se agregan el gancho, los
rótulos de cada paso y la tarjeta de cierre (`estudio.cjs`). Los toques se ven
como un círculo, porque en una grabación de pantalla no aparece el dedo.

| Video | App grabada | Script |
|---|---|---|
| `bible-devocional.mp4` | Producción: `https://bible-ai-honduras.vercel.app/hoy`, el devocional del día que se ve sin iniciar sesión | `devocional.cjs` |
| `evo-mascota.mp4` | `luiscf1226/evo-ai-mvp`: exportación web (`npx expo export -p web`) contra un backend Convex local | `evo.cjs` |
| `bible-ansiedad` | **No se grabó**: ver abajo | — |

```bash
NODE_PATH=$(npm root -g) node devocional.cjs /tmp/semana-47
EVO_DIR=~/evo-ai-mvp EVO_WEB=http://localhost:8090 NODE_PATH=$(npm root -g) node evo.cjs /tmp/semana-47
```

## Devocional

Se graba el devocional que la app sirve el día de la grabación
(`devotional:today` usa la fecha de Honduras del servidor). Se grabó el lunes
16 de noviembre, así que el encabezado dice esa fecha y el texto es el de ese
día (Salmos 116:12). El devocional del día es el mismo para todas las
personas: el código no lo arma por usuario.

## Evo

- Backend: el binario `convex-local-backend` oficial, con las funciones de
  `evo-ai-mvp` (`npx convex dev --once`), `EVO_AI_PROVIDER=mock` y llaves JWT
  generadas para esa copia. No se escribió nada en producción.
- Ese backend no tiene proveedor de correo. La cuenta de prueba
  (`video-evo-…@evo-ai.test`) se crea con la acción real de registro y el correo
  se marca como verificado con una mutación interna que solo existió en la
  copia local (`convex/zzVideoLocal.ts`, no está en ningún repo).
- Parte 1: onboarding real (área, meta, compañero Orbit Impulso, forma Evo
  Cosmos), el plan del día y el inicio con Orbit.
- Entre partes, para no esperar varios días, la XP de la cuenta de prueba sube
  de 0 a 85. Primero entra el rótulo «Unos días después…» con el anillo en 0%;
  ya con el rótulo en pantalla, la XP sube en pasos de 5 y la app actualiza el
  anillo en vivo (0 → 85%). La parte 1 se puede reusar con `EVO_PARTE1`.
- Parte 2: se completa «Practica durante 20 minutos» (+20 XP), sube a nivel 2,
  Orbit celebra y en Progreso → Recompensas aparece desbloqueado «Brillo de
  Enfoque» (el premio de nivel 2 del catálogo). Ojo: el campo «Etapa» de la
  mascota no cambia en el código actual (siempre 1); lo que crece es el nivel
  y los desbloqueos.
- Al terminar se borró la base local completa (todas las cuentas de prueba).

## Por qué no hay `bible-ansiedad`

En la web de producción, Preguntar se abre sin sesión pero no envía la
pregunta: `rag/answer:ask` es una acción interna y la app solo pregunta con una
cuenta (Clerk: código por correo, Google o Apple). Esta sesión no tiene una
cuenta de prueba ni un buzón para recibir el código: los servicios de correo
temporal están bloqueados por la red. El harness de QA tampoco sirve: su
respuesta es un texto fijo («El texto no promete ausencia de tormenta…»), no
la respuesta real con versículos. Para grabarlo hace falta una sesión iniciada
(por ejemplo, la cuenta de prueba de App Review).
