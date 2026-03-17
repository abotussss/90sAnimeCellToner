from __future__ import annotations

import cv2
import numpy as np

from anime_celify.utils.image_ops import blend_mask, build_center_weight, to_float01


def estimate_skin_mask(frame_bgr: np.ndarray) -> np.ndarray:
    ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    cr = ycrcb[..., 1]
    cb = ycrcb[..., 2]
    sat = hsv[..., 1]
    val = hsv[..., 2]
    mask = (
        (cr >= 135)
        & (cr <= 185)
        & (cb >= 85)
        & (cb <= 140)
        & (sat >= 25)
        & (val >= 35)
    )
    return blend_mask(mask.astype(np.float32), blur_sigma=2.0)


def estimate_subtitle_mask(frame_bgr: np.ndarray) -> np.ndarray:
    height, width = frame_bgr.shape[:2]
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    _, threshold = cv2.threshold(gray, 210, 1.0, cv2.THRESH_BINARY)
    edges = cv2.Canny(gray, 80, 160).astype(np.float32) / 255.0
    mask = threshold * np.clip(edges + 0.4, 0.0, 1.0)
    vertical_start = int(height * 0.72)
    limited = np.zeros((height, width), dtype=np.float32)
    limited[vertical_start:, :] = mask[vertical_start:, :]
    return blend_mask(limited, blur_sigma=1.5)


def estimate_emissive_mask(frame_bgr: np.ndarray, threshold: float) -> np.ndarray:
    frame_float = to_float01(frame_bgr)
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
    luminance = np.dot(frame_float, np.array([0.114, 0.587, 0.299], dtype=np.float32))
    value = hsv[..., 2]
    saturation = hsv[..., 1]
    local_luminance = cv2.GaussianBlur(luminance, (0, 0), 5.0)
    bright_mask = (luminance > threshold) & (value > threshold)
    contrast_peak = luminance > (local_luminance + 0.045)
    emissive = bright_mask & (contrast_peak | ((saturation > 0.16) & (luminance > threshold + 0.04)))
    return blend_mask(emissive.astype(np.float32), blur_sigma=3.0)


def estimate_foreground_mask(
    frame_bgr: np.ndarray,
    edge_mask: np.ndarray,
    skin_mask: np.ndarray,
) -> np.ndarray:
    height, width = frame_bgr.shape[:2]
    center_weight = build_center_weight(height, width)
    local_edges = cv2.GaussianBlur(edge_mask, (0, 0), 6.0)
    foreground = 0.45 * local_edges + 0.40 * skin_mask + 0.25 * center_weight
    return np.clip(foreground, 0.0, 1.0)
