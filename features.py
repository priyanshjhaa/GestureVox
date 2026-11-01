"""Practice mode, session summary and saved settings for GestureVox v2.

No camera code here, so all of it can be tested (see test_features.py).
"""

import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent / "settings.json"


class Practice:
    """Guided first-run tutorial: each gesture must be done once before control goes live.

    Nothing reaches the slideshow during practice. The time taken is logged, which gives a
    simple learnability measure for the user study.
    """

    STEPS = [
        ("swipe_right", "Swipe RIGHT (next slide)"),
        ("swipe_left", "Swipe LEFT (previous slide)"),
        ("hold_peace", "Hold a V sign still to PAUSE"),
        ("hold_peace", "Hold a V sign again to RESUME"),
    ]

    def __init__(self):
        self.index = 0
        self.step_times = []  # time each step was completed

    @property
    def active(self):
        return self.index < len(self.STEPS)

    def feed(self, event, t):
        """Report a recognised gesture. Returns True if it completed the current step."""
        if self.active and event == self.STEPS[self.index][0]:
            self.index += 1
            self.step_times.append(t)
            return True
        return False

    def skip(self):
        self.index = len(self.STEPS)


class SessionStats:
    """Counts what happened in a session, for the summary shown on quit."""

    def __init__(self):
        self.counts = {"next": 0, "previous": 0, "pause": 0, "resume": 0,
                       "ignored": 0, "blackout": 0}

    def add(self, name):
        self.counts[name] += 1

    def summary(self, duration_s):
        c = self.counts
        minutes, seconds = divmod(int(duration_s), 60)
        parts = [
            f"{c['next'] + c['previous']} swipes ({c['next']} next, {c['previous']} back)",
            f"{c['pause']} pauses",
        ]
        if c["ignored"]:
            parts.append(f"{c['ignored']} swipes ignored while paused")
        if c["blackout"]:
            parts.append(f"{c['blackout']} blackouts")
        parts.append(f"{minutes} min {seconds:02d} s")
        return parts


def load_settings(path=SETTINGS_PATH):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_settings(settings, path=SETTINGS_PATH):
    path.write_text(json.dumps(settings, indent=2))
