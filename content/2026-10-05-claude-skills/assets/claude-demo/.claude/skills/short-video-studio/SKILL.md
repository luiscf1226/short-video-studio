---
name: short-video-studio
description: Interview the creator about weekly topics, then plan and produce weekly batches of vertical videos for YouTube Shorts, TikTok, and Instagram Reels, with standalone scripts, batch shot lists, edits, captions, platform copy, and a content calendar. Use for short-form content weeks or individual vertical videos.
---

# Short Video Studio

Turn a topic or existing footage into a manageable week of standalone vertical videos. Support planning-only, footage editing, and performance review; select the requested mode rather than forcing every request through production.

Default audience-facing deliverables to Spanish, matching the author's original video studio. User language choices override this. Keep filenames and JSON keys in English.

## Interview the creator about the week

For a new content week, start a short conversation about the creator's topics before choosing the lineup or drafting scripts. Read [references/interview.md](references/interview.md). A broad niche such as “AI tools for beginners” establishes the audience; it does not replace the weekly topic interview.

Read existing notes and previous weeks first, and reuse known audience, language and preferences. Ask in the deliverable language, with no more than three short questions per round. Start with what the creator wants to discuss this week, what their audience should learn, and any recent experience or audience question worth showing. Tailor follow-ups to the answers rather than presenting a long generic intake form.

Wait for the creator's answers before choosing topics or drafting that week's scripts. While waiting, inspect previous content, assets or relevant sources. Silence or elapsed time is not a topic choice. If the user explicitly asks to skip the interview, delegate topic selection, or supplies a sufficiently complete weekly brief, proceed and record that basis; do not repeat questions already answered.

Save answers and editorial decisions in `interview.md` in the content-week directory. Keep user statements distinct from suggestions and unknowns. Use the answers to choose distinct angles, not merely to add an interview file to a preselected calendar. Present a compact recap of the chosen direction with the resulting plan; no extra approval gate is needed when the answers establish the direction.

Determine start date/timezone, cadence, footage and production capacity from context or focused follow-ups. Unless otherwise specified, use seven original concepts for a Monday–Sunday week, one reusable vertical master per concept, adapted copy for all three platforms, and a 30–45 second creative target. This is seven videos and up to 21 publishing placements, not 21 separate productions. Duration and cadence are creative defaults, not platform limits. Use the next Monday for an undated future week; preserve a requested start date. Do not claim posting times are optimal without account evidence.

## Weekly planning

Use the interview answers or explicit delegated brief. Read [references/weekly-workflow.md](references/weekly-workflow.md). Produce a complete calendar, seven distinct scripts (or the requested count), recording list grouped by setup, and platform copy. Every video should work for a viewer who missed earlier days. Vary the viewer problem and format; avoid seven paraphrases of the same tip.

Give every concept a stable ID used in filenames, calendar, scripts, and status. Each brief needs a concrete promise, exact spoken hook plus an alternate, visual payoff, timed beats, full spoken text, on-screen text, B-roll/screen needs, cover text, one CTA, and a measurable hypothesis. Budget spoken words against the creator's pace and leave room for demonstrations. Timings remain estimates until recorded.

Write `calendar.md`, `week.json`, `production.md`, `scripts/<id>.md`, and `publishing.csv` in a content-week directory. Keep `week.json` as the canonical schedule/status record; regenerate tables if it changes. Read platform guidance only when adapting/exporting: [references/platforms.md](references/platforms.md).

## Production from footage

Read [references/production.md](references/production.md). Bundled scripts reuse the author's original ffmpeg workflow; provenance and limits are in [references/upstream.md](references/upstream.md). Resolve script paths from this skill directory, not a fixed user home path.

Keep originals in `raw/` and work in `build/`; keep an EDL and timemap per video. Source-time EDL values must come from actual footage/transcripts, never estimated script beats. Inspect the source dimensions before choosing a vertical crop. Make vertical framing before burning captions; horizontal captions do not survive a crop correctly. Keep speech meaning intact when removing pauses/fillers; consult [references/filler-words-es.md](references/filler-words-es.md) for Spanish ambiguity.

Complete authorized reversible local work without extra outline/edit approval stops. Missing footage is a production dependency, not a reason to leave requested scripts unfinished. Use paid transcription or generation only within the user's authorization and budget; offer supplied transcripts/local tools when unavailable. Verify live pricing before quoting costs. Publishing or scheduling into accounts requires instructions for that action; a content plan alone authorizes preparation.

## Review and handoff

Distinguish `planned`, `recorded`, `edited`, `ready`, `scheduled`, and `published`; never mark footage ready from a written plan. Mark a render ready only after technical checks and visual/audio inspection, listing unavailable checks honestly. Return links to the calendar, scripts, publishing sheet and any actual renders, with remaining inputs.

For a follow-up week, use actual account metrics measured at comparable post ages. Compare formats and topics within each platform; do not equate differently defined view counts. Missing analytics stay unknown. Turn the strongest observed hypothesis into a new test, without promising reach or inventing trends.
