from __future__ import annotations

from pathlib import Path

from anime_celify.config import load_preset_definition
from anime_celify.pipeline import analyze_video, transform_video


def test_pipeline_smoke(sample_video_path: Path, tmp_path: Path) -> None:
    preset = load_preset_definition("cyber_noir_95")
    output_path = tmp_path / "smoke_output.mp4"
    log_path = tmp_path / "smoke_output.transform_log.json"

    report = analyze_video(sample_video_path, preset)
    assert report
    assert report[0].shot_profile in {"urban_night", "neutral_daylight", "bio_mech_glow"}

    run_log = transform_video(
        input_path=sample_video_path,
        output_path=output_path,
        preset_definition=preset,
        auto_tune=True,
        log_path=log_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert log_path.exists()
    assert run_log.auto_tune_enabled is True
    assert any(scene.shot_profile in {"urban_night", "neutral_daylight", "bio_mech_glow"} for scene in run_log.scenes)

