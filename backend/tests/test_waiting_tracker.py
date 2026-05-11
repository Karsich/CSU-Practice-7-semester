from datetime import datetime, timedelta

import numpy as np

from services.waiting_tracker import WaitingTracker
from services.zone_utils import scale_zone_coords


def test_waiting_status_threshold():
    wt = WaitingTracker(wait_threshold_s=10.0, missing_ttl_s=2.0, prune_after_s=100.0)
    zone = (0.0, 0.0, 100.0, 100.0)

    t0 = datetime(2026, 1, 1, 0, 0, 0)
    # 0s: в зоне
    out0 = wt.update(now=t0, observations=[(1, (10.0, 10.0, 20.0, 20.0))], stop_zone=zone)
    st0 = {x["track_id"]: x for x in out0}[1]
    assert st0["status"] == "in_zone_not_waiting"

    # +9s: всё ещё не waiting
    out1 = wt.update(now=t0 + timedelta(seconds=9), observations=[(1, (10.0, 10.0, 20.0, 20.0))], stop_zone=zone)
    st1 = {x["track_id"]: x for x in out1}[1]
    assert st1["status"] == "in_zone_not_waiting"

    # +11s: становится waiting
    out2 = wt.update(now=t0 + timedelta(seconds=11), observations=[(1, (10.0, 10.0, 20.0, 20.0))], stop_zone=zone)
    st2 = {x["track_id"]: x for x in out2}[1]
    assert st2["status"] == "waiting"


def test_missing_person_keeps_waiting_within_ttl():
    wt = WaitingTracker(wait_threshold_s=10.0, missing_ttl_s=2.0, prune_after_s=100.0)
    zone = (0.0, 0.0, 100.0, 100.0)
    t0 = datetime(2026, 1, 1, 0, 0, 0)

    # 0s: видим в зоне
    wt.update(now=t0, observations=[(1, (10.0, 10.0, 20.0, 20.0))], stop_zone=zone)
    # 10s: видим в зоне => waiting
    out_wait = wt.update(now=t0 + timedelta(seconds=10), observations=[(1, (10.0, 10.0, 20.0, 20.0))], stop_zone=zone)
    assert {x["track_id"]: x for x in out_wait}[1]["status"] == "waiting"

    # 11s: пропал (окклюзия), но ещё в пределах TTL => остаётся waiting
    out_missing = wt.update(now=t0 + timedelta(seconds=11), observations=[], stop_zone=zone)
    st_missing = {x["track_id"]: x for x in out_missing}[1]
    assert st_missing["status"] == "waiting"
    assert st_missing["last_in_zone"] is True


def test_missing_person_expires_after_ttl_does_not_keep_accumulating():
    wt = WaitingTracker(wait_threshold_s=10.0, missing_ttl_s=2.0, prune_after_s=100.0)
    zone = (0.0, 0.0, 100.0, 100.0)
    t0 = datetime(2026, 1, 1, 0, 0, 0)

    wt.update(now=t0, observations=[(1, (10.0, 10.0, 20.0, 20.0))], stop_zone=zone)
    wt.update(now=t0 + timedelta(seconds=5), observations=[(1, (10.0, 10.0, 20.0, 20.0))], stop_zone=zone)

    # пропал на 10 секунд (больше TTL) — накопление времени в зоне после TTL не должно продолжаться
    out_missing_long = wt.update(now=t0 + timedelta(seconds=15), observations=[], stop_zone=zone)
    st = {x["track_id"]: x for x in out_missing_long}[1]
    # последние данные всё ещё "в зоне", но missing_for_s > TTL, поэтому time_in_zone не должно увеличиться на все 10 секунд пропажи
    assert st["missing_for_s"] > 2.0
    assert st["time_in_zone_s"] <= 6.0


def test_scale_stop_zone_coords_matches_frame_resolution():
    frame = np.zeros((760, 1344, 3), dtype=np.uint8)  # половина от 1520x2688
    coords = [[2688.0, 1520.0], [0.0, 0.0]]
    scaled = scale_zone_coords(frame, coords, {"width": 2688, "height": 1520})
    assert scaled is not None
    # точка (2688,1520) должна стать (1344,760)
    assert abs(scaled[0][0] - 1344.0) < 1e-3
    assert abs(scaled[0][1] - 760.0) < 1e-3

