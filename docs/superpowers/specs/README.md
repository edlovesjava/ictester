# docs/superpowers/specs

One spec per increment: what is being built, why, and how each step is proven. The index with each
spec's status is in [../README.md](../README.md).

## Rules

- **Name:** `YYYY-MM-DD-<topic>-design.md`, dated the day the spec was first written.
- **Size:** about a page. A spec covers one increment in detail; anything later is an outline of a few
  lines, and gets its own spec when we reach it.
- **Steps:** every step is one commit and ends in a check someone can run, on the bench where the
  change touches hardware. Steps that touch `tester.c`, `cmd.c` or the chip DB also need `make test`
  before and after.
- **Changes after approval:** edit the spec in place and note the change in the commit message. Update
  the index status in `../README.md` in the same commit.

## Template

```markdown
# <Stage or feature>: <one-line summary>

**Goal.** What this increment proves or delivers, and on what hardware.

**Done when.** The observable checks that close it out.

**Not in <this increment>.** What is deliberately left out.

## <Design sections as needed: wiring, firmware, API ...>

Tables for pin maps and connections; short bullets for decisions, each with its reason.

## Steps

| # | Step | Change | Check |
|---|---|---|---|
| 1 | <name> | <what changes> | <command or measurement, and the expected result> |

If a step fails, debug it at that step. Don't move on with a known failure.

## Later (outline only)

- **<next increment>:** one or two lines.
```
