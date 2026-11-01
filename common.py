"""Shared helpers for GestureVox: hand tracking, drawing, and swipe detection.

Used by v1_basic.py now and by v2 later, so both versions track hands the same way.
"""

from collections import deque
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

MODEL_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"
WRIST = 0


class HandTracker:
    """Wraps MediaPipe HandLandmarker in VIDEO mode (one frame at a time)."""

    def __init__(self, min_confidence=0.6):
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=min_confidence,
            min_hand_presence_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        self.last_timestamp_ms = -1

    def detect(self, frame_bgr, timestamp_ms):
        """Return the 21 landmarks of the first hand, or None if no hand is visible."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        # MediaPipe raises an error unless timestamps strictly increase; two frames in the
        # same millisecond would otherwise crash the program.
        timestamp_ms = max(timestamp_ms, self.last_timestamp_ms + 1)
        self.last_timestamp_ms = timestamp_ms
        result = self.landmarker.detect_for_video(image, timestamp_ms)
        return result.hand_landmarks[0] if result.hand_landmarks else None

    def close(self):
        self.landmarker.close()


def hand_center_x(landmarks):
    """Average x of all 21 points. Unlike the wrist alone, this also moves when the
    user swipes by flicking from the wrist, which is how most people naturally swipe."""
    return sum(lm.x for lm in landmarks) / len(landmarks)


def draw_hand(frame, landmarks, color=(0, 255, 0)):
    """Draw the hand skeleton on the frame (landmarks are normalised 0..1)."""
    h, w = frame.shape[:2]
    points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for conn in vision.HandLandmarksConnections.HAND_CONNECTIONS:
        cv2.line(frame, points[conn.start], points[conn.end], color, 2)
    for p in points:
        cv2.circle(frame, p, 4, (255, 255, 255), -1)


class SwipeDetector:
    """Detects horizontal swipes from the hand centre's x position over a short time window.

    A swipe is reported when the hand moves more than `min_distance` (fraction of
    frame width) within `window_s` seconds. v1 has no cooldown, so one physical swipe
    can be reported several times; that is a known v1 problem, fixed in v2.
    """

    def __init__(self, min_distance=0.10, window_s=0.6):
        self.min_distance = min_distance
        self.window_s = window_s
        self.history = deque()  # (time_s, x)
        self.last_dx = 0.0  # latest movement across the window, shown on screen for debugging

    def update(self, t, x):
        """Feed one hand-position sample. Returns 'right', 'left', or None."""
        self.history.append((t, x))
        while self.history and t - self.history[0][0] > self.window_s:
            self.history.popleft()

        dx = x - self.history[0][1]
        self.last_dx = dx
        if dx > self.min_distance:
            return "right"
        if dx < -self.min_distance:
            return "left"
        return None

    def reset(self):
        self.history.clear()
