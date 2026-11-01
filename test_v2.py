"""Checks the v2 gesture logic with simulated data (no webcam needed).

Run: .venv/bin/python test_v2.py
"""

import random
from collections import namedtuple

from gestures import HoldDetector, SwipeDetectorV2, hand_pose

P = namedtuple("P", "x y")
FPS = 25


def move(x0, x1, start_t, duration):
    """Hand moving smoothly from x0 to x1."""
    n = max(2, int(duration * FPS))
    return [(start_t + i / FPS, x0 + (x1 - x0) * i / (n - 1)) for i in range(n)]


def still(x, start_t, duration):
    return [(start_t + i / FPS, x) for i in range(int(duration * FPS))]


def run(samples, detector=None):
    detector = detector or SwipeDetectorV2()
    return [d for t, x in samples if (d := detector.update(t, x))]


def test_one_swipe_fires_once():
    # the v1 problem: one swipe fired about 5 times
    samples = still(0.3, 0, 0.5) + move(0.3, 0.8, 0.5, 0.35) + still(0.8, 0.85, 1.0)
    assert run(samples) == ["right"]


def test_return_motion_is_not_a_left_swipe():
    # the reported problem: swipe right, hand comes back to centre -> must stay one "right"
    samples = (still(0.3, 0, 0.3) + move(0.3, 0.8, 0.3, 0.3)
               + move(0.8, 0.4, 0.6, 0.4) + still(0.4, 1.0, 1.0))
    assert run(samples) == ["right"]


def test_deliberate_left_after_pause_works():
    # after the hand rests, a real left swipe must still work
    samples = (move(0.3, 0.8, 0, 0.3) + still(0.8, 0.3, 1.5)
               + move(0.8, 0.3, 1.8, 0.3) + still(0.3, 2.1, 0.5))
    assert run(samples) == ["right", "left"]


def test_two_quick_right_swipes():
    # going forward two slides: right, reset hand, right again
    samples = (move(0.2, 0.7, 0, 0.3) + move(0.7, 0.2, 0.3, 0.5) + still(0.2, 0.8, 0.3)
               + move(0.2, 0.7, 1.1, 0.3) + still(0.7, 1.4, 0.5))
    assert run(samples) == ["right", "right"]


def repeat_swipes(stroke, ret, n=4):
    """n right swipes, each followed by the hand returning, with no pause in between."""
    samples, t = still(0.3, 0, 0.3), 0.3
    for _ in range(n):
        samples += move(0.3, 0.7, t, stroke)
        t += stroke
        samples += move(0.7, 0.3, t, ret)
        t += ret
    return samples + still(0.3, t, 1.0)


def test_fast_repeat_swipes_all_fire():
    # final tuning: the old fixed timers missed swipes faster than about one per 0.7 s
    for stroke, ret in [(0.3, 0.4), (0.25, 0.3), (0.2, 0.25)]:
        assert run(repeat_swipes(stroke, ret)) == ["right"] * 4, (stroke, ret)


def test_long_slow_swipe_fires_once():
    # final tuning: the old cooldown let the tail of one long swipe fire a second time
    samples = still(0.1, 0, 0.3) + move(0.1, 0.95, 0.3, 1.0) + still(0.95, 1.3, 1.0)
    assert run(samples) == ["right"]


def test_robust_to_tracking_noise():
    # +/-1% of frame width per frame, more than MediaPipe's averaged hand centre jitters
    scenarios = [
        (repeat_swipes(0.25, 0.3), ["right"] * 4),
        (still(0.1, 0, 0.3) + move(0.1, 0.95, 0.3, 1.0) + still(0.95, 1.3, 1.0), ["right"]),
        (move(0.3, 0.8, 0, 0.3) + move(0.8, 0.5, 0.3, 0.4) + still(0.5, 0.7, 0.8)
         + move(0.5, 0.1, 1.5, 0.3) + still(0.1, 1.8, 0.5), ["right", "left"]),
    ]
    for samples, expected in scenarios:
        for seed in range(50):
            rng = random.Random(seed)
            noisy = [(t, x + rng.uniform(-0.01, 0.01)) for t, x in samples]
            assert run(noisy) == expected, (expected, seed)


def test_slow_return_after_swipe_is_ignored():
    # final check: lowering the hand slowly after a swipe used to fire two false lefts
    for ret_s in (0.4, 0.8, 1.2, 1.6, 2.0, 3.0):
        samples = (still(0.3, 0, 0.3) + move(0.3, 0.8, 0.3, 0.3)
                   + move(0.8, 0.3, 0.6, ret_s) + still(0.3, 0.6 + ret_s, 1.0))
        assert run(samples) == ["right"], ret_s


def test_gentle_deliberate_swipe_still_works():
    # a calm swipe of a quarter of the frame in half a second must still count
    samples = still(0.4, 0, 0.5) + move(0.4, 0.65, 0.5, 0.5) + still(0.65, 1.0, 0.5)
    assert run(samples) == ["right"]


def test_jitter_does_not_fire():
    random.seed(1)
    samples = [(i / FPS, 0.5 + random.uniform(-0.06, 0.06)) for i in range(200)]
    assert run(samples) == []


def test_slow_drift_does_not_fire():
    assert run(move(0.2, 0.8, 0, 4.0)) == []


def fake_hand(index, middle, ring, pinky):
    """21 landmarks: wrist at bottom, each finger's middle joint at a fixed spot,
    tip far above it (open) or curled back below it (closed)."""
    pts = [P(0.5, 0.9)] + [P(0.5, 0.7)] * 20
    for i, (tip, pip, is_open) in enumerate(zip((8, 12, 16, 20), (6, 10, 14, 18),
                                                 (index, middle, ring, pinky))):
        x = 0.4 + 0.07 * i
        pts[pip] = P(x, 0.6)
        pts[tip] = P(x, 0.4) if is_open else P(x, 0.75)
    return pts


def test_poses():
    assert hand_pose(fake_hand(True, True, True, True)) == "palm"
    assert hand_pose(fake_hand(False, False, False, False)) == "fist"
    assert hand_pose(fake_hand(True, True, False, False)) == "peace"
    assert hand_pose(fake_hand(True, False, False, False)) == "other"


def test_hold_fires_once_after_one_second():
    h = HoldDetector()
    fired = [h.update(i / FPS, "peace", (0.5, 0.5)) for i in range(60)]
    assert [f for f in fired if f] == ["peace"]
    assert fired.index("peace") >= FPS  # not before 1 s


def test_resting_open_palm_does_not_pause():
    # the v2 test-run problem: an open palm resting before a swipe paused the system
    h = HoldDetector()
    fired = [h.update(i / FPS, "palm", (0.5, 0.5)) for i in range(100)]
    assert not any(fired)


def test_fist_needs_longer_hold_and_can_be_disabled():
    h = HoldDetector({"peace": 1.0, "fist": 1.5})
    fired = [h.update(i / FPS, "fist", (0.5, 0.5)) for i in range(60)]
    assert fired.index("fist") >= int(1.5 * FPS)
    h = HoldDetector({"peace": 1.0})  # blackout disabled
    assert not any(h.update(i / FPS, "fist", (0.5, 0.5)) for i in range(100))


def test_moving_pose_does_not_trigger_hold():
    h = HoldDetector()
    fired = [h.update(i / FPS, "fist", (0.2 + 0.02 * i, 0.5)) for i in range(60)]
    assert not any(fired)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
