# GestureVox

Hands-free presentation control with hand gestures and an ordinary webcam (HCI mini project, AIM4141).

Swipe your hand to change slides, hold up a V sign to pause. Works with PowerPoint, Keynote, Google Slides and PDF slideshows on macOS.

## Quick start
```
git clone https://github.com/priyanshjhaa/GestureVox.git
cd GestureVox
./run.sh
```
The first run installs everything it needs (about a minute). Needs Python 3.9+ and a webcam. Or double-click **`GestureVox.command`** in Finder.

Then open a slideshow, click on it so it's the active window, and swipe.

| Command | What it does |
|---|---|
| `./run.sh` | Start GestureVox (with practice mode) |
| `./run.sh quick` | Start without practice mode |
| `./run.sh study P1` | User study session for participant P1 (log: `logs/P1_...csv`) |
| `./run.sh access` | Large text + left-handed mode |
| `./run.sh v1` | The original v1 prototype, for comparison |
| `./run.sh test` | Run all tests |
| `./run.sh help` | Show all commands |

Extra options are passed through, e.g. `./run.sh quick --no-sound --blackout`.

**macOS permissions (first run):** allow **Camera** for Terminal when asked, and turn on Terminal under **System Settings → Privacy & Security → Accessibility** so it can press the arrow keys. Restart Terminal after changing either.

## Files
| File | What it is |
|---|---|
| `run.sh`, `GestureVox.command` | Launchers (see Quick start) |
| `v2_gesturevox.py` | **Version 2 (the main app):** fixes the v1 problems, adds pause, on-screen feedback, sound, practice mode and logging |
| `gestures.py` | v2 gesture logic: smoothing, motion-based re-arm, return-motion handling, V-sign/fist detection |
| `features.py` | Practice mode, session summary, saved settings |
| `common.py` | Shared hand tracking (MediaPipe) and skeleton drawing |
| `v1_basic.py` | Version 1: swipe left/right only. Deliberately basic (no cooldown, no feedback, no pause), so the heuristic evaluation had real problems to find |
| `test_v2.py`, `test_features.py`, `test_swipe.py` | Tests with simulated data (no webcam needed) |
| `models/hand_landmarker.task` | Google's MediaPipe hand landmark model |
| `study/` | User study kit (see below) |
| `logs/` | One CSV per run (time, event, state). Kept local, not uploaded |

## Gestures
| Gesture | Action |
|---|---|
| Swipe right / left | Next / previous slide |
| Hold V sign (index + middle finger up) still for 1 s | Pause / resume gesture control |
| Hold fist still for 1.5 s | Black screen on / off (PowerPoint, Keynote). **Off by default**, turn on with `--blackout` |

Keys in the camera window: **D** shows the debug readout, **[** / **]** make swipes more / less sensitive, **Q** quits.

### Options
| Flag | What it does |
|---|---|
| `--participant P1` | Names the log file, for the user study |
| `--skip-practice` | Starts without the practice tutorial |
| `--left-handed` | Reverses the swipe directions |
| `--large-text` | Bigger, high-contrast overlay text (yellow messages, white outlines) |
| `--blackout` | Turns on the hold-fist blackout gesture |
| `--no-sound` | Turns off sound feedback |
| `--dry-run` | Shows and logs gestures without pressing keys |

