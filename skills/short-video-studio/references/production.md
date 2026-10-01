# Local editing bridge

These helpers are bundled from the original studio. Run `python3 <skill>/scripts/<tool>.py --help` before choosing flags. Run `fftool.py` to inspect ffmpeg/ffprobe and filters on the actual machine; do not copy macOS-specific installation advice onto Linux. Inspect available fonts before selecting a caption preset.

For each video, work from its project directory. Use separate `edl.json`, `build/timemap.json`, transcripts and captions so days cannot overwrite one another.

1. Inspect footage and transcript. Supplied word timestamps or a supported local transcriber are sufficient; `transcribe.py` is an optional ElevenLabs upload, not a prerequisite for planning. Inspect its options and obtain authorization for paid uploads as needed. `analyze.py` helps find pauses/fillers.
2. Write source-time cuts following [edl-schema.md](edl-schema.md). `cut.py edl.json --outdir build` generates both rough cut and timemap. Preserve originals. Source paths are resolved from the working directory.
3. Use `overlay.py` only for assets actually present and timed through the EDL/timemap. Check its current CLI. Avoid adding graphics for every line when a real demo explains the point.
4. If necessary, run `reframe.py build/rough.mp4 --preset crop --out build/vertical.mp4`, choosing focus after inspecting the subject. Use blur for full-frame content or stack with a measured webcam rectangle. Do not center-crop UI blindly. If the edit is already 1080×1920, keep it vertical without reframing.
5. Generate captions from actual words and `build/timemap.json` using `captions.py`, with `--width 1080 --height 1920`. Inspect `--help` for style and font/position options. Correct names and punctuation; check caption placement on a real preview. Convert ASS to SRT with ffmpeg if a sidecar is needed. Scripts do not fabricate captions from estimated script timings.
6. `render.py build/vertical.mp4 --captions captions/final.ass --out final/<id>-master.mp4` encodes the vertical edit. Adapt the input path to the actual completed intermediate. Read optional music flags if a licensed track is provided.

Verify with ffprobe: dimensions, video/audio codecs, frame rate, duration, pixel format, and audio presence. Decode the entire file for errors and inspect beginning, cuts, captions, ending and audio. Check loudness if delivery depends on it. The helper's built-in validation alone does not prove captions are readable or audio is intelligible. Do not mark a render ready when only a CLI help or capability check ran.

Update the week record and publishing paths only after exports exist. Reuse the clean master across platforms when identical; render variants only when copy, audio rights, length or framing requires them.
