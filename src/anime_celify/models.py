from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProcessingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    smoothing_strength: float = Field(ge=0.0, le=1.0)
    edge_strength: float = Field(ge=0.0, le=1.5)
    line_thickness: float = Field(ge=0.5, le=3.0)
    saturation_scale: float = Field(ge=0.0, le=2.0)
    contrast_scale: float = Field(ge=0.5, le=2.0)
    gamma: float = Field(ge=0.5, le=1.5)
    shadow_crush: float = Field(ge=-0.5, le=0.5)
    highlight_rolloff: float = Field(ge=-0.5, le=0.5)
    midtone_shift_r: float = Field(ge=-0.3, le=0.3)
    midtone_shift_g: float = Field(ge=-0.3, le=0.3)
    midtone_shift_b: float = Field(ge=-0.3, le=0.3)
    halation_strength: float = Field(ge=0.0, le=1.0)
    grain_strength: float = Field(ge=0.0, le=0.5)
    temporal_blend: float = Field(ge=0.0, le=1.0)
    optical_flow_consistency: float = Field(ge=0.0, le=1.0)
    vignette_strength: float = Field(ge=0.0, le=0.5)
    background_softness: float = Field(ge=0.0, le=1.0)
    skin_protect_strength: float = Field(default=0.10, ge=0.0, le=1.0)
    subtitle_protect_enabled: bool = True
    posterize_levels: int | None = Field(default=None, ge=2, le=16)
    blur_radius: float = Field(default=1.0, ge=0.0, le=8.0)
    line_blue_shift: float = Field(default=0.08, ge=0.0, le=0.5)
    posterize_luma_levels: int | None = Field(default=None, ge=2, le=16)
    posterize_chroma_levels: int | None = Field(default=None, ge=2, le=16)
    skin_desaturate: float = Field(default=0.10, ge=0.0, le=1.0)
    skin_gray_shift: float = Field(default=0.05, ge=0.0, le=0.5)
    halation_radius: float = Field(default=2.0, ge=0.5, le=8.0)
    emissive_mask_threshold: float = Field(default=0.78, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def resolve_posterize_defaults(self) -> "ProcessingConfig":
        if self.posterize_levels is not None:
            if self.posterize_luma_levels is None:
                self.posterize_luma_levels = self.posterize_levels
            if self.posterize_chroma_levels is None:
                self.posterize_chroma_levels = max(2, self.posterize_levels - 1)
        if self.posterize_luma_levels is None:
            self.posterize_luma_levels = 5
        if self.posterize_chroma_levels is None:
            self.posterize_chroma_levels = 4
        return self


class ProcessingAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    smoothing_strength: float | None = None
    edge_strength: float | None = None
    line_thickness: float | None = None
    saturation_scale: float | None = None
    contrast_scale: float | None = None
    gamma: float | None = None
    shadow_crush: float | None = None
    highlight_rolloff: float | None = None
    midtone_shift_r: float | None = None
    midtone_shift_g: float | None = None
    midtone_shift_b: float | None = None
    halation_strength: float | None = None
    grain_strength: float | None = None
    temporal_blend: float | None = None
    optical_flow_consistency: float | None = None
    vignette_strength: float | None = None
    background_softness: float | None = None
    skin_protect_strength: float | None = None
    posterize_levels: float | None = None
    blur_radius: float | None = None
    line_blue_shift: float | None = None
    posterize_luma_levels: float | None = None
    posterize_chroma_levels: float | None = None
    skin_desaturate: float | None = None
    skin_gray_shift: float | None = None
    halation_radius: float | None = None
    emissive_mask_threshold: float | None = None
    subtitle_protect_enabled: bool | None = None

    def numeric_items(self) -> dict[str, float]:
        return {
            key: value
            for key, value in self.model_dump(exclude_none=True).items()
            if isinstance(value, (int, float))
        }


class PresetDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    processing: ProcessingConfig
    shot_profiles: dict[str, ProcessingAdjustment] = Field(default_factory=dict)


class VideoMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    duration_seconds: float = Field(gt=0.0)
    fps: float = Field(gt=0.0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    codec_name: str
    has_audio: bool = False
    audio_codec_name: str | None = None
    frame_count_estimate: int = Field(gt=0)


class SceneSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(gt=0.0)
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)

    @property
    def mid_frame(self) -> int:
        return self.start_frame + max(0, (self.end_frame - self.start_frame) // 2)


class ShotReasoningSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_type: str
    line_density: str
    palette_bias: str
    subtitle_present: bool
    brightness: float
    saturation: float
    highlight_ratio: float
    skin_ratio: float
    sky_ratio: float
    cool_ratio: float


class SuggestedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset_base: str
    shot_profile: str
    adjustments: ProcessingAdjustment
    reasoning_summary: ShotReasoningSummary


class SceneConfigAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: SceneSegment
    applied_preset_name: str
    shot_profile: str | None = None
    processing: ProcessingConfig
    suggestion: SuggestedConfig | None = None


class TransformRunLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_path: Path
    output_path: Path
    preset_name: str
    auto_tune_enabled: bool
    input_metadata: VideoMetadata
    scenes: list[SceneConfigAssignment]
    warnings: list[str] = Field(default_factory=list)
    notes: dict[str, Any] = Field(default_factory=dict)

