from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from anime_celify.utils.image_ops import mix, resize_flow


@dataclass
class TemporalState:
    previous_original_gray_small: np.ndarray | None = None
    previous_processed: np.ndarray | None = None


class TemporalStabilizer:
    def __init__(self, downscale: float = 0.5) -> None:
        self.downscale = downscale
        self.state = TemporalState()

    def reset(self) -> None:
        self.state = TemporalState()

    def stabilize(
        self,
        original_bgr: np.ndarray,
        processed_float: np.ndarray,
        temporal_blend: float,
        optical_flow_consistency: float,
    ) -> np.ndarray:
        gray = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.resize(gray, (0, 0), fx=self.downscale, fy=self.downscale, interpolation=cv2.INTER_AREA)

        if self.state.previous_processed is None or temporal_blend <= 0.0:
            self.state.previous_original_gray_small = small_gray
            self.state.previous_processed = processed_float
            return processed_float

        previous_processed = self.state.previous_processed
        previous_gray_small = self.state.previous_original_gray_small
        blended_reference = previous_processed

        if previous_gray_small is not None and optical_flow_consistency > 0.0:
            flow_small = cv2.calcOpticalFlowFarneback(
                small_gray,
                previous_gray_small,
                None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0,
            )
            height, width = gray.shape[:2]
            flow = resize_flow(flow_small, width=width, height=height, scale=self.downscale)
            grid_x, grid_y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
            map_x = grid_x + flow[..., 0]
            map_y = grid_y + flow[..., 1]
            blended_reference = cv2.remap(
                previous_processed.astype(np.float32),
                map_x,
                map_y,
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT,
            )

        amount = min(0.5, temporal_blend * (0.65 + optical_flow_consistency * 0.35))
        stabilized = mix(processed_float, blended_reference, amount)
        self.state.previous_original_gray_small = small_gray
        self.state.previous_processed = stabilized
        return stabilized

