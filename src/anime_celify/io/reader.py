from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class VideoFrame:
    index: int
    frame_bgr: np.ndarray


class VideoReader:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._capture = cv2.VideoCapture(str(path))
        if not self._capture.isOpened():
            raise RuntimeError(f"Failed to open video for reading: {path}")

    def __enter__(self) -> "VideoReader":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._capture.isOpened():
            self._capture.release()

    def iter_frames(self):
        index = 0
        while True:
            success, frame = self._capture.read()
            if not success:
                break
            yield VideoFrame(index=index, frame_bgr=frame)
            index += 1

    def read_frame(self, frame_index: int) -> np.ndarray:
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = self._capture.read()
        if not success:
            raise RuntimeError(f"Could not read frame index {frame_index}")
        return frame
