# tools

Python generators. Their outputs are checked in, so run them only after changing them or their data.

| Script | Produces | Notes |
|---|---|---|
| [chips.py](chips.py) | `firmware/src/chips_db.c`, `docs/chips.txt` | The chip database: pinouts, behavioural models, stimulus. Checks every chip as it generates. Run `make test` afterwards. |
| [design.py](design.py) | (data only) | Single source of truth for stage 1 connections. Read by the three scripts below. |
| [blocks.py](blocks.py) | `docs/stage1/sch-0-blocks.*` | Block diagram / sheet index |
| [sheets.py](sheets.py) | `docs/stage1/sch-1…5-*.*` | Stage 1 schematic sheets |
| [wiring.py](wiring.py) | `docs/stage1/WIRING.md` | Wiring tables and BOM |
| [schlib.py](schlib.py) | (library) | Minimal SVG schematic drawing library used by `sheets.py` |
| [old-1284p/](old-1284p/) | `docs/old-1284p/` schematics | Superseded 1284P drawings, kept for reference |
