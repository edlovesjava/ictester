# docs/superpowers

How work gets planned. Each increment gets a **spec** (what and why, how each step is checked), then a
**plan** (the exact changes, step by step). Work is built in small end-to-end steps, each checked
(on the bench where possible) before the next.

## Lifecycle

1. **Spec** written in [specs/](specs/) → status *In review*.
2. You review it; changes go into the same file → status *Approved*.
3. **Plan** written in `plans/` from the approved spec → status *In review*, then *Approved*.
4. Steps are built one commit each → spec status *In progress*, then *Done* once every step's check has
   passed.

If what we learn at the bench changes the design, update the spec first, then the plan. Never let them
drift from what was built.

## Index

| Spec | Plan | Status |
|---|---|---|
| [Stage 0: Nano + 7400 on a breadboard](specs/2026-09-26-stage0-nano-breadboard-design.md) | – | Spec in review |
