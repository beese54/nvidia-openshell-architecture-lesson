# Plan: Interactive architecture diagram and lesson on NVIDIA OpenShell

Status: **built and verified, 2026-11-12.** Two decisions remain open (see the end).

## Goal
One page that lets you understand OpenShell from the inside, and a guided lesson on top of it that carries over to running AI agents safely in general.

- **Explore mode:** every component, every boundary, and the path each kind of request takes. Hover over, tap or tab to any part and a panel explains it.
- **Learn mode:** nine short modules that use the same figures, with a predict-first question, recall checks, a command to run yourself, and the general principle.

Each panel has: an **ELI5** line (the playroom and babysitter analogy), **How it really works**, **Evidence** with a badge and audit row ids, and where relevant a **Gotcha** and a version note.

| Badge | Meaning |
|---|---|
| `OBSERVED` | seen on a real machine running 0.1.2 |
| `SOURCE` | read in NVIDIA/OpenShell at tag `v0.1.2` |
| `DOCS` | NVIDIA's docs as shipped with `v0.1.2` |
| `INFERRED` | reasoning, not proven |

## Scope
OpenShell **0.1.2 with the Docker driver on WSL 2**. Latest is 0.1.8. Anything not used in this setup (VM and Kubernetes drivers, providers, middleware) gets a note instead of being drawn as fact.

## Steps
- [x] 1. **Gather evidence.** `tasks/doc_audit.md` built from a live inspection and the OpenShell source at tag `v0.1.2`.
- [x] 2. **Close the gaps.** More source reading, then two live runs in throwaway sandboxes: run A (deny all) and run B (allow one host). Raw output in `evidence/runs/`.
- [x] 3. **Wireframe check.** Figure 1's arrows name mechanisms (`gRPC + mTLS`, `Docker API`, outbound session, channel).
- [x] 4. **Vertical slice**, then
- [x] 5. **the rest:** five figures, the limits strip, five request scenarios, nine lesson modules, the policy simulator with a seven-test capstone.
- [x] 6. **Verify.** See the review below.
- [x] 7. **Review.** Below.

## Review (2026-11-12)

### What was built
- `index.html`: one self-contained file, no libraries, opens by double-click.
  - Figure 1, system map, with step-through scenarios for exec, `connect()`, DNS lookup, file write and upload.
  - Figure 2, where each part of the policy file is enforced, with the deny-all and allow-example policies.
  - Figure 3, twelve locks in four groups on one shared kernel.
  - Figure 4, the `connect()` sequence with its deny and allow endings.
  - Figure 5, startup order, phases, the fail-closed sequence and generation identity.
  - A limits strip and a policy simulator.
- 87 panels, 26 scenario steps, 40 quiz questions.
- `tasks/doc_audit.md`: 100 claims. 95 verified (34 of them from source only), 1 corrected, 3 inferred, 1 unverified and not shown.

### How it was checked
- `python scripts/check_content.py`: every one of the 277 citation lists in the page points at an audit row that exists and is not unverified. Evidence that rests only on inferred rows carries the INFERRED badge.
- `scripts/selftest.sh` runs the page's built-in self-test in headless Chrome at 1440px and inside a 375px frame. It opens and pins all 87 panels and checks each fits the screen and has a badge; steps all 26 scenario steps and checks the right boxes light up; clicks every option of all 40 questions and checks the feedback; runs 10 simulator cases plus the capstone reference solution; and checks the page does not scroll sideways. Both widths pass with no failures.
- Screenshots were reviewed by eye for all figures at desktop width, light and dark, for a lesson module and the simulator, and for two views at 375px. Three defects were found and fixed: a hidden title in Figure 1, message numbers in Figure 4 that did not match their panels, and bold labels breaking onto their own line in Figure 2.

### What was not checked
- **No real browser session.** Everything ran in headless Chrome. Hover and touch were exercised through events, not a hand; Safari and Firefox were not tried.
- **"Try it" outputs are taken from the two recorded runs**, not from running each lesson command on its own afterwards. The commands are the ones in `evidence/inspect.sh` and `evidence/probe.py`, apart from two `grep` filters.
- **Reader simulation was done by the author.** Walking module 3 cold, the `connect()` path can be explained from Figure 4 and its panels alone. No second person has tried it.
- **Never tested live, shown with the SOURCE badge only:** the fail-closed freeze, a changed-binary denial, provider credentials, rule proposals, live policy updates, stop and start.

### Findings worth keeping
- The `connect()` mechanism is seccomp user notification. There is no proxy variable; a denial is `EACCES` in under 10 ms; an unused loopback port gives `ECONNREFUSED`, so `EACCES` specifically means "policy said no".
- The SSH server that receives exec belongs to the supervisor, not the workload. An early draft had this wrong.
- The agent only ever sees placeholder addresses (`198.18.x.x`), even on an allowed connection. The supervisor resolves, pins and dials the real ones.
- The log reports `NET:LISTEN 127.0.0.1:3128`, but nothing answers there from the workload or the host.
- `landlock.compatibility: best_effort` means that if file rules cannot be applied, the sandbox runs without them.
- Request rules default to `audit`, which logs and allows.
- The gateway refuses connections for a few seconds after WSL starts; scripts must wait for `openshell status`.

### Privacy
The page was first written with links into a private project. Those were removed from everything published. Rows that rest on that project's notes are marked `OBS-P` in the audit and say so. A local, uncommitted `local/project_links.js` can add an "In your project" section to panels for the author's own use; the published page works without it.

## Open decisions
1. **Licence:** none chosen. Without one, others may read the repository but not reuse it.
2. **GitHub Pages:** not enabled. Turning it on would make the page openable on a phone by URL.
