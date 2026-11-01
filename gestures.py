"""GestureVox v2 gesture logic. Pure Python with no camera code, so it can be tested.

Each fix here answers a problem found in the v1 heuristic evaluation:
  - Smoothing + path efficiency check  -> jittery, inaccurate swipes
  - Cooldown                           -> one swipe skipping several slides
  - Return-motion block                -> swiping right also triggering left
  - Hold-to-confirm poses              -> pause and blackout without accidental triggers
"""

import math
from collections import deque

WRIST = 0
FINGER_TIPS = (8, 12, 16, 20)  # index, middle, ring, pinky (thumb ignored: unreliable)
FINGER_PIPS = (6, 10, 14, 18)  # the middle joint of each of those fingers


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def finger_states(landmarks):
    """(index, middle, ring, pinky) as True when extended. A finger counts as extended
    when its tip is clearly farther from the wrist than its middle joint. Using distances
    (not just y) works even if the hand is tilted."""
    wrist = landmarks[WRIST]
    return tuple(
        _dist(landmarks[tip], wrist) > 1.1 * _dist(landmarks[pip], wrist)
        for tip, pip in zip(FINGER_TIPS, FINGER_PIPS)
    )


def hand_pose(landmarks):
    """'palm' (all four open), 'fist' (all closed), 'peace' (V sign: index and middle
    open, ring and pinky closed), or 'other'.

    Pause uses 'peace', not 'palm': people swipe with an open palm, so an open-palm
    pause fired by accident whenever the hand rested before a swipe (Midas touch problem
    found while testing v2)."""
    fingers = finger_states(landmarks)
    if all(fingers):
        return "palm"
    if not any(fingers):
        return "fist"
    if fingers == (True, True, False, False):
        return "peace"
    return "other"


def hand_center(landmarks):
    """Average (x, y) of all 21 points, so a wrist flick still counts as hand movement."""
    n = len(landmarks)
    return sum(lm.x for lm in landmarks) / n, sum(lm.y for lm in landmarks) / n


