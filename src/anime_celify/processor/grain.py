from __future__ import annotations

import cv2
import numpy as np


def apply_film_grain(frame_float: np.ndarray, strength: float, frame_index: int) -> np.ndarray:
    if strength <= 0.0:
        return frame_float
    rng = np.random.default_rng(seed=frame_index + 90210)
    mono_noise = rng.normal(0.0, 1.0, size=frame_float.shape[:2]).astype(np.float32)
    mono_noise = cv2.GaussianBlur(mono_noise, (0, 0), 0.6)
    noise = np.repeat(mono_noise[..., None], 3, axis=2)
    amount = strength * 0.07
    return np.clip(frame_float + noise * amount, 0.0, 1.0)

