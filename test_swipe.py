"""Checks the swipe logic with simulated wrist positions (no webcam needed).

Run: .venv/bin/python test_swipe.py
"""

from common import SwipeDetector


def feed(detector, samples):
    """samples: list of (time_s, x). Returns the list of detections (None filtered out)."""
    return [d for t, x in samples if (d := detector.update(t, x))]


def test_fast_right_swipe():
    # wrist moves 0.4 of the frame width in 0.3 s (30 fps)
    samples = [(i / 30, 0.3 + 0.4 * i / 9) for i in range(10)]
    assert "right" in feed(SwipeDetector(), samples)


def test_fast_left_swipe():
    samples = [(i / 30, 0.7 - 0.4 * i / 9) for i in range(10)]
    assert "left" in feed(SwipeDetector(), samples)


def test_slow_drift_is_ignored():
    # same distance but over 3 seconds: not a swipe
    samples = [(i / 30, 0.3 + 0.4 * i / 89) for i in range(90)]
    assert feed(SwipeDetector(), samples) == []


def test_still_hand_is_ignored():
    samples = [(i / 30, 0.5) for i in range(60)]
    assert feed(SwipeDetector(), samples) == []


def test_v1_double_trigger_exists():
    # Documents the known v1 problem: one swipe fires on several frames.
    samples = [(i / 30, 0.2 + 0.6 * i / 11) for i in range(12)]
    assert len(feed(SwipeDetector(), samples)) > 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