class SwipeDetectorV2:
    """Horizontal swipe detection with the v1 problems fixed.

    Motion-based rules (not fixed timers), so fast users aren't slowed down:
      - Re-arm: after a swipe, the next one is only accepted once the stroke has ended,
        i.e. the hand slowed down or reversed. One long swipe can never fire twice.
      - Return motion: the first opposite movement after a swipe is treated as the hand
        returning and ignored, however fast it comes, unless the hand rested first.
      - A short cooldown stays as a safety net.

    min_distance  fraction of frame width the hand must travel within window_s
    consistency   minimum net movement / total movement, 0..1 (rejects jitter)
    smoothing     exponential smoothing factor for the x position (1 = no smoothing)
    cooldown_s    minimum time between two swipes
    rearm_speed   hand speed (frame widths per second) below which a stroke has ended
    min_peak_speed  a swipe must reach at least this speed somewhere (rejects slow drifts,
                  such as the hand being lowered slowly after a swipe)
    rest_s, rest_range  the hand counts as resting when it moved less than rest_range
                  within rest_s; resting after a swipe allows a deliberate opposite swipe
    """

    def __init__(self, min_distance=0.10, window_s=0.6, consistency=0.6, smoothing=0.6,
                 cooldown_s=0.25, rearm_speed=0.35, min_peak_speed=0.4,
                 rest_s=0.5, rest_range=0.03):
        self.min_distance = min_distance
        self.window_s = window_s
        self.consistency = consistency
        self.smoothing = smoothing
        self.cooldown_s = cooldown_s
        self.rearm_speed = rearm_speed
        self.min_peak_speed = min_peak_speed
        self.rest_s = rest_s
        self.rest_range = rest_range

        self.history = deque()  # (time_s, smoothed_x)
        self.smoothed = None
        self.last_fire_t = -math.inf
        self.last_direction = None
        self.armed = True            # False from a swipe until that stroke ends
        self.stroke_sign = 0         # direction of the stroke that disarmed (+1 right, -1 left)
        self.expect_return = False   # True from a swipe until its return motion is consumed
        self.recent = deque()        # (time_s, smoothed_x) over rest_s, for rest detection
        self.last_dx = 0.0           # for the debug readout

    def in_cooldown(self, t):
        return t - self.last_fire_t < self.cooldown_s

    def update(self, t, x):
        """Feed one hand-position sample. Returns 'right', 'left', or None."""
        prev = self.history[-1] if self.history else None
        if self.smoothed is None:
            self.smoothed = x
        else:
            self.smoothed = self.smoothing * x + (1 - self.smoothing) * self.smoothed
        self.history.append((t, self.smoothed))
        while t - self.history[0][0] > self.window_s:
            self.history.popleft()

        velocity = (self.smoothed - prev[1]) / max(t - prev[0], 1e-6) if prev else 0.0
        speed = abs(velocity)
        reversed_ = velocity * self.stroke_sign < 0
        if speed < self.rearm_speed or reversed_:
            self.armed = True  # the stroke has ended

        # Resting = the hand stayed within rest_range for rest_s (moving slowly isn't resting).
        self.recent.append((t, self.smoothed))
        while t - self.recent[0][0] > self.rest_s:
            self.recent.popleft()
        xs_recent = [x for _, x in self.recent]
        if (t - self.recent[0][0] >= self.rest_s * 0.9
                and max(xs_recent) - min(xs_recent) < self.rest_range):
            self.expect_return = False  # hand rested: an opposite swipe is now deliberate

        # While a stroke is still going (or just fired), movement is consumed rather than
        # remembered, so its tail cannot fire again.
        if not self.armed or self.in_cooldown(t):
            self._keep_latest_only()
            return None
        if len(self.history) < 3:
            return None

        dx = self.history[-1][1] - self.history[0][1]
        self.last_dx = dx
        if abs(dx) < self.min_distance:
            return None

        # Path efficiency: net movement / total movement. A clean swipe is close to 1;
        # jitter moves back and forth a lot for little net movement. Frames where the
        # hand is still add nothing, so resting before a swipe does not count against it.
        xs = [x for _, x in self.history]
        path = sum(abs(b - a) for a, b in zip(xs, xs[1:]))
        if abs(dx) / path < self.consistency:
            return None

        pts = list(self.history)
        peak = max(abs(b[1] - a[1]) / max(b[0] - a[0], 1e-6) for a, b in zip(pts, pts[1:]))
        if peak < self.min_peak_speed:
            return None

        direction = "right" if dx > 0 else "left"
        self.armed = False
        self.stroke_sign = 1 if dx > 0 else -1
        self._keep_latest_only()
        if self.expect_return and direction != self.last_direction:
            self.expect_return = False  # this is the hand returning: swallow it
            return None

        self.last_fire_t = t
        self.last_direction = direction
        self.expect_return = True
        return direction

    def _keep_latest_only(self):
        latest = self.history[-1]
        self.history.clear()
        self.history.append(latest)

    def reset(self):
        """Call when the hand has been gone for a while."""
        self.history.clear()
        self.smoothed = None
        self.armed = True
        self.recent.clear()


class HoldDetector:
    """Fires once when a pose is held still for that pose's hold time.

    hold_times maps pose -> seconds, e.g. {"peace": 1.0, "fist": 1.5}. Poses not in it
    never fire. Holding still is required so a pose passing by during a swipe does not count.
    """

    def __init__(self, hold_times=None, max_move=0.05):
        self.hold_times = hold_times or {"peace": 1.0, "fist": 1.5}
        self.max_move = max_move
        self.reset()

    def reset(self):
        self.pose = None
        self.start_t = 0.0
        self.anchor = (0.0, 0.0)
        self.fired = False

    def update(self, t, pose, center):
        """Returns the pose name once when the hold completes, else None."""
        moved = math.hypot(center[0] - self.anchor[0], center[1] - self.anchor[1])
        if pose != self.pose or moved > self.max_move:
            self.pose, self.start_t, self.anchor, self.fired = pose, t, center, False
            return None
        hold_s = self.hold_times.get(pose)
        if not self.fired and hold_s is not None and t - self.start_t >= hold_s:
            self.fired = True
            return pose
        return None

    def progress(self, t):
        """0..1 progress of the current hold, for the on-screen progress bar."""
        hold_s = self.hold_times.get(self.pose)
        if hold_s is None or self.fired:
            return 0.0
        return min(1.0, (t - self.start_t) / hold_s)
