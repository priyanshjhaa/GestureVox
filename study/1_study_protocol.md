# GestureVox user study: protocol and moderator script

**Goal:** compare GestureVox (gesture control) with the keyboard arrow keys for controlling a presentation, measuring **task time**, **errors** and **satisfaction (SUS)**.

**Design:** within-subjects. Every participant uses both conditions, and the order alternates between participants to balance out the learning effect.

| | |
|---|---|
| Participants | 5 classmates (Nielsen: 5 users find about 85% of usability problems) |
| Time per participant | About 12 minutes |
| Condition A | Keyboard: Right / Left arrow keys |
| Condition B | GestureVox v2: swipes and V-sign pause |
| Measures | Task time (stopwatch), errors, task completion, SUS score, practice time (from the log) |

## Order of conditions (counterbalancing)
| Participant | First | Second |
|---|---|---|
| P1 | A Keyboard | B Gesture |
| P2 | B Gesture | A Keyboard |
| P3 | A Keyboard | B Gesture |
| P4 | B Gesture | A Keyboard |
| P5 | A Keyboard | B Gesture |

## What to have ready
- [ ] Laptop on a table, in a well-lit room (light in front of the participant, not behind)
- [ ] `study/test_deck.pdf` open in Preview (View → Slideshow), or imported into Keynote/PowerPoint
- [ ] Terminal open in the GestureVox folder
- [ ] Phone stopwatch
- [ ] Printed or on-screen: `2_task_cards.md`, `3_sus_questionnaire.md`
- [ ] `results.csv`, `sus.csv` and `participants.csv` open to fill in (or write on paper and type up later)

Participants sit at the laptop for both conditions, hands resting on the table before each task.

## Error definitions (count each one)
| Error | Example |
|---|---|
| Wrong direction | Slide went back when the participant swiped or pressed forward |
| Overshoot | Skipped past the target slide |
| Missed gesture | Participant clearly swiped or pressed, nothing happened, and they had to repeat |
| Accidental pause / action | System paused, or a slide changed, without the participant meaning it |

A task counts as **completed** if the participant reaches the target slide within 30 seconds.

---

## Script (read aloud)

### 1. Welcome (1 min)
> "Thanks for helping. I'm testing a system that lets you control slides with hand gestures. I'm testing the system, not you: if something goes wrong, that's the system's fault, and it's useful for me. It takes about 12 minutes. I'll time a few short tasks and ask you to fill in a 10-question form at the end. Your name won't appear in my report, just P1, P2 and so on. Is that OK?"

Note their verbal consent, then fill in `participants.csv`: age, handedness, and whether they've used gesture control before (e.g. Kinect, smart TV).

### 2. Condition A: Keyboard (2 min)
1. Open the slideshow at **slide 1**.
2. > "Use only the Right and Left arrow keys. Rest your hands on the table. When I say *go*, do the task, and say *done* when you're there."
3. Run **Task 1** and **Task 2** from the task cards. Start the stopwatch on "go" and stop it when the target slide appears.
4. Record the time and errors for each task in `results.csv`.

(Task 3 is gesture-only: the keyboard has no pause to compare.)

### 3. Condition B: GestureVox (6 min)
1. Start GestureVox with practice mode on, using the participant's code:
   ```
   ./run.sh study P1
   ```
   For a left-handed participant, ask whether they'd like reversed swipes (`./run.sh study P1 --left-handed`), and note it.
2. **Practice:**
   > "First, a short practice. The camera window shows a checklist: swipe right, swipe left, then hold up a V sign, like this, to pause, and again to resume. Nothing happens to the slides yet."

   Demonstrate each gesture once. Let them complete the checklist; the log records how long it takes.
3. When it says **"Ready!"**, click on the slideshow (so it receives the key presses) and go to **slide 1**.
4. > "Same as before: hands on the table, I say *go*, you say *done*."
5. Run **Task 1**, **Task 2** and **Task 3**. Time each one and count errors.
6. Press **Q** in the camera window. The session summary appears and is saved in the log.

### 4. Questionnaire (3 min)
Give them `3_sus_questionnaire.md`.
> "Please answer these about the gesture system, not the keyboard. Go with your first reaction."

Then ask the two open questions at the end of the form and write down their answers.

### 5. Thank them
> "That's it, thanks a lot! That was really helpful."

---

## After each participant
- Check that `logs/P#_....csv` exists. It holds the practice time and every gesture.
- Write down anything notable in the `notes` column (e.g. "kept swiping too slowly", "laughed when it paused").

## After all participants
Ask me to run the results script. It reads `results.csv`, `sus.csv`, `participants.csv` and the logs, then makes the charts and summary table for the report.
