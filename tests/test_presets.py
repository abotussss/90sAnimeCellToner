from __future__ import annotations

from anime_celify.config import list_presets, load_preset_definition


def test_builtin_presets_exist() -> None:
    presets = list_presets()
    assert "cyber_noir_95" in presets
    assert "tv_mecha_95" in presets
    assert "sports_cel_warm" in presets


def test_cyber_noir_preset_has_shot_profiles() -> None:
    preset = load_preset_definition("cyber_noir_95")
    assert preset.processing.line_blue_shift > 0.0
    assert set(preset.shot_profiles) == {"urban_night", "neutral_daylight", "bio_mech_glow"}

