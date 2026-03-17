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
    halo_mask = cv2.GaussianBlur(np.clip(emissive_mask, 0.0, 1.0), (0, 0), sigma * 1.2)
    milky = np.clip(blurred * 0.78 + 0.22, 0.0, 1.0)
    amount = np.clip(halo_mask[..., None] * strength * 0.72, 0.0, 0.52)
    return mix(frame_float, np.maximum(frame_float, milky), amount)
