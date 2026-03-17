from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from anime_celify.models import PresetDefinition, SceneSegment, SuggestedConfig


class Analyzer(ABC):
    @abstractmethod
    def analyze_scene(
        self,
        frame_bgr: np.ndarray,
        preset: PresetDefinition,
        scene: SceneSegment,
    ) -> SuggestedConfig:
        """Return scene-local parameter suggestions."""

