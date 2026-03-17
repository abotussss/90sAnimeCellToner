from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np

from anime_celify.ffmpeg_utils import mux_processed_video


class OpenCVTempWriter:
    def __init__(self, width: int, height: int, fps: float) -> None:
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="anime_celify_"))
        self.temp_video_path = self._tmp_dir / "processed_silent.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(str(self.temp_video_path), fourcc, fps, (width, height))
        if not self._writer.isOpened():
            raise RuntimeError("Failed to initialize temporary video writer.")

    def write(self, frame_bgr: np.ndarray) -> None:
        self._writer.write(frame_bgr)

    def close(self) -> Path:
        self._writer.release()
        return self.temp_video_path

    def finalize(self, source_video_path: Path, output_path: Path) -> None:
        processed_video_path = self.close()
        try:
            mux_processed_video(processed_video_path, source_video_path, output_path)
        finally:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
