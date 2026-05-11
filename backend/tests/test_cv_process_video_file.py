import os
import tempfile

import cv2
import numpy as np
from fastapi.testclient import TestClient

from main import app


def _make_test_video(path: str, *, w: int = 160, h: int = 120, fps: float = 10.0, frames: int = 6) -> None:
    # AVI + MJPG обычно доступен даже на headless окружениях
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    assert writer.isOpened()
    try:
        for i in range(frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.rectangle(frame, (10 + i, 10), (40 + i, 60), (255, 255, 255), -1)
            writer.write(frame)
    finally:
        writer.release()


def test_process_video_file_endpoint_returns_video_bytes():
    client = TestClient(app)

    fd, in_path = tempfile.mkstemp(suffix=".avi")
    os.close(fd)
    try:
        _make_test_video(in_path)

        with open(in_path, "rb") as f:
            files = {"file": ("test.avi", f, "video/x-msvideo")}
            data = {
                "stop_zone_coords_json": "[[0,0],[159,0],[159,119],[0,119]]",
                "original_width": "160",
                "original_height": "120",
            }
            r = client.post("/api/v1/cv/process-video-file", files=files, data=data)

        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("video/")
        assert r.content is not None and len(r.content) > 0
    finally:
        try:
            os.remove(in_path)
        except Exception:
            pass

