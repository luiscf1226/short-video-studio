# Weekly workflow and output contract

## Content choices

Start from the creator’s weekly interview or explicitly delegated/provided brief. Read [interview.md](interview.md) when gathering topics. Tie the week to one audience problem and a concrete outcome. A useful starting mix is: problem/quick win, tutorial, mistake, before/after demonstration, behind the scenes, FAQ/objection, and recap/challenge. Change it for the niche and available evidence; it is not a fixed content formula.

Each video teaches or demonstrates one useful thing. Open with an observable result or recognizable problem, show the proof early, and end with one action. Do not invent testimonials, savings, product capabilities or audience comments. If a demo result is unverified, mark it as something to record/check.

For 30–45 seconds, start with roughly 65–95 Spanish words, then time a spoken read and leave pauses for visuals. Estimated beat structure: hook 0–3s, problem/result 3–8s, demonstration 8–30s, payoff/CTA 30–40s. Change timing for the story. An alternate hook is an optional variant, not a second required render.

## Files

`interview.md` records the creator’s answers and chosen direction. `week.json` includes `brief_source` with mode `interview`, `provided`, or `delegated` and its brief path; do not backfill a fictional interview for an earlier plan.

`week.json` has `week_start` (ISO date), `timezone`, `language`, `topic`, `audience`, `goal`, `assumptions`, `production_budget`, and `videos`.

Each `videos` item: `id`, `date`, `slug`, `format`, `promise`, `target_seconds`, `script_path`, `status`, `hypothesis`, and `platforms` keyed by `youtube`, `tiktok`, `instagram`. Each platform stores proposed copy, `publish_time` (null if unknown), `status`, and later `published_url`. Rendering one master does not imply that all placements were published.

`calendar.md` shows date, ID, topic, hook, format, target duration, goal and status. `scripts/<id>.md` contains exact narration, estimated beats/visuals, alternate hook, cover text and CTA. `production.md` groups all takes by camera/screen/props and states realistic prep/record/edit allowances and blockers. `publishing.csv` has one row per video/platform, with date, timezone, proposed time, ID, platform, file, title/caption, cover text and status. Do not fabricate a final file path as existing; leave it empty until rendered.

## Batch production

Prepare recurring set, light, audio and vertical text treatment once. Record all hooks with two takes, then all main takes grouped by setup, then demonstrations/B-roll. Retakes preserve the same ID. For screen demos, show only the relevant UI at readable scale and remove private information.

Plan the first batch before its first release. For an ongoing weekly rhythm, use a preparation block, recording block, editing block and daily publishing/reply block. Give time allowances as estimates, and offer a smaller cadence if actual capacity cannot cover the batch. Do not silently reduce a requested seven-video week.

## Measurement

Track actual views, average watch time and video duration, retention/completion if available, saves, shares, profile visits and relevant actions. Record platform, capture timestamp and post age. A 24-hour snapshot and a 7-day snapshot are useful repeatable checkpoints, not guaranteed attribution windows. Compare against the account's own history. Change one major variable per follow-up experiment where practical.
