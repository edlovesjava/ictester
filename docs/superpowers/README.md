# docs/superpowers

How work gets planned. Each increment gets a **spec** (what and why, how each step is checked), then a
**plan** (the exact changes, step by step). Work is built in small end-to-end steps, each checked
(on the bench where possible) before the next.

| Path | Purpose |
|---|---|
| [roadmap.md](roadmap.md) | Outline from stage 0 to breadboard MVP, perfboard and PCB. Updated as stages land. |
| [specs/](specs/) | One spec per increment. Rules and template in its README. |
| [plans/](plans/) | One plan per approved spec. Rules and template in its README. |

## Lifecycle

1. **Spec** written in `specs/` → status *Spec in review*.
2. You review it; changes go into the same file → *Spec approved*.
3. **Plan** written in `plans/` from the approved spec → *Plan in review*, then *Plan approved*.
4. Steps are built one commit each → *In progress (step n)*, then *Done* once every step's check has
   passed.

If what we learn at the bench changes the design, update the spec first, then the plan, then the
roadmap if it's affected. Never let them drift from what was built.

## Index

| Spec | Plan | Status |
|---|---|---|
| [Stage 0: Nano + 7400 on a breadboard](specs/2026-09-26-stage0-nano-breadboard-design.md) | [plan](plans/2026-09-26-stage0-nano-breadboard.md) | In progress: steps 1–4 done (ID finds the 7400; 5-min soak clean) |
