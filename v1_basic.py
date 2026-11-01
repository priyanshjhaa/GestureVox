"""GestureVox v1: the first, deliberately basic prototype.

What it does:
  - Swipe your hand right  -> presses the Right arrow (next slide)
  - Swipe your hand left   -> presses the Left arrow (previous slide)

What it does NOT do yet (these are the problems the heuristic evaluation should find):
  - No cooldown, so one swipe can skip several slides
  - No status indicator (is it on? did it see my hand?)
  - No way to pause it, so talking with your hands changes slides
  - No feedback about which gesture was recognised

Run:  .venv/bin/python v1_basic.py            (sends real key presses)
      .venv/bin/python v1_basic.py --dry-run  (only prints, no key presses)
Quit: press Q in the camera window.
"""

import argparse
import time

import cv2
import pyautogui

from common import HandTracker, SwipeDetector, draw_hand, hand_center_x

KEYS = {"right": "right", "left": "left"}


def main():
    parser = argparse.ArgumentParser(description="GestureVox v1")
    parser.add_argument("--dry-run", action="store_true", help="print gestures without pressing keys")
    parser.add_argument("--camera", type=int, default=0, help="webcam index")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit("Could not open the webcam. Check camera permission for your terminal app.")

    tracker = HandTracker()
    swipes = SwipeDetector()
    start = time.monotonic()
    last_frame = 0.0
    peak, peak_time = 0.0, 0.0  # biggest movement in the last 2 s, so it can be read on screen

    print("GestureVox v1 running. Swipe left/right. Press Q in the window to quit.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)  # mirror, so moving your hand right moves it right on screen

            now = time.monotonic() - start
            landmarks = tracker.detect(frame, int(now * 1000))

            # No reset when the hand is lost: fast swipes blur the hand for a frame or two,
            # and old samples drop out of the swipe window on their own anyway.
            if landmarks:
                draw_hand(frame, landmarks)
                direction = swipes.update(now, hand_center_x(landmarks))
                if direction:
                    print(f"{now:7.2f}s  swipe {direction}")
                    if not args.dry_run:
                        pyautogui.press(KEYS[direction])

            # Debug readout for testing; not user-facing feedback (that comes in v2).
            fps = 1 / max(now - last_frame, 1e-6)
            last_frame = now
            if abs(swipes.last_dx) > abs(peak) or now - peak_time > 2:
                peak, peak_time = swipes.last_dx, now
            lines = [
                f"FPS {fps:4.1f}   hand {'yes' if landmarks else 'NO'}",
                f"move {swipes.last_dx:+.2f}   peak {peak:+.2f}",
                f"need +/-{swipes.min_distance:.2f}   ([ / ] to adjust)",
            ]
            for i, line in enumerate(lines):
                cv2.putText(frame, line, (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow("GestureVox v1", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
            if key == ord("["):
                swipes.min_distance = max(0.03, swipes.min_distance - 0.01)
            elif key == ord("]"):
                swipes.min_distance = min(0.5, swipes.min_distance + 0.01)
    finally:
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
