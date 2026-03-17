from __future__ import annotations

from anime_celify.config import apply_adjustments, load_preset_definition
from anime_celify.models import ProcessingAdjustment


def test_apply_adjustments_changes_numeric_fields() -> None:
    preset = load_preset_definition("cyber_noir_95")
    adjusted = apply_adjustments(
        preset.processing,
        ProcessingAdjustment(
            saturation_scale=-0.05,
            halation_strength=0.02,
            subtitle_protect_enabled=True,
        ),
    )
    assert adjusted.saturation_scale == preset.processing.saturation_scale - 0.05
    assert adjusted.halation_strength == preset.processing.halation_strength + 0.02
    assert adjusted.subtitle_protect_enabled is True

