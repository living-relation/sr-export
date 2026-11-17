# Usage

## Before you start

1. Install the add-in as described in [Install](install.md).
2. Open the Fusion design you want to export.

## Run

Click **SR Export** on the **SR Tools** tab, or in the Design workspace Add-Ins, Make, or Insert panel.

- **File name:** defaults to the design name, with Fusion's version suffix stripped. You can edit it.
- **Folder:** the last folder is remembered. Use **Choose folder...** to pick another.
- **File types:** tick any of STEP, F3D, STL, 3MF, IGES, SAT, and DXF.
- **Component (optional):** leave empty to export the whole design, or pick one occurrence to export just that component.
- **DXF source:** required only when DXF is ticked. Pick a sketch or a flat face.

If no design is open, the add-in asks you to open one first. If you tick DXF and do not pick a sketch or face, that format is reported as failed and the others still run.

## Results

A result list reports OK or FAILED for each format, including the path or the error. IGES and SAT may be blocked on a non-commercial Fusion plan; the list will say so. Files overwrite in place when the name and folder stay the same.

## Limits and known issues

- DXF needs a selected sketch or planar face. A non-flat face is rejected.
- IGES and SAT can be blocked by the Fusion plan. The add-in still offers them and reports the block instead of stopping the rest of the batch.
