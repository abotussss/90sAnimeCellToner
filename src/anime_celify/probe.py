from __future__ import annotations

from pathlib import Path

from anime_celify.ffmpeg_utils import FFMpegError, run_ffprobe_json
from anime_celify.models import VideoMetadata

MAX_DURATION_SECONDS = 15.0
SUPPORTED_VIDEO_CODECS = {"h264", "hevc", "mpeg4", "av1"}


class ProbeError(RuntimeError):
    """Raised when video probing or validation fails."""


def _parse_fps(avg_frame_rate: str) -> float:
    if not avg_frame_rate or avg_frame_rate == "0/0":
        raise ProbeError("Could not determine FPS from ffprobe output.")
    numerator, denominator = avg_frame_rate.split("/")
    return float(numerator) / float(denominator)


def probe_video(path: Path) -> VideoMetadata:
    if not path.exists():
        raise ProbeError(f"Input file not found: {path}")
    if path.suffix.lower() != ".mp4":
        raise ProbeError("Only mp4 input is supported in this MVP.")

    try:
        payload = run_ffprobe_json(path)
    except FFMpegError as exc:
        raise ProbeError(str(exc)) from exc

    streams = payload.get("streams", [])
    format_info = payload.get("format", {})
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if video_stream is None:
        raise ProbeError("No video stream found in input mp4.")

    duration_seconds = float(format_info.get("duration", 0.0))
    fps = _parse_fps(str(video_stream.get("avg_frame_rate", "0/0")))
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    codec_name = str(video_stream.get("codec_name", "unknown"))
    nb_frames = video_stream.get("nb_frames")
    frame_count_estimate = int(float(nb_frames)) if nb_frames not in (None, "N/A") else max(1, round(duration_seconds * fps))

    metadata = VideoMetadata(
        path=path,
        duration_seconds=duration_seconds,
        fps=fps,
        width=width,
        height=height,
        codec_name=codec_name,
        has_audio=audio_stream is not None,
        audio_codec_name=str(audio_stream.get("codec_name")) if audio_stream else None,
        frame_count_estimate=frame_count_estimate,
    )
    validate_video_metadata(metadata)
    return metadata


def validate_video_metadata(metadata: VideoMetadata) -> None:
    if metadata.duration_seconds > MAX_DURATION_SECONDS:
        raise ProbeError(
            f"Input duration {metadata.duration_seconds:.2f}s exceeds the 15s MVP limit."
        )
    if metadata.codec_name not in SUPPORTED_VIDEO_CODECS:
        supported = ", ".join(sorted(SUPPORTED_VIDEO_CODECS))
        raise ProbeError(
            f"Unsupported video codec '{metadata.codec_name}'. Supported codecs: {supported}."
        )
    if metadata.width < 640 or metadata.height < 360:
        raise ProbeError("Input resolution is too small for this MVP. Please use at least 640x360.")

