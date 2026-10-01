# Weekly topic interview

## Start naturally

Reuse known preferences. For this creator, the established audience is Spanish-speaking people who want to learn about AI tools. Keep this in mind unless the creator changes it. Do not ask again which language to use every week.

A suitable opening is:

“¿Qué herramientas o temas de IA te gustaría enseñar esta semana? Puedes contarme una idea, algo que probaste o una duda que te hayan hecho. Si todavía no tienes temas, podemos descubrirlos juntos.”

Ask this first and let the answer guide the next round. Optional prompts can help someone answer; do not replace their choice with a predefined tool list.

## Follow up on the answer

Choose only the questions that resolve actual gaps, usually one or two at a time:

- Audience problem: “¿Qué te gustaría que una persona principiante pudiera hacer después de ver estos videos?”
- Personal evidence: “¿Qué probaste tú y qué resultado o dificultad podríamos mostrar?”
- Scope: “¿Quieres profundizar en esa herramienta durante la semana o combinarla con otros temas?”
- Viewer questions: “¿Hay alguna pregunta o comentario de tu audiencia que quieras responder?”
- Angle: “¿Quieres explicarlo como tutorial, experiencia personal o comparación? ¿Qué te interesa contar?”
- Boundaries: “¿Qué temas o promesas quieres evitar?”
- Production: “¿Puedes grabar demostraciones de pantalla, hablar a cámara o prefieres voz en off? ¿Cuánto tiempo tienes esta semana?”

Ask tool/access questions only for tools that the creator actually wants to feature. If there are no ideas yet, explore one everyday problem first, then offer two or three topic directions with a reason for each. Ask which direction interests them and wait for their answer. An answer such as “elige tú” delegates selection; record it and proceed.

## Finish with a useful brief

When the creator has supplied a direction and enough material to plan, stop interviewing. Do not require a fixed question count or an additional approval round. If an answer is ambiguous and changes the topic lineup, clarify that specific point.

Write `interview.md` with:

- Known audience and language.
- Creator's topic ideas, questions and experiences, preserving their meaning.
- Desired viewer outcome and preferred approach.
- Tools/material that can actually be demonstrated.
- Exclusions and production constraints supplied by the creator.
- Chosen direction, distinguishing creator choices from agent suggestions.
- Remaining unknowns and any explicitly delegated decisions.

Add `brief_source` to `week.json`, such as `{"mode": "interview", "path": "interview.md"}`. If the creator explicitly skips the interview or supplies a complete brief, use mode `delegated` or `provided` and record the actual instruction in the brief. Never claim an interview happened when only assumptions were supplied.

Build the calendar from this brief. It can turn one tool into several distinct viewer problems or combine several tools, depending on the creator's chosen approach. For an existing week, interview about the requested topic changes before replacing its lineup; preserve the current files until the new direction is established. A narrow edit to an existing script does not require restarting the interview.
