from __future__ import annotations

import json
import subprocess
from pathlib import Path


class FFMpegError(RuntimeError):
    """Raised when ffmpeg or ffprobe commands fail."""


def run_ffmpeg(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise FFMpegError(completed.stderr.strip() or "ffmpeg command failed")


def run_ffprobe_json(path: Path) -> dict[str, object]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_name,codec_type,width,height,avg_frame_rate,nb_frames",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise FFMpegError(completed.stderr.strip() or "ffprobe command failed")
    return json.loads(completed.stdout)


def mux_processed_video(
    processed_video_path: Path,
    source_video_path: Path,
    output_path: Path,
) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(processed_video_path),
        "-i",
        str(source_video_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a?",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        "-shortest",
        str(output_path),
    ]
    run_ffmpeg(command)

