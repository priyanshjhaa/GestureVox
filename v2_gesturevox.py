"""GestureVox v2: the improved prototype after the v1 heuristic evaluation.

Gestures:
  Swipe right            -> next slide        (Right arrow)
  Swipe left             -> previous slide    (Left arrow)
  Hold V sign 1 s        -> pause / resume gesture control  (index + middle finger up)
  Hold fist 1.5 s        -> black screen on / off  (B key; only with --blackout)

Blackout is off by default: in testing, a sideways hand during swipes was read as a
fist, and the accidental B presses blacked out the slides (Midas touch problem).

Feedback (fixes "no visibility of system status" from v1):
  - Status pill: ACTIVE (green) / PAUSED (amber) / NO HAND (red), always with a text label
  - Toast showing the action just performed, fading after about 1 s
  - Progress bar while holding a V sign or fist
  - A short sound for every action (multimodal feedback), turn off with --no-sound

Learnability and accessibility:
  - Practice mode on start: do each gesture once before control goes live (S skips)
  - --left-handed reverses the swipe directions
  - --large-text uses bigger, high-contrast overlay text
  - Swipe sensitivity set with [ / ] is saved in settings.json and reused next time
  - A session summary is shown and logged on quit

Every action is logged to logs/<participant>_<time>.csv for the user study.

Run:  .venv/bin/python v2_gesturevox.py
      .venv/bin/python v2_gesturevox.py --participant P1
      .venv/bin/python v2_gesturevox.py --skip-practice --large-text --left-handed
      .venv/bin/python v2_gesturevox.py --dry-run --no-sound
      .venv/bin/python v2_gesturevox.py --blackout
Keys in the camera window:  S = skip practice,  D = debug readout,
                            [ / ] = swipe sensitivity,  Q = quit
"""

import argparse
import csv
import subprocess
import time
from datetime import datetime
from pathlib import Path

import cv2
import pyautogui

from common import HandTracker, draw_hand
from features import Practice, SessionStats, load_settings, save_settings
from gestures import HoldDetector, SwipeDetectorV2, hand_center, hand_pose

WINDOW = "GestureVox v2"
HAND_LOST_RESET_S = 0.3  # forget swipe history if the hand is gone longer than this
TOAST_S = 1.0
SUMMARY_S = 4.0  # how long the summary stays on screen after Q
FONT = cv2.FONT_HERSHEY_SIMPLEX
DISPLAY_W = 1280  # width the overlay is drawn at; the window shows it scaled down

# pyautogui's fail-safe raises an error on any key press while the mouse pointer sits in
# a screen corner (where presenters often park it), which would crash a session. This
# program only presses arrow keys and never moves the mouse, so the fail-safe isn't needed.
# PAUSE = 0 removes pyautogui's default 0.1 s sleep after every key press, which froze
# the camera loop.
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# BGR colours. Status is never shown by colour alone: each pill also has a text label.
GREEN, AMBER, RED, GREY = (60, 170, 60), (0, 170, 255), (50, 50, 220), (110, 110, 110)
WHITE, BLACK, YELLOW = (255, 255, 255), (0, 0, 0), (0, 230, 255)

SOUNDS = {
    "swipe": "/System/Library/Sounds/Tink.aiff",
    "pause": "/System/Library/Sounds/Pop.aiff",
    "resume": "/System/Library/Sounds/Pop.aiff",
    "blackout": "/System/Library/Sounds/Bottle.aiff",
    "step": "/System/Library/Sounds/Glass.aiff",
    "ready": "/System/Library/Sounds/Hero.aiff",
}

# Overlay style; --large-text scales everything up and switches to high contrast.
STYLE = {"scale": 1.0, "thick": 2, "contrast": False}


def s(value):
    """Scale a size by the current text scale."""
    return int(value * STYLE["scale"]) if isinstance(value, int) else value * STYLE["scale"]


class Logger:
    def __init__(self, participant):
        logs = Path(__file__).parent / "logs"
        logs.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = logs / f"{participant}_{stamp}.csv"
        self.file = open(self.path, "w", newline="")
        self.writer = csv.writer(self.file)
        self.writer.writerow(["time_s", "event", "state"])

    def log(self, t, event, state):
        self.writer.writerow([f"{t:.3f}", event, state])
        self.file.flush()

    def close(self):
        self.file.close()


