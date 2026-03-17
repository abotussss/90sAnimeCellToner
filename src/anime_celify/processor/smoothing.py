from __future__ import annotations

import cv2
import numpy as np

from anime_celify.utils.image_ops import mix, to_float01, to_uint8


def apply_edge_preserving_smoothing(frame_bgr: np.ndarray, strength: float) -> np.ndarray:
    if strength <= 0.0:
        return frame_bgr
    sigma_color = 20.0 + strength * 55.0
    sigma_space = 5.0 + strength * 18.0
    return cv2.bilateralFilter(frame_bgr, d=0, sigmaColor=sigma_color, sigmaSpace=sigma_space)


def apply_background_softness(
    frame_bgr: np.ndarray,
    foreground_mask: np.ndarray,
    softness: float,
    blur_radius: float,
) -> np.ndarray:
    if softness <= 0.0:
        return frame_bgr
    frame_float = to_float01(frame_bgr)
    sigma = max(0.6, blur_radius + softness * 2.5)
    blurred = cv2.GaussianBlur(frame_float, (0, 0), sigma)
    background_mask = (1.0 - np.clip(foreground_mask, 0.0, 1.0))[..., None] * min(1.0, softness * 0.9)
    return to_uint8(mix(frame_float, blurred, background_mask))

