# Short Video Studio

Skill para entrevistar al creador y preparar una semana de videos verticales en español para YouTube Shorts, TikTok e Instagram Reels. Incluye guiones, tomas, edición local con ffmpeg y textos por plataforma.

## Empezar con la semana de skills

La primera semana explica qué son las skills, cómo crear una y cómo usarla en Claude Code.

- [Guía del viernes: grabar V01](content/2026-10-05-claude-skills/recording-kit/FRIDAY.md)
- [Calendario y siete guiones](content/2026-10-05-claude-skills/calendar.md)
- [Plan de producción](content/2026-10-05-claude-skills/production.md)
- [Textos para 21 publicaciones](content/2026-10-05-claude-skills/publishing.csv)
- [Proyecto de demostración y comandos](content/2026-10-05-claude-skills/assets/demo-commands.md)

Grabación prevista desde el viernes 2 de octubre de 2026; publicación propuesta del 5 al 11. Las fechas son un plan, no publicaciones programadas. También se conserva el borrador inicial de herramientas de IA en `content/2026-10-05-ai-tools/`.

## Teleprompter y material visual

Abrir `content/2026-10-05-claude-skills/recording-kit/studio.html` directamente en el navegador: funciona sin conexión. Incluye selección de los siete guiones, velocidad, tamaño de letra, espejo, edición temporal del texto y descarga. Las portadas PNG/SVG y las tarjetas visuales están en `recording-kit/`.

Para verlo desde un servidor local, ejecutar desde la raíz del repositorio:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Abrir `http://localhost:8765/content/2026-10-05-claude-skills/recording-kit/studio.html`.

## Usar la skill

La skill principal está en [skills/short-video-studio](skills/short-video-studio/SKILL.md). La carpeta contiene instrucciones, referencias y scripts; no requiere la copia del repositorio original.

Para Claude Code, copiar esa carpeta a `.claude/skills/short-video-studio/` dentro del proyecto donde quieras usarla, o a `~/.claude/skills/short-video-studio/` para uso personal. Invocar `/short-video-studio` y contarle qué semana quieres preparar. Empezará por una entrevista sobre tus temas.

El proyecto de demostración ya incluye una copia de esa skill y una skill mínima `ideas-short`:

```bash
cd content/2026-10-05-claude-skills/assets/claude-demo
claude
```

Dentro de Claude Code:

```text
/ideas-short skills para principiantes
```

Para Codex, copiar la carpeta principal a `~/.codex/skills/short-video-studio/` e invocar `$short-video-studio`.

La planificación no necesita APIs ni grabaciones. Los scripts de edición requieren Python 3 y ffmpeg/ffprobe; `fftool.py` comprueba las capacidades. La transcripción ElevenLabs es opcional, usa una clave y puede tener coste. Consultar `--help` y las referencias antes de ejecutar cada helper.

## Estado y archivos

`week.json` guarda calendario y estados; `interview.md` conserva respuestas del creador. Guiones y copy están preparados; faltan grabación, demos reales en Claude Code, edición y revisión de exports. Guardar originales en `content/<semana>/raw/<video>/`; grabaciones, exports, credenciales y paquetes ZIP locales no se suben al repositorio.

Validado: estructura de skills, enlaces del kit, 21 entradas de publicación y controles básicos del teleprompter. Los helpers de corte, reencuadre, subtítulos y render pasaron una prueba local con material sintético; las demostraciones de Claude Code no se ejecutaron.

## Origen y licencia

Basado en [video-studio-skill de Luis Fernando](https://github.com/luiscf1226/video-studio-skill). Los helpers reutilizados y sus referencias conservan la licencia MIT; [procedencia y revisión base](skills/short-video-studio/references/upstream.md). El flujo semanal, la entrevista y el kit de grabación se añadieron en este proyecto.