def play(sound, enabled):
    if enabled and sound in SOUNDS:
        subprocess.Popen(["afplay", SOUNDS[sound]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def text_size(text, size):
    (tw, th), _ = cv2.getTextSize(text, FONT, s(size), STYLE["thick"])
    return tw, th


def draw_pill(frame, text, color, origin=(12, 12)):
    tw, th = text_size(text, 0.7)
    x, y = origin
    pad = s(12)
    cv2.rectangle(frame, (x, y), (x + tw + 2 * pad, y + th + 2 * pad), color, -1)
    if STYLE["contrast"]:
        cv2.rectangle(frame, (x, y), (x + tw + 2 * pad, y + th + 2 * pad), WHITE, 2)
    cv2.putText(frame, text, (x + pad, y + th + pad), FONT, s(0.7), WHITE, STYLE["thick"])


def draw_toast(frame, text, age, y_frac=0.5):
    """Large centred message that fades out over TOAST_S seconds. y_frac = height on screen."""
    alpha = max(0.0, 1 - age / TOAST_S)
    if alpha <= 0 or not text:
        return
    h, w = frame.shape[:2]
    size = 1.2
    tw, th = text_size(text, size)
    if tw > w - 60:  # long message: shrink it to fit the width
        size *= (w - 60) / tw
        tw, th = text_size(text, size)
    x, y = (w - tw) // 2, int(h * y_frac)
    overlay = frame.copy()
    cv2.rectangle(overlay, (x - 20, y - th - 20), (x + tw + 20, y + 20), BLACK, -1)
    cv2.putText(overlay, text, (x, y), FONT, s(size), YELLOW if STYLE["contrast"] else WHITE,
                STYLE["thick"] + 1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def draw_hold_bar(frame, label, progress):
    h, w = frame.shape[:2]
    x0, bw, bh = 12, s(260), s(14)
    y0 = h - s(34) - bh - s(30)
    cv2.putText(frame, label, (x0, y0 - 8), FONT, s(0.6), WHITE, STYLE["thick"])
    cv2.rectangle(frame, (x0, y0), (x0 + bw, y0 + bh), GREY, -1)
    cv2.rectangle(frame, (x0, y0), (x0 + int(bw * progress), y0 + bh), AMBER, -1)


def draw_help(frame, blackout_enabled):
    h, w = frame.shape[:2]
    text = "Swipe: next/prev   V sign: pause   "
    text += "Fist: blackout   Q: quit" if blackout_enabled else "Q: quit"
    bar = s(34)
    cv2.rectangle(frame, (0, h - bar), (w, h), BLACK, -1)
    cv2.putText(frame, text, (12, h - bar // 3), FONT, s(0.55), WHITE, max(1, STYLE["thick"] - 1))


def draw_panel(frame, title, lines, title_color=YELLOW):
    """Dark box in the middle-left with a title and coloured lines: [(text, colour), ...]."""
    h, w = frame.shape[:2]
    line_h = s(34)
    box_h = line_h * (len(lines) + 1) + s(30)
    x0, y0 = 12, s(70)
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (w - 12, y0 + box_h), BLACK, -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    y = y0 + line_h
    cv2.putText(frame, title, (x0 + 14, y), FONT, s(0.75), title_color, STYLE["thick"])
    for text, color in lines:
        y += line_h
        cv2.putText(frame, text, (x0 + 14, y), FONT, s(0.65), color, STYLE["thick"])


def draw_practice(frame, practice, left_handed=False):
    lines = []
    for i, (_, prompt) in enumerate(Practice.STEPS):
        if left_handed:  # directions are reversed, so tell the user the physical one
            prompt = prompt.replace("RIGHT", "<tmp>").replace("LEFT", "RIGHT").replace("<tmp>", "LEFT")
        if i < practice.index:
            lines.append((f"[x] {prompt}", GREEN))
        elif i == practice.index:
            lines.append((f"[ ] {prompt}   <- now", YELLOW))
        else:
            lines.append((f"[ ] {prompt}", (180, 180, 180)))
    lines.append(("Nothing is sent to your slides yet.  S = skip", WHITE))
    draw_panel(frame, "PRACTICE  (try each gesture once)", lines)


def main():
    parser = argparse.ArgumentParser(description="GestureVox v2")
    parser.add_argument("--dry-run", action="store_true", help="show and log gestures without pressing keys")
    parser.add_argument("--no-sound", action="store_true", help="turn off sound feedback")
    parser.add_argument("--participant", default="session", help="name used for the log file, e.g. P1")
    parser.add_argument("--camera", type=int, default=0, help="webcam index")
    parser.add_argument("--blackout", action="store_true", help="enable the hold-fist blackout gesture")
    parser.add_argument("--skip-practice", action="store_true", help="start without the practice tutorial")
    parser.add_argument("--left-handed", action="store_true", help="reverse the swipe directions")
    parser.add_argument("--large-text", action="store_true", help="bigger, high-contrast overlay text")
    args = parser.parse_args()
    sound = not args.no_sound

    if args.large_text:
        STYLE.update(scale=1.6, thick=3, contrast=True)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit("Could not open the webcam. Check camera permission for your terminal app.")
    # 640x480 is plenty: MediaPipe shrinks frames to about 224 px internally anyway, and
    # smaller frames mean less copying, flipping and drawing per frame (lower lag).
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    settings = load_settings()
    tracker = HandTracker()
    swipes = SwipeDetectorV2()
    if "min_distance" in settings:
        swipes.min_distance = settings["min_distance"]
    holds = HoldDetector({"peace": 1.0, "fist": 1.5} if args.blackout else {"peace": 1.0})
    logger = Logger(args.participant)
    practice = Practice()
    if args.skip_practice:
        practice.skip()
    stats = SessionStats()

    # Not "always on top": on macOS that can pull keyboard focus back to this window,
    # so the arrow keys never reach the slideshow.
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, 960 if args.large_text else 640, 720 if args.large_text else 480)

    paused = False
    blackout = False
    toast, toast_t = "", -10.0
    last_seen = -10.0
    show_debug = False
    start = time.monotonic()
    last_frame = 0.0
    frame = None

    def state():
        if practice.active:
            return "practice"
        return "paused" if paused else ("blackout" if blackout else "active")

    def show_toast(t, message):
        nonlocal toast, toast_t
        toast, toast_t = message, t

    def act(t, event, key, message, sound_name):
        print(f"{t:7.2f}s  {event}")
        logger.log(t, event, state())
        if key and not args.dry_run:
            pyautogui.press(key)
        show_toast(t, message)
        play(sound_name, sound)

    def practice_event(t, event):
        """During practice, gestures only tick off steps; nothing is sent to the slides."""
        if practice.feed(event, t):
            logger.log(t, f"practice_step_{practice.index}", "practice")
            if practice.active:
                show_toast(t, "Nice!")
                play("step", sound)
            else:
                logger.log(t, "practice_complete", "active")
                print(f"{t:7.2f}s  practice complete")
                show_toast(t, "Ready! Gestures now control your slides")
                play("ready", sound)

    def change_sensitivity(delta):
        nonlocal show_debug
        swipes.min_distance = round(min(0.4, max(0.04, swipes.min_distance + delta)), 2)
        settings["min_distance"] = swipes.min_distance
        save_settings(settings)
        show_debug = True

    logger.log(0.0, "start", state())
    print(f"GestureVox v2 running. Logging to {logger.path}")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            now = time.monotonic() - start
            landmarks = tracker.detect(frame, int(now * 1000))
            # Detect on the small frame (fast), then enlarge it for drawing so the overlay
            # stays sharp and laid out the same at any camera resolution.
            frame = cv2.resize(frame, (DISPLAY_W, DISPLAY_W * frame.shape[0] // frame.shape[1]))

            if landmarks:
                last_seen = now
                draw_hand(frame, landmarks, AMBER if paused else GREEN)
                center = hand_center(landmarks)
                pose = hand_pose(landmarks)

                held = holds.update(now, pose, center)
                direction = swipes.update(now, center[0])
                if direction and args.left_handed:
                    direction = "left" if direction == "right" else "right"

                if practice.active:
                    if held == "peace":
                        practice_event(now, "hold_peace")
                    if direction:
                        practice_event(now, f"swipe_{direction}")
                else:
                    if held == "peace":
                        paused = not paused
                        if paused:
                            stats.add("pause")
                            act(now, "pause", None, "Paused", "pause")
                        else:
                            stats.add("resume")
                            act(now, "resume", None, "Resumed", "resume")
                        swipes.reset()
                    elif held == "fist" and not paused:
                        blackout = not blackout
                        if blackout:
                            stats.add("blackout")
                        act(now, "blackout_on" if blackout else "blackout_off", "b",
                            "Screen black" if blackout else "Screen back", "blackout")

                    if direction:
                        if paused:
                            stats.add("ignored")
                            logger.log(now, f"swipe_{direction}_ignored", "paused")
                        else:
                            blackout = False  # arrow keys also end black screen in PowerPoint/Keynote
                            stats.add("next" if direction == "right" else "previous")
                            act(now, f"swipe_{direction}", direction,
                                "Next slide  >>" if direction == "right" else "<<  Previous slide",
                                "swipe")
            else:
                holds.reset()
                if now - last_seen > HAND_LOST_RESET_S:
                    swipes.reset()

            # ---- feedback overlay ----
            if practice.active:
                draw_pill(frame, "PRACTICE" if landmarks else "PRACTICE - show your hand",
                          GREY if landmarks else RED)
                draw_practice(frame, practice, args.left_handed)
            elif paused:
                draw_pill(frame, "PAUSED - hold V sign to resume", AMBER)
            elif not landmarks:
                draw_pill(frame, "NO HAND", RED)
            elif blackout:
                draw_pill(frame, "ACTIVE - screen black", GREY)
            else:
                draw_pill(frame, "ACTIVE", GREEN)

            progress = holds.progress(now)
            if progress > 0.15:  # don't flash the bar for every brief pose
                if holds.pose == "peace":
                    draw_hold_bar(frame, "Resuming..." if paused else "Pausing...", progress)
                elif holds.pose == "fist" and not paused and not practice.active:
                    draw_hold_bar(frame, "Screen back..." if blackout else "Black screen...", progress)

            # during practice, keep the toast below the checklist panel
            draw_toast(frame, toast, now - toast_t, 0.8 if practice.active else 0.5)
            draw_help(frame, args.blackout)

            if show_debug:
                fps = 1 / max(now - last_frame, 1e-6)
                pose_text = hand_pose(landmarks) if landmarks else "-"
                debug = (f"FPS {fps:4.1f}  move {swipes.last_dx:+.2f}  "
                         f"need {swipes.min_distance:.2f}  pose {pose_text}")
                cv2.putText(frame, debug, (12, s(80) if not practice.active else frame.shape[0] - s(110)),
                            FONT, s(0.6), YELLOW, STYLE["thick"])
            last_frame = now

            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
            if key in (ord("s"), ord("S")) and practice.active:
                practice.skip()
                logger.log(now, "practice_skipped", "active")
                show_toast(now, "Practice skipped - gestures are live")
            elif key in (ord("d"), ord("D")):
                show_debug = not show_debug
            elif key == ord("["):  # more sensitive
                change_sensitivity(-0.01)
            elif key == ord("]"):  # less sensitive
                change_sensitivity(+0.01)
    finally:
        duration = time.monotonic() - start
        summary = stats.summary(duration)
        logger.log(duration, "summary", "; ".join(summary))
        logger.log(duration, "quit", "")
        logger.close()
        print("\nSession summary:\n  " + "\n  ".join(summary))
        print(f"Log saved to {logger.path}")
        if frame is not None:
            draw_panel(frame, "SESSION SUMMARY", [(line, WHITE) for line in summary]
                       + [("Closing...", (180, 180, 180))])
            cv2.imshow(WINDOW, frame)
            cv2.waitKey(int(SUMMARY_S * 1000))
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
