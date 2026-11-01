"""Checks practice mode, session summary, saved settings and overlay drawing (no webcam).

Run: .venv/bin/python test_features.py
"""

import tempfile
from pathlib import Path

import numpy as np

import v2_gesturevox as app
from features import Practice, SessionStats, load_settings, save_settings


def test_practice_steps_in_order():
    p = Practice()
    assert p.active
    assert not p.feed("swipe_left", 1.0)  # wrong gesture: no progress
    assert p.feed("swipe_right", 2.0)
    assert p.feed("swipe_left", 3.0)
    assert p.feed("hold_peace", 4.0)
    assert p.active
    assert p.feed("hold_peace", 5.0)
    assert not p.active
    assert p.step_times == [2.0, 3.0, 4.0, 5.0]
    assert not p.feed("swipe_right", 6.0)  # finished: ignores further input


def test_practice_skip():
    p = Practice()
    p.skip()
    assert not p.active


def test_summary_text():
    st = SessionStats()
    for name in ["next"] * 7 + ["previous"] * 5 + ["pause", "pause", "ignored"]:
        st.add(name)
    lines = st.summary(270)
    assert lines[0] == "12 swipes (7 next, 5 back)"
    assert "2 pauses" in lines
    assert "1 swipes ignored while paused" in lines
    assert lines[-1] == "4 min 30 s"


def test_settings_round_trip():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "settings.json"
        assert load_settings(path) == {}  # missing file
        save_settings({"min_distance": 0.08}, path)
        assert load_settings(path) == {"min_distance": 0.08}
        path.write_text("not json")
        assert load_settings(path) == {}  # broken file doesn't crash


def test_overlay_draws_in_both_styles():
    for large in (False, True):
        app.STYLE.update(scale=1.6 if large else 1.0, thick=3 if large else 2, contrast=large)
        frame = np.zeros((720, 1280, 3), np.uint8)
        p = Practice()
        p.feed("swipe_right", 1.0)
        app.draw_pill(frame, "ACTIVE", app.GREEN)
        app.draw_practice(frame, p)
        app.draw_toast(frame, "Ready! Gestures now control your slides", 0.2)
        app.draw_hold_bar(frame, "Pausing...", 0.5)
        app.draw_help(frame, blackout_enabled=True)
        app.draw_panel(frame, "SESSION SUMMARY", [("12 swipes", app.WHITE)])
        assert frame.any()
    app.STYLE.update(scale=1.0, thick=2, contrast=False)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
