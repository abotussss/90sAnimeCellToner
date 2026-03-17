from __future__ import annotations

import math

import cv2
import numpy as np


def to_float01(frame_bgr: np.ndarray) -> np.ndarray:
    return frame_bgr.astype(np.float32) / 255.0


def to_uint8(frame_float: np.ndarray) -> np.ndarray:
    return np.clip(frame_float * 255.0, 0, 255).astype(np.uint8)


def posterize_channel(channel: np.ndarray, levels: int) -> np.ndarray:
    if levels <= 1:
        return channel
    scaled = np.round(channel * (levels - 1)) / float(levels - 1)
    return np.clip(scaled, 0.0, 1.0)


def apply_gamma(frame: np.ndarray, gamma: float) -> np.ndarray:
    safe_gamma = max(gamma, 1e-3)
    return np.power(np.clip(frame, 0.0, 1.0), 1.0 / safe_gamma)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / max(edge1 - edge0, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def apply_vignette(frame: np.ndarray, strength: float) -> np.ndarray:
    if strength <= 0.0:
        return frame
    height, width = frame.shape[:2]
    ys = np.linspace(-1.0, 1.0, height, dtype=np.float32)
    xs = np.linspace(-1.0, 1.0, width, dtype=np.float32)
    grid_y, grid_x = np.meshgrid(ys, xs, indexing="ij")
    distance = np.sqrt(grid_x**2 + grid_y**2)
    mask = 1.0 - strength * np.clip(distance**1.6, 0.0, 1.0)
    return np.clip(frame * mask[..., None], 0.0, 1.0)


def build_center_weight(height: int, width: int) -> np.ndarray:
    ys = np.linspace(-1.0, 1.0, height, dtype=np.float32)
    xs = np.linspace(-1.0, 1.0, width, dtype=np.float32)
    grid_y, grid_x = np.meshgrid(ys, xs, indexing="ij")
    sigma_x = 0.85
    sigma_y = 0.75
    return np.exp(-((grid_x**2) / (2 * sigma_x**2) + (grid_y**2) / (2 * sigma_y**2)))


def resize_flow(flow: np.ndarray, width: int, height: int, scale: float) -> np.ndarray:
    resized = cv2.resize(flow, (width, height), interpolation=cv2.INTER_LINEAR)
    return resized / max(scale, 1e-6)


def bgr_to_lab_float(frame_bgr_float: np.ndarray) -> np.ndarray:
    frame_u8 = to_uint8(frame_bgr_float)
    lab_u8 = cv2.cvtColor(frame_u8, cv2.COLOR_BGR2LAB)
    return lab_u8.astype(np.float32) / 255.0


def lab_float_to_bgr(frame_lab_float: np.ndarray) -> np.ndarray:
    lab_u8 = np.clip(frame_lab_float * 255.0, 0, 255).astype(np.uint8)
    bgr_u8 = cv2.cvtColor(lab_u8, cv2.COLOR_LAB2BGR)
    return bgr_u8.astype(np.float32) / 255.0


def mix(base: np.ndarray, overlay: np.ndarray, amount: np.ndarray | float) -> np.ndarray:
    return np.clip(base * (1.0 - amount) + overlay * amount, 0.0, 1.0)


def blue_black_color(blue_shift: float) -> np.ndarray:
    blue = 0.10 + blue_shift * 0.35
    green = 0.08 + blue_shift * 0.10
    red = 0.07
    return np.array([blue, green, red], dtype=np.float32)


def quantize_lab(
    frame_bgr_float: np.ndarray,
    luma_levels: int,
    chroma_levels: int,
) -> np.ndarray:
    lab = bgr_to_lab_float(frame_bgr_float)
    lab[..., 0] = posterize_channel(lab[..., 0], luma_levels)
    lab[..., 1] = posterize_channel(lab[..., 1], chroma_levels)
    lab[..., 2] = posterize_channel(lab[..., 2], chroma_levels)
    return lab_float_to_bgr(lab)


def blend_mask(mask: np.ndarray, blur_sigma: float = 3.0) -> np.ndarray:
    if blur_sigma <= 0.0:
        return np.clip(mask, 0.0, 1.0)
    ksize = max(3, int(math.ceil(blur_sigma * 3) * 2 + 1))
    return cv2.GaussianBlur(np.clip(mask, 0.0, 1.0), (ksize, ksize), blur_sigma)

