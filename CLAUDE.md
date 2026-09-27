# ictester: working notes

- Work in small end-to-end increments, each checked (on the bench where possible) before the next.
- Run shell commands through the Bash tool (Git Bash), never PowerShell: the Makefile recipes need `sh`.
- Run `cd firmware && make test` before and after any change to `tester.c`, `cmd.c`, `tools/chips.py` or
  `chips_db.c`. It must end with `ALL TESTS PASSED (0 failures)`. See README → Tests for setup.
- Folder READMEs:
  - **Doc folders (everything under `docs/`) must have a `README.md`** that states the folder's purpose, the
    format or template its files follow, the rules for changing them (generated? frozen? who edits?), and
    an index of what is there. Read it before adding to the folder, and update it in the same commit.
  - **Code and tool folders** get a short README only when the folder is a meaningful unit (`firmware/`,
    `firmware/test/`, `host/`, `tools/`). Folders that are just path segments (e.g. Java package
    directories) don't get one.
- `make test` does not cover the hardware layer (`hal_*.c`, pin maps, wiring). Those changes need a bench check.
