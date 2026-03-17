from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Iterable

import yaml

from anime_celify.models import (
    PresetDefinition,
    ProcessingAdjustment,
    ProcessingConfig,
)

PRESET_PACKAGE = "anime_celify.presets"


class ConfigError(RuntimeError):
    """Raised when preset or config files cannot be resolved."""


def _clamp_config(data: dict[str, object]) -> ProcessingConfig:
    return ProcessingConfig.model_validate(data)


def apply_adjustments(
    base_config: ProcessingConfig,
    adjustments: ProcessingAdjustment | None,
) -> ProcessingConfig:
    if adjustments is None:
        return base_config

    merged = base_config.model_dump()
    for field_name, delta in adjustments.numeric_items().items():
        base_value = merged.get(field_name)
        if isinstance(base_value, bool) or base_value is None:
            continue
        if field_name in {"posterize_levels", "posterize_luma_levels", "posterize_chroma_levels"}:
            merged[field_name] = int(round(float(base_value) + delta))
        else:
            merged[field_name] = float(base_value) + float(delta)

    if adjustments.subtitle_protect_enabled is not None:
        merged["subtitle_protect_enabled"] = adjustments.subtitle_protect_enabled

    return _clamp_config(merged)


def _load_yaml(path: Path) -> dict[str, object]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc


def load_preset_definition(name: str) -> PresetDefinition:
    preset_dir = files(PRESET_PACKAGE)
    target = preset_dir.joinpath(f"{name}.yaml")
    if not target.is_file():
        available = ", ".join(list_presets())
        raise ConfigError(f"Unknown preset '{name}'. Available presets: {available}")
    return PresetDefinition.model_validate(yaml.safe_load(target.read_text(encoding="utf-8")))


def load_config_file(path: Path) -> PresetDefinition:
    suffix = path.suffix.lower()
    raw = _load_yaml(path) if suffix in {".yaml", ".yml"} else json.loads(path.read_text(encoding="utf-8"))
    return PresetDefinition.model_validate(raw)


def list_presets() -> list[str]:
    preset_dir = files(PRESET_PACKAGE)
    return sorted(
        entry.name.rsplit(".", 1)[0]
        for entry in preset_dir.iterdir()
        if entry.name.endswith(".yaml")
    )


def show_preset_yaml(name: str) -> str:
    preset = load_preset_definition(name)
    return yaml.safe_dump(preset.model_dump(mode="json"), sort_keys=False, allow_unicode=False)


def resolve_preset(
    preset_name: str | None = None,
    config_path: Path | None = None,
) -> PresetDefinition:
    if preset_name and config_path:
        raise ConfigError("Use either --preset or --config, not both.")
    if config_path:
        return load_config_file(config_path)
    if preset_name:
        return load_preset_definition(preset_name)
    raise ConfigError("Either --preset or --config is required.")


def apply_shot_profile(
    preset: PresetDefinition,
    shot_profile_name: str | None,
) -> ProcessingConfig:
    if not shot_profile_name:
        return preset.processing
    return apply_adjustments(
        base_config=preset.processing,
        adjustments=preset.shot_profiles.get(shot_profile_name),
    )


def available_profile_names(preset: PresetDefinition) -> Iterable[str]:
    return preset.shot_profiles.keys()

