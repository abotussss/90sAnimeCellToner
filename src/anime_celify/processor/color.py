from __future__ import annotations

import cv2
import numpy as np

from anime_celify.models import ProcessingConfig
from anime_celify.utils.image_ops import apply_gamma, mix, quantize_lab, smoothstep, to_float01


def adjust_saturation(frame_float: np.ndarray, saturation_scale: float) -> np.ndarray:
    hsv = cv2.cvtColor((frame_float * 255.0).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
    hsv[..., 1] = np.clip(hsv[..., 1] * saturation_scale, 0.0, 1.0)
    return cv2.cvtColor((hsv * 255.0).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32) / 255.0


def _apply_shadow_partition(frame_float: np.ndarray, shadow_crush: float) -> np.ndarray:
    luminance = np.dot(frame_float, np.array([0.114, 0.587, 0.299], dtype=np.float32))
    thresholds = np.array([0.16, 0.34, 0.54, 0.76], dtype=np.float32)
    levels = np.array([0.09, 0.23, 0.40, 0.60, 0.84], dtype=np.float32)
    indices = np.digitize(luminance, thresholds)
    target_luminance = levels[indices]
    scale = target_luminance / np.maximum(luminance, 1e-4)
    cel_partitioned = np.clip(frame_float * scale[..., None], 0.0, 1.0)
    shadow_mid_mask = 1.0 - smoothstep(0.72, 0.92, luminance)
    amount = np.clip(0.20 + shadow_crush * 1.6, 0.18, 0.48)
    return mix(frame_float, cel_partitioned, shadow_mid_mask[..., None] * amount)


def _apply_reference_palette(
    frame_float: np.ndarray,
    original_float: np.ndarray,
    skin_mask: np.ndarray,
    foreground_mask: np.ndarray,
    config: ProcessingConfig,
) -> np.ndarray:
    if config.palette_mix_strength <= 0.0:
        return frame_float

    luminance = np.dot(frame_float, np.array([0.114, 0.587, 0.299], dtype=np.float32))
    shadow_mask = 1.0 - smoothstep(0.12, 0.42, luminance)
    midtone_mask = np.exp(-((luminance - 0.47) ** 2) / 0.05)
    highlight_mask = smoothstep(0.62, 0.92, luminance)
    background_mask = 1.0 - np.clip(foreground_mask, 0.0, 1.0)

    shadow_target = np.array(
        [
            0.15 + config.shadow_cool_tint * 0.15,
            0.12 + config.shadow_cool_tint * 0.08,
            0.08 + config.shadow_cool_tint * 0.03,
        ],
        dtype=np.float32,
    )
    midtone_target = np.array(
        [
            0.38 + config.palette_mix_strength * 0.12,
            0.36 + config.palette_mix_strength * 0.09 + config.shadow_cool_tint * 0.04,
            0.30 - config.highlight_warm_tint * 0.03,
        ],
        dtype=np.float32,
    )
    highlight_target = np.array(
        [
            0.86 - config.highlight_warm_tint * 0.07,
            0.87 - config.highlight_warm_tint * 0.01,
            0.88 + config.highlight_warm_tint * 0.05,
        ],
        dtype=np.float32,
    )

    weight_sum = shadow_mask + midtone_mask + highlight_mask + 1e-6
    palette_target = (
        shadow_target * shadow_mask[..., None]
        + midtone_target * midtone_mask[..., None]
        + highlight_target * highlight_mask[..., None]
    ) / weight_sum[..., None]

    palette_amount = (
        config.palette_mix_strength * 0.14
        + shadow_mask * config.palette_mix_strength * 0.16
        + midtone_mask * config.palette_mix_strength * 0.10
        + background_mask * config.background_palette_strength * 0.32
    )
    frame = mix(frame_float, palette_target, np.clip(palette_amount[..., None], 0.0, 0.58))

    grayscale = np.repeat(luminance[..., None], 3, axis=2)
    skin_target = (
        original_float * 0.52
        + grayscale * 0.20
        + np.array([0.67, 0.64, 0.59], dtype=np.float32).reshape(1, 1, 3) * 0.28
    )
    skin_amount = np.clip(
        config.skin_gray_shift * 0.55 + config.palette_mix_strength * 0.10,
        0.0,
        0.40,
    )
    return mix(frame, skin_target, skin_mask[..., None] * skin_amount)


def apply_cel_color_grade(
    frame_bgr: np.ndarray,
    config: ProcessingConfig,
    skin_mask: np.ndarray,
    foreground_mask: np.ndarray,
) -> np.ndarray:
    original = to_float01(frame_bgr)
    frame = apply_gamma(original, config.gamma)
    frame = np.clip((frame - 0.5) * config.contrast_scale + 0.5, 0.0, 1.0)
    frame = adjust_saturation(frame, config.saturation_scale)

    luminance = np.dot(frame, np.array([0.114, 0.587, 0.299], dtype=np.float32))
    shadow_mask = 1.0 - smoothstep(0.08, 0.48, luminance)
    highlight_mask = smoothstep(0.68, 0.98, luminance)
    midtone_mask = np.exp(-((luminance - 0.52) ** 2) / 0.035)

    frame *= 1.0 - shadow_mask[..., None] * config.shadow_crush * 0.45
    frame = np.clip(frame, 0.0, 1.0)
    frame = frame - np.maximum(frame - 0.75, 0.0) * config.highlight_rolloff * highlight_mask[..., None] * 1.5

    frame[..., 0] = np.clip(frame[..., 0] + midtone_mask * config.midtone_shift_b, 0.0, 1.0)
    frame[..., 1] = np.clip(frame[..., 1] + midtone_mask * config.midtone_shift_g, 0.0, 1.0)
    frame[..., 2] = np.clip(frame[..., 2] + midtone_mask * config.midtone_shift_r, 0.0, 1.0)
    frame = _apply_shadow_partition(frame, config.shadow_crush)
    frame = _apply_reference_palette(frame, original, skin_mask, foreground_mask, config)

    grayscale = np.repeat(luminance[..., None], 3, axis=2)
    if config.skin_desaturate > 0.0:
        frame = mix(frame, grayscale, skin_mask[..., None] * config.skin_desaturate * 0.45)
    if config.skin_gray_shift > 0.0:
        skin_reference = original * 0.75 + grayscale * 0.25
        frame = mix(frame, skin_reference, skin_mask[..., None] * config.skin_gray_shift)
    if config.skin_protect_strength > 0.0:
        frame = mix(frame, original, skin_mask[..., None] * config.skin_protect_strength * 0.20)

    frame = quantize_lab(frame, config.posterize_luma_levels or 5, config.posterize_chroma_levels or 4)
    return np.clip(frame, 0.0, 1.0)


def apply_finish_grade(frame_float: np.ndarray, config: ProcessingConfig) -> np.ndarray:
    final_saturation_scale = min(1.0, max(0.0, config.saturation_scale * 0.76))
    frame = adjust_saturation(frame_float, final_saturation_scale)

    luminance = np.dot(frame, np.array([0.114, 0.587, 0.299], dtype=np.float32))
    midtone_mask = np.exp(-((luminance - 0.48) ** 2) / 0.055)
    shadow_mask = 1.0 - smoothstep(0.06, 0.34, luminance)
    highlight_mask = smoothstep(0.70, 0.95, luminance)

    frame[..., 0] = np.clip(frame[..., 0] + midtone_mask * config.midtone_shift_b * 0.34, 0.0, 1.0)
    frame[..., 1] = np.clip(frame[..., 1] + midtone_mask * config.midtone_shift_g * 0.14, 0.0, 1.0)
    frame[..., 2] = np.clip(frame[..., 2] + shadow_mask * config.midtone_shift_r * 0.14, 0.0, 1.0)
    frame = frame - np.maximum(frame - 0.80, 0.0) * config.highlight_rolloff * highlight_mask[..., None] * 0.75

    return np.clip(frame, 0.0, 1.0)
