# KLM-GOMS analysis: keyboard vs GestureVox

The **Keystroke-Level Model (KLM)**, the simplest member of the GOMS family (Card, Moran & Newell, 1980), predicts how long an **expert** takes to do a task **without errors**, by adding up standard times for each physical and mental operator. Here it predicts task times for the keyboard and for GestureVox before the user study, and the predictions are compared with the measured times afterwards.

## 1. Operators

### Standard KLM operators (Card, Moran & Newell)
| Operator | Meaning | Time |
|---|---|---|
| **K** | Press a key (average non-secretarial typist) | 0.28 s |
| **H** | Home the hand onto a device (e.g. table → keyboard) | 0.40 s |
| **M** | Mental preparation (deciding / recalling what to do) | 1.35 s |
| **B** | Press or release a mouse button (a click = BB) | 0.10 s |

### New operators for gesture input
KLM has no gesture operators, so these were defined for this project. Following KLM's expert, error-free assumption, the swipe-cycle time uses the **fastest** interval measured in the dry run with the final version.

| Operator | Meaning | Time | Source |
|---|---|---|---|
| **Hg** | Raise the hand from the table into the camera's view | 0.80 s | Estimate (2 × H, since the whole arm moves); check against the study video |
| **G** | One swipe stroke, including detection | 0.50 s | About 0.4 s stroke + about 0.1 s for the smoothing and detection window |
| **S** | Repeat-swipe cycle: return the hand to the start, then the next stroke | 1.05 s | Dry run with the final version (P0, 1 Nov): 7 consecutive same-direction swipes, 1.03–1.66 s apart (median 1.17 s); fastest rounded to 1.05 s |
| **F** | Form a hand pose (e.g. V sign) | 0.40 s | Estimate (similar to one homing movement) |
| **Hd** | Hold a pose still until it triggers | 1.00 s | Fixed by design (`HoldDetector`, peace = 1.0 s) |

**How S changed across iterations:** with the earlier detector (fixed 0.6 s cooldown, 1 s return block), the fastest pilot cycle was 1.10–1.20 s (31 Oct logs). The final detector uses motion-based rules and can handle cycles down to about 0.45 s in simulation. The measured 1.05 s is therefore now limited by **how fast a person moves their arm back and forth**, not by the software.

## 2. Task predictions
All tasks start with the participant's hands resting on the table, matching the study protocol. One **M** is placed at the start of each task (deciding what to do). Repeated presses or swipes of the same kind don't get extra M operators, following the standard KLM placement rules.

### Task 1: slide 1 → slide 5 (4 × forward)
| Method | Operator sequence | Calculation | Predicted |
|---|---|---|---|
| Keyboard | M H K K K K | 1.35 + 0.40 + 4 × 0.28 | **2.87 s** |
| Mouse (click to advance) | M H BB BB BB BB | 1.35 + 0.40 + 4 × 0.20 | **2.55 s** |
| GestureVox | M Hg G S S S | 1.35 + 0.80 + 0.50 + 3 × 1.05 | **5.80 s** |

### Task 2: slide 5 → slide 3 (2 × back)
| Method | Operator sequence | Calculation | Predicted |
|---|---|---|---|
| Keyboard | M H K K | 1.35 + 0.40 + 2 × 0.28 | **2.31 s** |
| GestureVox | M Hg G S | 1.35 + 0.80 + 0.50 + 1.05 | **3.70 s** |

### Task 3: pause, talk for 5 s, resume, then forward 1 slide (gesture only)
| Step | Operators | Time |
|---|---|---|
| Pause | M Hg F Hd | 1.35 + 0.80 + 0.40 + 1.00 = 3.55 s |
| Talk with hands (fixed by the task) | none | 5.00 s |
| Resume | M F Hd | 1.35 + 0.40 + 1.00 = 2.75 s |
| Next slide | G | 0.50 s |
| **Total** | | **11.80 s** (6.80 s excluding the talking) |

The keyboard has no equivalent: pausing isn't needed because hand movements can't trigger key presses.

## 3. Summary of predictions
| Task | Keyboard | GestureVox | Ratio (gesture / keyboard) |
|---|---|---|---|
| T1: 4 forward | 2.87 s | 5.80 s | 2.0× |
| T2: 2 back | 2.31 s | 3.70 s | 1.6× |
| T3: pause-talk-resume-forward | n/a | 11.80 s | n/a |

## 4. What the model tells us
1. **Gestures are predicted to be slower** for a person sitting at the laptop: about 1.6–2.0×. This is expected; the keyboard is one of the fastest input devices there is. GestureVox's value isn't raw speed at the desk, but **hands-free use away from the laptop** (presenting while standing, accessibility, busy or dirty hands). KLM has no operator for walking to the laptop, so it can't capture that benefit.
2. **The gap grows with the number of slides.** Each extra slide costs 0.28 s by keyboard but 1.05 s by gesture (operator S). For jumping many slides, a dedicated gesture (e.g. "hold two fingers to skip 5") would help.
3. **Speed vs. error prevention was a design trade-off, and iteration reduced its cost.** The first v2 used a fixed cooldown to stop v1's double triggers (19 swipes → 100 triggers), which made S 1.10–1.20 s. Replacing the timers with motion-based rules kept the error prevention but removed the software delay: S is now 1.05 s, limited by the human arm rather than the system (design rationale).
4. **Pausing costs about 3.5 s**, mostly from M and the 1-second hold. The hold is deliberately long so that it can't trigger by accident (the open-palm Midas touch problem found in iteration 2).

## 5. Predicted vs. measured (fill in after the study)
| Task | Method | KLM predicted | Measured mean (n = 5) | Difference |
|---|---|---|---|---|
| T1 | Keyboard | 2.87 s | | |
| T1 | GestureVox | 5.80 s | | |
| T2 | Keyboard | 2.31 s | | |
| T2 | GestureVox | 3.70 s | | |
| T3 | GestureVox | 11.80 s | | |

**Expect the measured times to be higher than predicted**, especially for gestures. KLM assumes expert, error-free users, while participants are novices who've had about 30 seconds of practice, and any missed or wrong gesture adds time. The results script fills in this table automatically.

## References
- Card, S. K., Moran, T. P., & Newell, A. (1980). The keystroke-level model for user performance time with interactive systems. *Communications of the ACM*, 23(7), 396–410.
- Dix, A., Finlay, J., Abowd, G. D., & Beale, R. (2004). *Human–Computer Interaction* (3rd ed.), ch. 12: Cognitive models. Pearson.
