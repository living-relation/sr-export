# SR Export

A Spark Robotic Fusion add-in that exports STEP, F3D, STL, 3MF, IGES, SAT and DXF in one click, to a
folder you pick, overwriting in place.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## How this add-in is installed

**SR Export is junctioned straight to the repo clone**, so a `git pull` updates what Fusion loads. Fusion's AddIns entry must be named exactly `SRExport` and must point at the `SRExport` folder inside this repo, not the repo root.

Fusion does not pick up new code until the add-in restarts: restart Fusion, or press **Shift+S**, open **Add-Ins**, and **Stop** then **Run**.

An automatic updater (coming soon, in the workstation repo) will pull updates hourly and notify you to restart Fusion.

To create the junction, open a normal Command Prompt (not Run as administrator). `mklink /J` does not need elevation. Both paths below are absolute, so no `cd` is required. Run:

```
mklink /J "%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SRExport" "<path-to-this-clone>\SRExport"
```

Replace `<path-to-this-clone>` with this repo's clone path on that PC. The active-folder path differs per PC.

## Features

- **Toolbar button** "SR Export" on several Design-workspace panels, including the **SR Tools** panel on the SOLID tab, plus Add-Ins, Make, and Insert. The panel list is configurable in `%APPDATA%/SRExport/panels.json`.
- A checkbox per file type. Pick a folder once; it is remembered.
- Files are named after the design (Fusion's ` v12` suffix dropped), so each export **overwrites in place**.
- Optional: pick one component to export just that. DXF needs a selected sketch or flat face.
- Every STEP gets a `<name>.bom.json` beside it with the BOM, mass properties, hole and thread data, and the source document, for the drawing sheet editor. See [docs/sidecar-schema.md](docs/sidecar-schema.md).
- IGES and SAT may be blocked on a non-commercial Fusion plan; the result list says so if they are.

## Requirements

- Autodesk Fusion

## Install

1. Clone this repo and keep the folder on disk.
2. Create the AddIns junction as described in [How this add-in is installed](#how-this-add-in-is-installed). Do not copy the folder into AddIns; a copy will not follow `git pull`.
3. In Fusion, press **Shift+S**, open the **Add-Ins** tab, select **SR Export**, tick **Run on Startup**, and click **Run**. After a later `git pull`, restart the add-in the same way (**Stop**, then **Run**) or restart Fusion.
4. The button shows up on the default panels listed in [Where the buttons go](#where-the-buttons-go).

Settings (last folder and checked types) are saved in `%APPDATA%\SRExport\`.

See [docs/install.md](docs/install.md) for the full steps, including uninstall.

## Where the buttons go

The **SR Export** button can show on several Design-workspace toolbar panels at once. By default it is added to:

- **Utilities > Add-ins** (`SolidScriptsAddinsPanel`)
- **Make** (`SolidMakePanel`)
- **Insert** (`InsertPanel`)
- **SR Tools** (`SRToolsPanel`)

By default the button is pinned on SR Tools and on Add-ins. Insert and Make still get the command; Fusion keeps your own pin or unpin choice after the first run.

The list lives in `%APPDATA%\SRExport\panels.json`. Create or edit that file, then Stop and Run the add-in (or restart Fusion) so the change takes effect. Example:

```json
{
  "panel_ids": [
    "SolidScriptsAddinsPanel",
    "SolidMakePanel",
    "InsertPanel",
    "SRToolsPanel"
  ]
}
```

Unknown panel ids are skipped. If the file is missing or `panel_ids` is empty or unusable, the defaults above are used. Stopping the add-in removes every toolbar button for this command, including leftovers from an older list.

If `SRToolsPanel` already exists (for example because another SR add-in created it on the SOLID tab), this add-in reuses it. If it does not exist, this add-in creates an **SR Tools** tab in the Design workspace and puts the panel on that tab. If the panel (and its tab) are empty after stop, they are removed too.

## Usage

Open a design, click **SR Export**, tick the formats you want, and confirm the folder. See [docs/usage.md](docs/usage.md).

## Documentation

- [Overview](docs/overview.md)
- [Install](docs/install.md)
- [Usage](docs/usage.md)
- [BOM sidecar JSON](docs/sidecar-schema.md)
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
