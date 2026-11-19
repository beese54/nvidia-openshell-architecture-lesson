# Lessons

## 2026-11-19: test a walkthrough the way a reader uses it
- **What happened:** the first version of the "Start here" tour showed only the current step's number on the map. Clicking that number restarted the tour, so the reader saw "1" and nothing else. The self-test passed because it called `setScenario()` directly instead of clicking.
- **Rule:** for any guided or step-through UI, simulate the clicks a reader would make (the start button, the visible marker, Next, the arrow keys) and check that the step changes. Anything on screen that looks clickable must move the reader forward, never back to the start.
- **Rule:** a walkthrough should show where it is going, not only where it is: show all the steps, mark the current one and the next one.
