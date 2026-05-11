from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple


BBox = Tuple[float, float, float, float]  # x1, y1, x2, y2
ZoneRect = Tuple[float, float, float, float]  # x1, y1, x2, y2


def _center(bbox: BBox) -> Tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def point_in_rect(px: float, py: float, rect: ZoneRect) -> bool:
    x1, y1, x2, y2 = rect
    return x1 <= px <= x2 and y1 <= py <= y2


@dataclass
class TrackState:
    track_id: int
    created_at: datetime
    last_update_at: datetime
    last_seen_at: datetime
    last_bbox: Optional[BBox]
    last_in_zone: bool
    time_in_zone_s: float = 0.0


class WaitingTracker:
    """
    Трекер ожидания на остановке поверх любых track_id.

    Идея:
    - если трек в зоне, накапливаем время в зоне
    - если трек "пропал", но его последнее положение было в зоне, мы продолжаем считать,
      что он в зоне до `missing_ttl_s` (окклюзия/перекрытие)
    """

    def __init__(
        self,
        wait_threshold_s: float = 10.0,
        missing_ttl_s: float = 2.0,
        prune_after_s: float = 30.0,
    ):
        self.wait_threshold_s = float(wait_threshold_s)
        self.missing_ttl_s = float(missing_ttl_s)
        self.prune_after_s = float(prune_after_s)
        self._tracks: Dict[int, TrackState] = {}

    def reset(self) -> None:
        self._tracks.clear()

    def update(
        self,
        *,
        now: datetime,
        observations: Iterable[Tuple[int, BBox]],
        stop_zone: Optional[ZoneRect],
    ) -> List[dict]:
        """
        Args:
            now: текущее время кадра/обработки
            observations: список (track_id, bbox) для текущего кадра
            stop_zone: зона остановки (прямоугольник) или None

        Returns:
            Список словарей по каждому наблюдаемому треку + "продолжающимся" (окклюзия).
        """
        obs_map: Dict[int, BBox] = {tid: bbox for tid, bbox in observations}
        visible_ids = set(obs_map.keys())

        # 1) обновляем/создаем состояния по видимым
        for tid, bbox in obs_map.items():
            st = self._tracks.get(tid)
            if st is None:
                st = TrackState(
                    track_id=tid,
                    created_at=now,
                    last_update_at=now,
                    last_seen_at=now,
                    last_bbox=bbox,
                    last_in_zone=False,
                    time_in_zone_s=0.0,
                )
                self._tracks[tid] = st

            dt = (now - st.last_update_at).total_seconds()
            if dt < 0:
                dt = 0.0

            in_zone = False
            if stop_zone is not None:
                cx, cy = _center(bbox)
                in_zone = point_in_rect(cx, cy, stop_zone)

            # если сейчас в зоне — добавляем dt (между апдейтами)
            if in_zone:
                st.time_in_zone_s += dt

            st.last_update_at = now
            st.last_seen_at = now
            st.last_bbox = bbox
            st.last_in_zone = in_zone

        # 2) обработка пропавших: если они "были в зоне", продолжаем считать время в зоне до TTL
        for tid, st in list(self._tracks.items()):
            if tid in visible_ids:
                continue
            dt = (now - st.last_update_at).total_seconds()
            if dt < 0:
                dt = 0.0

            missing_for = (now - st.last_seen_at).total_seconds()
            if st.last_in_zone and missing_for <= self.missing_ttl_s:
                st.time_in_zone_s += dt

            st.last_update_at = now

        self._prune(now)
        return self._export(now, stop_zone)

    def _export(self, now: datetime, stop_zone: Optional[ZoneRect]) -> List[dict]:
        out: List[dict] = []
        for tid, st in self._tracks.items():
            # статус определяем из последней известной "в зоне/вне зоны" и времени в зоне
            if st.last_in_zone:
                status = "waiting" if st.time_in_zone_s >= self.wait_threshold_s else "in_zone_not_waiting"
            else:
                status = "out_of_zone"

            missing_for = (now - st.last_seen_at).total_seconds()
            is_visible = missing_for <= 0.001  # "видимый в этом update" даём через last_seen_at==now

            out.append(
                {
                    "track_id": tid,
                    "bbox": list(st.last_bbox) if st.last_bbox is not None else None,
                    "status": status,
                    "time_in_zone_s": float(st.time_in_zone_s),
                    "last_in_zone": bool(st.last_in_zone),
                    "missing_for_s": float(max(0.0, missing_for)),
                    "is_visible": bool(is_visible),
                }
            )
        return out

    def _prune(self, now: datetime) -> None:
        if self.prune_after_s <= 0:
            return
        to_del = []
        for tid, st in self._tracks.items():
            missing_for = (now - st.last_seen_at).total_seconds()
            if missing_for > self.prune_after_s:
                to_del.append(tid)
        for tid in to_del:
            del self._tracks[tid]

