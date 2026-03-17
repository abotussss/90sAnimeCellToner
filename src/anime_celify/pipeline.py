from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from anime_celify.analyzer.heuristic_analyzer import HeuristicAnalyzer
from anime_celify.config import apply_adjustments
from anime_celify.io.reader import VideoReader
from anime_celify.io.writer import OpenCVTempWriter
from anime_celify.models import (
    PresetDefinition,
    SceneConfigAssignment,
    SceneSegment,
    SuggestedConfig,
    TransformRunLog,
)
from anime_celify.processor.color import apply_cel_color_grade
from anime_celify.processor.edges import apply_line_emphasis, extract_edge_mask
from anime_celify.processor.grain import apply_film_grain
from anime_celify.processor.halation import apply_selective_halation
from anime_celify.processor.masks import (
    estimate_emissive_mask,
    estimate_foreground_mask,
    estimate_skin_mask,
    estimate_subtitle_mask,
)
from anime_celify.processor.smoothing import apply_background_softness, apply_edge_preserving_smoothing
from anime_celify.processor.temporal import TemporalStabilizer
from anime_celify.probe import probe_video
from anime_celify.scene_detect import detect_scenes
from anime_celify.utils.image_ops import apply_vignette, mix, to_float01, to_uint8


def analyze_video(input_path: Path, preset_definition: PresetDefinition) -> list[SuggestedConfig]:
    metadata = probe_video(input_path)
    scenes = detect_scenes(input_path, metadata)
    analyzer = HeuristicAnalyzer()
    suggestions: list[SuggestedConfig] = []
    with VideoReader(input_path) as reader:
        for scene in scenes:
            frame = reader.read_frame(min(scene.mid_frame, metadata.frame_count_estimate - 1))
            suggestions.append(analyzer.analyze_scene(frame, preset_definition, scene))
    return suggestions


def transform_video(
    input_path: Path,
    output_path: Path,
    preset_definition: PresetDefinition,
    auto_tune: bool = False,
    log_path: Path | None = None,
) -> TransformRunLog:
    metadata = probe_video(input_path)
    scenes = detect_scenes(input_path, metadata)
    suggestions = _suggest_scene_configs(input_path, preset_definition, scenes, metadata.frame_count_estimate) if auto_tune else []
    assignments = _build_assignments(preset_definition, scenes, suggestions)

    writer = OpenCVTempWriter(width=metadata.width, height=metadata.height, fps=metadata.fps)
    stabilizer = TemporalStabilizer()
    current_scene_index = 0

    with VideoReader(input_path) as reader:
        for video_frame in reader.iter_frames():
            while (
                current_scene_index < len(assignments) - 1
                and video_frame.index >= assignments[current_scene_index].scene.end_frame
            ):
                current_scene_index += 1
                stabilizer.reset()
            assignment = assignments[current_scene_index]
            processed = _process_frame(
                frame_bgr=video_frame.frame_bgr,
                scene_assignment=assignment,
                stabilizer=stabilizer,
                frame_index=video_frame.index,
            )
            writer.write(processed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer.finalize(source_video_path=input_path, output_path=output_path)
    run_log = TransformRunLog(
        input_path=input_path,
        output_path=output_path,
        preset_name=preset_definition.name,
        auto_tune_enabled=auto_tune,
        input_metadata=metadata,
        scenes=assignments,
        warnings=[],
        notes={
            "audio_behavior": "Video is re-encoded with H.264, source audio is copied when present.",
            "mvp_limit": "Only mp4 clips up to 15 seconds are supported.",
        },
    )
    _write_run_log(run_log, log_path=log_path or output_path.with_suffix(".transform_log.json"))
    return run_log


def _suggest_scene_configs(
    input_path: Path,
    preset_definition: PresetDefinition,
    scenes: list[SceneSegment],
    frame_count_estimate: int,
) -> list[SuggestedConfig]:
    analyzer = HeuristicAnalyzer()
    suggestions: list[SuggestedConfig] = []
    with VideoReader(input_path) as reader:
        for scene in scenes:
            frame = reader.read_frame(min(scene.mid_frame, frame_count_estimate - 1))
            suggestions.append(analyzer.analyze_scene(frame, preset_definition, scene))
    return suggestions


def _build_assignments(
    preset_definition: PresetDefinition,
    scenes: list[SceneSegment],
    suggestions: list[SuggestedConfig],
) -> list[SceneConfigAssignment]:
    suggestion_by_index = {index: suggestion for index, suggestion in enumerate(suggestions)}
    assignments: list[SceneConfigAssignment] = []
    for scene in scenes:
        suggestion = suggestion_by_index.get(scene.index)
        processing = (
            apply_adjustments(preset_definition.processing, suggestion.adjustments)
            if suggestion is not None
            else preset_definition.processing
        )
        assignments.append(
            SceneConfigAssignment(
                scene=scene,
                applied_preset_name=preset_definition.name,
                shot_profile=suggestion.shot_profile if suggestion else None,
                processing=processing,
                suggestion=suggestion,
            )
        )
    return assignments


def _process_frame(
    frame_bgr: np.ndarray,
    scene_assignment: SceneConfigAssignment,
    stabilizer: TemporalStabilizer,
    frame_index: int,
) -> np.ndarray:
    config = scene_assignment.processing
    edge_mask = extract_edge_mask(frame_bgr, config.edge_strength, config.line_thickness)
    skin_mask = estimate_skin_mask(frame_bgr)
    foreground_mask = estimate_foreground_mask(frame_bgr, edge_mask=edge_mask, skin_mask=skin_mask)
    emissive_mask = estimate_emissive_mask(frame_bgr, threshold=config.emissive_mask_threshold)
    subtitle_mask = estimate_subtitle_mask(frame_bgr) if config.subtitle_protect_enabled else np.zeros(frame_bgr.shape[:2], dtype=np.float32)

    smoothed = apply_edge_preserving_smoothing(frame_bgr, config.smoothing_strength)
    softened = apply_background_softness(smoothed, foreground_mask, softness=config.background_softness, blur_radius=config.blur_radius)
    graded = apply_cel_color_grade(softened, config=config, skin_mask=skin_mask)
    lined = apply_line_emphasis(graded, edge_mask=edge_mask, edge_strength=config.edge_strength, blue_shift=config.line_blue_shift)

    if config.blur_radius > 0.0:
        glow_base = cv2.GaussianBlur(lined, (0, 0), max(0.4, config.blur_radius * 0.35))
        lined = mix(lined, glow_base, 0.06)

    halated = apply_selective_halation(
        lined,
        emissive_mask=emissive_mask,
        strength=config.halation_strength,
        radius=config.halation_radius,
    )
    vignetted = apply_vignette(halated, config.vignette_strength)
    grained = apply_film_grain(vignetted, config.grain_strength, frame_index=frame_index)

    if config.subtitle_protect_enabled:
        original_float = to_float01(frame_bgr)
        grained = mix(grained, original_float, subtitle_mask[..., None] * 0.70)

    stabilized = stabilizer.stabilize(
        original_bgr=frame_bgr,
        processed_float=grained,
        temporal_blend=config.temporal_blend,
        optical_flow_consistency=config.optical_flow_consistency,
    )
    return to_uint8(stabilized)


def _write_run_log(run_log: TransformRunLog, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(run_log.model_dump(mode="json"), indent=2), encoding="utf-8")

