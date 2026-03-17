from __future__ import annotations

import logging
from pathlib import Path

from anime_celify.models import SceneSegment, VideoMetadata


def _fallback_scene(metadata: VideoMetadata) -> list[SceneSegment]:
    return [
        SceneSegment(
            index=0,
            start_seconds=0.0,
            end_seconds=metadata.duration_seconds,
            start_frame=0,
            end_frame=metadata.frame_count_estimate,
        )
    ]


def detect_scenes(video_path: Path, metadata: VideoMetadata) -> list[SceneSegment]:
    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import ContentDetector
    except Exception:
        return _fallback_scene(metadata)

    try:
        logging.getLogger("pyscenedetect").setLevel(logging.WARNING)
        video = open_video(str(video_path))
        manager = SceneManager()
        manager.add_detector(ContentDetector(threshold=24.0))
        manager.detect_scenes(video, show_progress=False)
        scene_list = manager.get_scene_list()
    except Exception:
        return _fallback_scene(metadata)

    if not scene_list:
        return _fallback_scene(metadata)

    segments: list[SceneSegment] = []
    for index, (start_time, end_time) in enumerate(scene_list):
        start_frame = max(0, start_time.get_frames())
        end_frame = max(start_frame + 1, end_time.get_frames())
        segments.append(
            SceneSegment(
                index=index,
                start_seconds=float(start_time.get_seconds()),
                end_seconds=float(end_time.get_seconds()),
                start_frame=start_frame,
                end_frame=end_frame,
            )
        )
    return segments
