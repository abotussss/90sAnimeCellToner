from __future__ import annotations

import cv2
import numpy as np

from anime_celify.utils.image_ops import blend_mask, blue_black_color, mix


def extract_edge_mask(frame_bgr: np.ndarray, edge_strength: float, line_thickness: float) -> np.ndarray:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (0, 0), 1.0)
    low_threshold = int(max(20, 70 - edge_strength * 28))
    high_threshold = int(max(low_threshold + 20, 160 - edge_strength * 45))
    edges = cv2.Canny(gray, low_threshold, high_threshold).astype(np.float32) / 255.0
    if line_thickness > 1.0:
        kernel_size = max(1, int(round(line_thickness)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size * 2 + 1, kernel_size * 2 + 1))
        edges = cv2.dilate(edges, kernel, iterations=1)
    return blend_mask(edges, blur_sigma=1.2)


def apply_line_emphasis(
    frame_float: np.ndarray,
    edge_mask: np.ndarray,
    edge_strength: float,
    blue_shift: float,
) -> np.ndarray:
    if edge_strength <= 0.0:
        return frame_float
    line_color = blue_black_color(blue_shift).reshape(1, 1, 3)
    amount = np.clip(edge_mask[..., None] * edge_strength * 0.62, 0.0, 0.78)
    line_target = np.minimum(frame_float * 0.35 + np.broadcast_to(line_color, frame_float.shape) * 0.65, frame_float)
    return mix(frame_float, line_target, amount)
