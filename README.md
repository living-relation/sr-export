# SR Export

A Spark Robotic Fusion add-in that exports STEP, F3D, STL, 3MF, IGES, SAT and DXF in one click, to a
folder you pick, overwriting in place.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **Toolbar button** "SR Export" in the Design workspace, Solid tab, **Add-Ins** panel (also listed under Utilities > Add-ins).
- A checkbox per file type. Pick a folder once; it is remembered.
- Files are named after the design (Fusion's ` v12` suffix dropped), so each export **overwrites in place**.
- Optional: pick one component to export just that. DXF needs a selected sketch or flat face.
- IGES and SAT may be blocked on a non-commercial Fusion plan; the result list says so if they are.

## Requirements

- Autodesk Fusion

## Install

1. Clone this repo and keep the folder on disk.
2. In Fusion: **Utilities > Add-ins > Scripts and Add-ins > Add-ins tab > + (green plus)**, and pick the `SRExport` folder inside the clone. Tick **Run on Startup** and click **Run**.

   Or copy or link the `SRExport` folder into `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` and restart Fusion.
3. The button shows up in the Add-Ins panel.

Settings (last folder and checked types) are saved in `%APPDATA%\SRExport\`.

See [docs/install.md](docs/install.md) for the full steps, including uninstall.

## Usage

Open a design, click **SR Export**, tick the formats you want, and confirm the folder. See [docs/usage.md](docs/usage.md).

## Documentation

- [Overview](docs/overview.md)
- [Install](docs/install.md)
- [Usage](docs/usage.md)
- [Development](docs/development.md)
- [Documentation index](docs/README.md)

## Development

```
python tools/check.py
```

CI runs the same check. `dev/fusion_smoke.py` is a live test that runs inside Fusion. See [docs/development.md](docs/development.md).

## Contributing

Work on a branch and open a pull request against `main`. Update `docs/` when behavior changes. See [docs/development.md](docs/development.md) and [AGENTS.md](AGENTS.md).

## License

This project is licensed under the [MIT License](LICENSE). Copyright (c) 2026 Spark Robotic.
