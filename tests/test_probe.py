from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from anime_celify.probe import ProbeError, probe_video


def test_probe_video_reads_short_mp4(sample_video_path: Path) -> None:
    metadata = probe_video(sample_video_path)
    assert metadata.duration_seconds <= 3.0
    assert metadata.width == 640
    assert metadata.height == 360
    assert metadata.codec_name == "h264"


def test_probe_rejects_over_15_seconds(tmp_path: Path) -> None:
    output_path = tmp_path / "too_long.mp4"
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=640x360:r=24:d=16.1",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    with pytest.raises(ProbeError, match="15s MVP limit"):
        probe_video(output_path)

