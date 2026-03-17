from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from anime_celify.config import load_preset_definition
from anime_celify.pipeline import analyze_video, transform_video


def _frame_stats(path: Path) -> dict[str, float]:
    capture = cv2.VideoCapture(str(path))
    success, frame = capture.read()
    capture.release()
    assert success
    frame_float = frame.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
    luminance = np.dot(frame_float, np.array([0.114, 0.587, 0.299], dtype=np.float32))
    cool_ratio = np.mean(
        (frame_float[..., 0] > frame_float[..., 1] + 0.04)
        & (frame_float[..., 0] > frame_float[..., 2] + 0.04)
    )
    return {
        "brightness": float(np.mean(luminance)),
        "saturation": float(np.mean(hsv[..., 1])),
        "cool_ratio": float(cool_ratio),
        "highlight_ratio": float(np.mean(luminance > 0.8)),
    }


def test_pipeline_smoke(sample_video_path: Path, tmp_path: Path) -> None:
    preset = load_preset_definition("cyber_noir_95")
    output_path = tmp_path / "smoke_output.mp4"
    log_path = tmp_path / "smoke_output.transform_log.json"

    report = analyze_video(sample_video_path, preset)
    assert report
    assert report[0].shot_profile == "urban_night"

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

    original_stats = _frame_stats(sample_video_path)
    transformed_stats = _frame_stats(output_path)
    assert transformed_stats["saturation"] <= original_stats["saturation"]
    assert transformed_stats["cool_ratio"] >= original_stats["cool_ratio"]
    assert transformed_stats["highlight_ratio"] <= original_stats["highlight_ratio"]
