from __future__ import annotations

import cv2
import numpy as np

from anime_celify.analyzer.base import Analyzer
from anime_celify.models import (
    PresetDefinition,
    ProcessingAdjustment,
    SceneSegment,
    ShotReasoningSummary,
    SuggestedConfig,
)
from anime_celify.processor.edges import extract_edge_mask
from anime_celify.processor.masks import estimate_skin_mask, estimate_subtitle_mask
from anime_celify.utils.image_ops import to_float01


class HeuristicAnalyzer(Analyzer):
    def analyze_scene(
        self,
        frame_bgr: np.ndarray,
        preset: PresetDefinition,
        scene: SceneSegment,
    ) -> SuggestedConfig:
        del scene
        features = _extract_features(frame_bgr)
        shot_profile = _classify_scene(features)
        adjustments = _build_adjustment(preset, shot_profile, features)
        reasoning = ShotReasoningSummary(
            scene_type=shot_profile,
            line_density=_bucket(features["edge_density"], low=0.03, high=0.085, labels=("low", "medium", "high")),
            palette_bias=_palette_bias(features),
            subtitle_present=bool(features["subtitle_ratio"] > 0.02),
            brightness=round(features["brightness"], 4),
            saturation=round(features["saturation"], 4),
            highlight_ratio=round(features["highlight_ratio"], 4),
            skin_ratio=round(features["skin_ratio"], 4),
            sky_ratio=round(features["sky_ratio"], 4),
            cool_ratio=round(features["cool_ratio"], 4),
        )
        return SuggestedConfig(
            preset_base=preset.name,
            shot_profile=shot_profile,
            adjustments=adjustments,
            reasoning_summary=reasoning,
        )


def _bucket(value: float, low: float, high: float, labels: tuple[str, str, str]) -> str:
    if value < low:
        return labels[0]
    if value < high:
        return labels[1]
    return labels[2]


def _palette_bias(features: dict[str, float]) -> str:
    if features["cool_ratio"] > 0.42:
        return "cool"
    if features["warm_ratio"] > 0.33:
        return "warm"
    return "neutral"


def _extract_features(frame_bgr: np.ndarray) -> dict[str, float]:
    frame_float = to_float01(frame_bgr)
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
    luminance = np.dot(frame_float, np.array([0.114, 0.587, 0.299], dtype=np.float32))
    edge_mask = extract_edge_mask(frame_bgr, edge_strength=0.6, line_thickness=1.0)
    skin_mask = estimate_skin_mask(frame_bgr)
    subtitle_mask = estimate_subtitle_mask(frame_bgr)

    blue_dominant = (frame_float[..., 0] > frame_float[..., 1] + 0.04) & (frame_float[..., 0] > frame_float[..., 2] + 0.04)
    cyan_dominant = (frame_float[..., 0] > 0.30) & (frame_float[..., 1] > 0.22) & (frame_float[..., 2] < frame_float[..., 1])
    warm_dominant = (frame_float[..., 2] > frame_float[..., 0] + 0.05) & (frame_float[..., 2] > frame_float[..., 1])
    top_half = slice(0, max(1, frame_bgr.shape[0] // 2))
    sky_mask = (
        (hsv[top_half, :, 1] < 0.35)
        & (hsv[top_half, :, 2] > 0.55)
        & (frame_float[top_half, :, 0] > frame_float[top_half, :, 2])
    )
    low_sat_bright = (hsv[..., 1] < 0.20) & (hsv[..., 2] > 0.72)
    dark_pixels = luminance < 0.20

    return {
        "brightness": float(np.mean(luminance)),
        "saturation": float(np.mean(hsv[..., 1])),
        "highlight_ratio": float(np.mean(luminance > 0.80)),
        "small_glow_ratio": float(np.mean((luminance > 0.82) & (hsv[..., 1] > 0.20))),
        "cool_ratio": float(np.mean(blue_dominant | cyan_dominant)),
        "warm_ratio": float(np.mean(warm_dominant)),
        "edge_density": float(np.mean(edge_mask > 0.15)),
        "skin_ratio": float(np.mean(skin_mask > 0.18)),
        "subtitle_ratio": float(np.mean(subtitle_mask > 0.12)),
        "sky_ratio": float(np.mean(sky_mask)),
        "low_sat_bright_ratio": float(np.mean(low_sat_bright)),
        "dark_ratio": float(np.mean(dark_pixels)),
    }


def _classify_scene(features: dict[str, float]) -> str:
    if (
        features["highlight_ratio"] > 0.20
        and features["low_sat_bright_ratio"] > 0.20
        and features["dark_ratio"] > 0.18
        and features["saturation"] < 0.30
    ):
        return "bio_mech_glow"
    if features["brightness"] < 0.42 and features["cool_ratio"] > 0.28:
        return "urban_night"
    return "neutral_daylight"


def _build_adjustment(
    preset: PresetDefinition,
    shot_profile: str,
    features: dict[str, float],
) -> ProcessingAdjustment:
    base_data: dict[str, float | bool] = {}
    preset_profile = preset.shot_profiles.get(shot_profile)
    if preset_profile is not None:
        base_data = preset_profile.model_dump(exclude_none=True)

    if shot_profile == "urban_night":
        base_data["line_blue_shift"] = float(base_data.get("line_blue_shift", 0.0)) + 0.02
        if features["small_glow_ratio"] > 0.04:
            base_data["halation_strength"] = float(base_data.get("halation_strength", 0.0)) + 0.02
        if features["cool_ratio"] > 0.45:
            base_data["midtone_shift_b"] = float(base_data.get("midtone_shift_b", 0.0)) + 0.01
            base_data["saturation_scale"] = float(base_data.get("saturation_scale", 0.0)) - 0.02
    elif shot_profile == "neutral_daylight":
        if features["skin_ratio"] > 0.10:
            base_data["skin_gray_shift"] = float(base_data.get("skin_gray_shift", 0.0)) + 0.02
        if features["sky_ratio"] > 0.14:
            base_data["highlight_rolloff"] = float(base_data.get("highlight_rolloff", 0.0)) + 0.01
    elif shot_profile == "bio_mech_glow":
        if features["highlight_ratio"] > 0.22:
            base_data["halation_strength"] = float(base_data.get("halation_strength", 0.0)) + 0.03
            base_data["highlight_rolloff"] = float(base_data.get("highlight_rolloff", 0.0)) + 0.02

    if features["subtitle_ratio"] > 0.02:
        base_data["subtitle_protect_enabled"] = True

    return ProcessingAdjustment.model_validate(base_data)
