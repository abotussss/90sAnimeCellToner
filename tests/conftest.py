from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe are required for these tests.")


@pytest.fixture()
def sample_video_path(tmp_path: Path) -> Path:
    require_ffmpeg()
    output_path = tmp_path / "sample.mp4"
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=0x0f1b27:s=640x360:r=24:d=1.2",
        "-f",
        "lavfi",
        "-i",
        "color=c=0xd7d7d0:s=640x360:r=24:d=1.2",
        "-filter_complex",
        (
            "[0:v]drawbox=x=120:y=70:w=400:h=220:color=0x57d4ff@1.0:t=fill,"
            "drawbox=x=145:y=95:w=180:h=150:color=0x121c2c@1.0:t=fill,"
            "drawbox=x=330:y=80:w=110:h=160:color=0xf0f0f0@1.0:t=fill,"
            "drawbox=x=20:y=305:w=600:h=34:color=0xffffff@1.0:t=fill[v0];"
            "[1:v]drawbox=x=170:y=55:w=300:h=250:color=0xffffff@1.0:t=fill,"
            "drawbox=x=205:y=90:w=230:h=180:color=0x202020@1.0:t=5[v1];"
            "[v0][v1]concat=n=2:v=1:a=0[v]"
        ),
        "-map",
        "[v]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output_path

