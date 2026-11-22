# Overview

SR Export is a Spark Robotic add-in for Autodesk Fusion. It exports the active design (or one
selected component) to a folder you pick, in the formats you tick, overwriting files of the same
name in place.

It is part of the Spark Robotic (SR-) tool set for Fusion.

## Features

- A toolbar button named **SR Export** on the **SR Tools** panel on the SOLID tab, and on the Add-Ins, Make, and Insert panels, in the Design workspace.
- Formats: STEP, Fusion archive (F3D), STL, 3MF, IGES, SAT, and DXF of a selected sketch or flat face.
- File names use the design name with Fusion's ` v12` version suffix stripped, so a later export replaces the previous files.
- Optional component selection to export just that component.
- A BOM and model-data JSON next to every STEP (`<name>.bom.json`) for drawing BOMs and hole callouts. See [BOM sidecar JSON](sidecar-schema.md).
- The last folder and checked types are remembered.

IGES and SAT may be blocked on a non-commercial Fusion plan. The result list says so if they are.

## Requirements

- Autodesk Fusion

## Settings

The last folder, checked types, and last file name are saved in `%APPDATA%\SRExport\`.

## Further reading

- [Install](install.md)
- [Usage](usage.md)
- [Development](development.md)
