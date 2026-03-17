from __future__ import annotations

import cv2
import numpy as np

from anime_celify.utils.image_ops import mix


def apply_selective_halation(
    frame_float: np.ndarray,
    emissive_mask: np.ndarray,
    strength: float,
    radius: float,
) -> np.ndarray:
    if strength <= 0.0:
        return frame_float
    sigma = max(0.8, radius)
    blurred = cv2.GaussianBlur(frame_float, (0, 0), sigma)
    milky = np.clip(blurred * 0.82 + 0.18, 0.0, 1.0)
    amount = np.clip(emissive_mask[..., None] * strength * 0.85, 0.0, 0.6)
    return mix(frame_float, np.maximum(frame_float, milky), amount)