### Learnability and accessibility features
| Feature | How it works | Syllabus link |
|---|---|---|
| Practice mode | On start, a checklist asks for each gesture once (swipe right, swipe left, V sign to pause, V sign to resume). Nothing reaches the slides until all are done; **S** skips. Time per step is logged. | Learnability, help and documentation (Nielsen #10), recognition rather than recall |
| Left-handed / large text | Command-line flags | Universal design, accessibility |
| Saved sensitivity | **[** / **]** changes are saved to `settings.json` and reused next run | Flexibility and efficiency of use (Nielsen #7) |
| Session summary | On **Q**: swipes, pauses, swipes ignored while paused, duration. Shown on screen, printed, and logged as a `summary` row | Visibility of system status |


### What v2 fixed (from the v1 evaluation)
| v1 problem | v2 fix | Heuristic / golden rule |
|---|---|---|
| One swipe fired about 5 times (19 swipes gave 100 triggers) | 0.6 s cooldown: one swipe = one slide (later replaced by motion-based re-arm, see Final tuning) | Error prevention |
| Hand returning after a right swipe counted as a left swipe | Opposite direction ignored for 1 s after a swipe (later: the first opposite movement is always the return, see Final tuning) | Error prevention |
| Jittery, inaccurate detection | Position smoothing + path-efficiency check (motion must be mostly in one direction) | Error prevention |
| No idea if the system is on or saw the hand | Status pill: ACTIVE / PAUSED / NO HAND (colour and text) | Visibility of system status |
| No confirmation of the action | Fading toast + sound for every action | Informative feedback (Shneiderman) |
| Talking with hands changed slides | Hold V sign to pause | User control and freedom |
| Nothing to show gestures | Help bar at the bottom of the window | Recognition rather than recall |

## Run v1
```
./run.sh v1 --dry-run   # prints gestures only
./run.sh v1             # presses arrow keys for real
```
Press **Q** in the camera window to quit.

## Known v1 problems (to log in the heuristic evaluation)
1. One swipe can skip several slides (no cooldown): *error prevention*
2. No status: is it on, does it see my hand? *visibility of system status*
3. Talking with your hands changes slides, and there's no pause: *user control and freedom*
4. No confirmation of which gesture was recognised: *informative feedback* (Shneiderman)
5. The camera window covers the slides: *aesthetic and minimalist design*

## Found while testing v2 (iteration 2 -> 3)
| Problem in the first v2 test run | Evidence (log of 28 s) | Fix |
|---|---|---|
| Pause was an open palm held still, and people swipe with an open palm, so v2 paused itself whenever the hand rested (Midas touch problem) | 4 accidental pauses, 1 swipe ignored while paused | Pause gesture changed to a V sign, which doesn't occur naturally while swiping |
| Swipes hard to trigger | Only 1 swipe recognised | Threshold lowered to 0.10, longer window (0.6 s), less smoothing lag; live adjustment with [ / ] |
| Swipes detected but slides didn't move | Second run log: 9 accidental blackouts in about 3 min. A sideways hand during swipes looked like a fist, B blacked the slides out, and the next arrow key only un-blacked them | Blackout made opt-in (`--blackout`) with a longer 1.5 s hold |
| Camera window kept keyboard focus | Arrow keys reached the camera window instead of the slideshow | Removed "always on top" from the camera window |

## User study kit (`study/`)
| File | Use |
|---|---|
| `1_study_protocol.md` | Moderator script, order of conditions, error definitions, checklist |
| `2_task_cards.md` | The 3 tasks to show participants |
| `3_sus_questionnaire.md` | SUS form + 2 open questions + scoring |
| `4_klm_goms.md` | KLM-GOMS predictions for keyboard vs GestureVox |
| `test_deck.pdf` | 15 numbered slides for the tasks |
| `results.csv`, `sus.csv`, `participants.csv` | Fill these in during the study |

## Final tuning (1 Nov): faster and more accurate swipes
Benchmarking the detector with simulated swipes showed two accuracy bugs that the fixed timers caused:

| Problem | Before | After |
|---|---|---|
| One long, slow swipe across the frame | Fired twice | Fires once |
| 4 quick repeat swipes, 0.55 s apart | Only 2 of 4 fired, plus one wrong-direction "left" | 4 of 4 |
| 4 quick repeat swipes, 0.45 s apart | 2 of 4 fired | 4 of 4 |
| Fastest reliable repeat-swipe cycle | about 0.7 s | about 0.45 s |
| With random tracking noise (±1% of frame width, 50 runs per scenario) | n/a | 100% correct |

**What changed:** the fixed 0.6 s cooldown and 1 s return block became rules based on the hand's motion:
- **Re-arm when the stroke ends:** the next swipe is accepted only once the hand slows down or reverses, so one stroke can never fire twice, and fast users aren't held back by a timer.
- **The first opposite movement after a swipe is the return**, however quickly it comes, unless the hand rested for 0.5 s first (then it counts as a deliberate swipe back).
- **Camera captured at 640×480** (MediaPipe works at about 224 px internally), with the overlay drawn at full size, for lower lag per frame.

### Final check (1 Nov)
A code review and extra simulations before the study found and fixed:

| Issue | Effect | Fix |
|---|---|---|
| Hand lowered slowly after a swipe (slower than about 0.35 frame widths/s) | Two false "previous slide" swipes | "Resting" now means the hand actually stayed still (moved less than 3% in 0.5 s); swipes must reach a peak speed of 0.4 widths/s |
| Mouse pointer parked in a screen corner | pyautogui's fail-safe would crash the app on the next key press | Fail-safe off (the app never moves the mouse) |
| pyautogui's default 0.1 s pause after each key press | Camera loop froze briefly on every swipe | Pause set to 0 |
| Two camera frames in the same millisecond | MediaPipe would crash | Timestamps forced to increase |
| `--left-handed` practice checklist | Told users the wrong physical direction | Shows the reversed directions |

## Run the tests
```
./run.sh test
```
