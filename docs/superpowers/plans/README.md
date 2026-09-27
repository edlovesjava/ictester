# docs/superpowers/plans

One implementation plan per approved spec: the exact changes, task by task, each ending in a check. The
index with each plan's status is in [../README.md](../README.md).

## Rules

- **Name:** `YYYY-MM-DD-<topic>.md`, matching the spec's topic (spec `…-stage0-nano-breadboard-design.md` →
  plan `…-stage0-nano-breadboard.md`).
- **Written only from an approved spec.** If the plan needs something the spec doesn't say, change the
  spec first.
- **Tasks:** one task per spec step, one commit per task. The next step in detail, with complete code, so
  it can be followed without reading anything else. Later steps can be lighter, and are filled in before
  they start.
- **Code in a plan is compiled before the plan is handed over.** Prototype it in a scratch copy of the
  firmware, not in the repo.
- **Checks are concrete:** the command to run and the expected output or measurement. Changes to the
  portable core are test-first: failing `make test`, then passing.
- **Progress:** tick the `- [ ]` boxes as steps are done, in the same commit as the work.

## Template

````markdown
# <Topic>. Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** one sentence.
**Architecture:** two or three sentences.
**Tech Stack:** toolchain, versions.
**Spec:** link.

## Global Constraints
One line each, copied from the spec.

## Review Focus
The likely failure modes no task's test covers, and where each gets checked.

---

### Task N: <step name>

**Files:** Create / Modify / Test, with exact paths.
**Interfaces:** Consumes / Produces, with exact names and types.

- [ ] **Step 1: ...** (one action each: write failing test, run it, implement, run it, bench check, commit)
````
