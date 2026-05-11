from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np


def scale_zone_coords(
    frame: np.ndarray,
    stop_zone_coords: Optional[List[List[float]]],
    original_resolution: Optional[Dict[str, int]] = None,
) -> Optional[List[List[float]]]:
    """
    Масштабирует координаты зоны из original_resolution под текущее разрешение кадра.

    stop_zone_coords ожидаются в пикселях оригинального кадра.
    """
    if not stop_zone_coords:
        return stop_zone_coords
    if not original_resolution:
        return stop_zone_coords

    ow = int(original_resolution.get("width") or 0)
    oh = int(original_resolution.get("height") or 0)
    if ow <= 0 or oh <= 0:
        return stop_zone_coords

    h, w = frame.shape[:2]
    sx = w / float(ow)
    sy = h / float(oh)

    scaled: List[List[float]] = []
    for pt in stop_zone_coords:
        if not pt or len(pt) < 2:
            continue
        scaled.append([float(pt[0]) * sx, float(pt[1]) * sy])
    return scaled if scaled else stop_zone_coords

