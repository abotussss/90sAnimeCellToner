from __future__ import annotations

from pathlib import Path

from anime_celify.desktop import DesktopTransformRequest, default_output_path, run_desktop_request


def test_default_output_path(sample_video_path: Path) -> None:
    output_path = default_output_path(sample_video_path)
    assert output_path.name.endswith("_celified.mp4")


def test_desktop_request_smoke(sample_video_path: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "desktop_output.mp4"
    log_path = tmp_path / "desktop_output.transform_log.json"
    run_log = run_desktop_request(
        DesktopTransformRequest(
            input_path=sample_video_path,
            output_path=output_path,
            preset_name="cyber_noir_95",
            auto_tune=True,
            log_path=log_path,
        )
    )
    assert output_path.exists()
    assert log_path.exists()
    assert run_log.output_path == output_path
