# Development

**SR Export** is a Fusion add-in written in Python.

## Clone

```
git clone https://github.com/living-relation/sr-export.git
```

Load the `SRExport` folder into Fusion as described in [Install](install.md).

## Layout

- `SRExport/` — the Fusion add-in (junction this folder into AddIns). Entry point: `SRExport.py` and `SRExport.manifest`.
- `SRExport/sr_fusion_common/` — settings and file-name helpers, vendored so the add-in stands alone.
- `SRExport/export_core.py` — pure path and summary helpers (no Fusion import); unit-tested.
- `SRExport/export_ops.py` — Fusion-side export calls. After a STEP succeeds it writes the BOM sidecar.
- `SRExport/sidecar_core.py` — pure sidecar helpers: schema, unit conversion, thread-table parsing and tap-drill lookup, hole callouts (no Fusion import); unit-tested.
- `SRExport/sidecar_ops.py` — reads the design for the sidecar (components, mass properties, holes, thumbnails). Tested against a small fake `adsk` in `tests/test_sidecar.py`.
- `docs/sample.bom.json` — example sidecar, generated from the test fixture.
- `tests/` — unit tests that do not need Fusion.
- `dev/fusion_smoke.py` — live test that runs inside Fusion.
- `tools/check.py` — secret/path scan plus pytest. CI runs the same command.

## Coding notes

- This repository is public. Do not commit secrets, tokens, passwords, personal email addresses, machine-specific paths, or vendor CAD files.
- Keep Spark Robotic / SR- naming in user-visible text and repository docs.
- Work on a branch and open a pull request against `main`. Never commit to `main` directly.
- Run `python tools/check.py` before every push. See [AGENTS.md](../AGENTS.md).

## Tests

```
python tools/check.py
```

`dev/fusion_smoke.py` is a live test. Take the machine's Fusion lock first. It opens a new scratch design, exports every format, registers and removes the button, then closes the design without saving. Output goes to `%TEMP%\srexport_fusion_smoke`. Your open documents are not touched.

## Contributing

1. Create a branch from `main`.
2. Add or update documentation in `docs/` when behavior changes.
3. Run `python tools/check.py`.
4. Open a pull request against `main`. CI must stay green.
