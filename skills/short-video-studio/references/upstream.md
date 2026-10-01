# Source and reuse

Adapted from https://github.com/luiscf1226/video-studio-skill at commit `2b5504281e01470ef31235aad41d656439a20f24` (MIT, Luis Fernando, 2026). The bundled editing scripts and EDL/filler references originate there; the weekly workflow is new. License is retained in `../LICENSE`.

The source checkout in the author's workspace is a reference, not a runtime dependency. Bundled scripts are usable without the original skill. Read their `--help` before invoking. They have not all been exercised end to end on the target machine. `transcribe.py` uploads audio to ElevenLabs and can incur charges; planning and local editing do not need it.

Original outline/edit/polish approval gates belong to the original workflow. This companion does not inherit them: complete authorized local planning and edits, report results, and only request missing inputs or authorization required for external actions.
