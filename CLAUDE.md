# ictester: working notes

- Work in small end-to-end increments, each checked (on the bench where possible) before the next.
- Run shell commands through the Bash tool (Git Bash), never PowerShell: the Makefile recipes need `sh`.
- Run `cd firmware && make test` before and after any change to `tester.c`, `cmd.c`, `tools/chips.py` or
  `chips_db.c`. It must end with `ALL TESTS PASSED (0 failures)`. See README → Tests for setup.
- Every folder has a `README.md` that says what the folder is for or indexes its contents. Add one with any
  new folder, and update it when files are added, removed or change purpose.
- `make test` does not cover the hardware layer (`hal_*.c`, pin maps, wiring). Those changes need a bench check.
