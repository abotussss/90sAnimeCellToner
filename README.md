# anime-celify

`anime-celify` is an OSS-ready Python CLI that shifts short modern anime mp4 clips toward a colder, harder 90s cel-photography feel. The MVP prioritizes a deterministic OpenCV + FFmpeg + PySceneDetect pipeline and keeps AI limited to shot-wise parameter suggestions.

The first completion target is `cyber_noir_95`: a cold cyber-noir look with restrained saturation, blue-black line treatment, hard cel-like shadow organization, selective milky halation on emissive regions, and mild temporal stabilization.

## What It Does

- Accepts mp4 input and writes mp4 output.
- Rejects clips longer than 15 seconds.
- Detects cuts with PySceneDetect and falls back to one full-scene segment if detection fails.
- Processes frames with deterministic signal processing:
  - edge-preserving smoothing
  - line extraction and blue-black line emphasis
  - luma/chroma posterization
  - cool midtone bias and darker shadows
  - selective halation, grain, vignette, and temporal blending
- Saves the actual applied settings and per-scene decisions as a JSON log.
- Supports `--auto-tune`, where a heuristic analyzer classifies scenes into:
  - `urban_night`
  - `neutral_daylight`
  - `bio_mech_glow`

## What It Does Not Do

- Long-form batch conversion.
- GUI workflows.
- Fully learned video-to-video stylization.
- Reproducing a specific title's exact drawing style.
- User-provided reference-image training.
- Cloud-only processing.

## Setup

### Requirements

- Python 3.11+
- FFmpeg and ffprobe available on `PATH`

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### FFmpeg Check

```bash
ffmpeg -version
ffprobe -version
```

## Usage

```bash
anime-celify presets list
anime-celify presets show cyber_noir_95
anime-celify analyze input.mp4 --preset cyber_noir_95
anime-celify transform input.mp4 -o output.mp4 --preset cyber_noir_95
anime-celify transform input.mp4 -o output.mp4 --preset cyber_noir_95 --auto-tune
anime-celify transform input.mp4 -o output.mp4 --config configs/custom.yaml
```

## Built-In Presets

- `cyber_noir_95`
- `tv_mecha_95`
- `sports_cel_warm`

`cyber_noir_95` is the main MVP target. The other presets exist so the project is publishable as a configurable OSS tool, but the strongest tuning effort is intentionally concentrated on the cyber-noir path.

## Auto-Tune

`--auto-tune` does not stylize frames directly. It analyzes a representative frame from each detected shot and proposes per-shot parameter deltas on top of the selected preset. In the current MVP, the analyzer is heuristic and deterministic so that future external LLM/VLM integrations can be added behind the same interface without changing the core pipeline.

## Logs

Each transform writes a sidecar JSON log by default:

- `output.transform_log.json`

The log contains:

- ffprobe metadata
- scene boundaries
- selected shot profile per scene
- actual merged processing parameters
- runtime notes and warnings

## Limitations

- Input must be `mp4`.
- Duration must be 15 seconds or less.
- The project primarily targets 24/30 fps anime clips and resolutions around 720p to 1080p.
- Audio is preserved when FFmpeg can copy it from the source; the processed video stream is always re-encoded to H.264.
- Background/foreground separation, subtitle protection, and shot classification are heuristic in this MVP.

## Design Notes

- The transform core is deterministic signal processing.
- AI is optional and acts only as a settings suggester.
- Presets are stored as YAML resources.
- The CLI-first layout is structured so a future Python API can be exposed cleanly.

## Running Tests

```bash
pytest
```

The smoke tests generate short synthetic mp4 fixtures with FFmpeg and verify that a transformed mp4 plus a transform log are produced successfully.

## TODO

- Improve foreground/background separation beyond the current center-and-edge heuristic.
- Add better subtitle and UI text protection masks.
- Expose more ffmpeg encoder controls on the CLI.
- Add scene-level preview export for analyzer debugging.
- Offer a Python API wrapper around the pipeline functions.
- Investigate optional GPU or parallel acceleration paths.

## License

MIT

