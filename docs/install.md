# Install

## Requirements

- Autodesk Fusion
- This repository, cloned or downloaded to a folder you can keep on disk

## Add the add-in in Fusion

1. Open Autodesk Fusion.
2. Open **Utilities > Add-ins > Scripts and Add-ins** (Shift+S in current builds).
3. Open the **Add-Ins** tab.
4. Click the green **+** and pick the `SRExport` folder inside your clone. That folder contains `SRExport.py` and `SRExport.manifest`. Do not pick the repository root.
5. Select **SR Export**, tick **Run on Startup**, and click **Run**.
6. The **SR Export** button appears in the Design workspace, Solid tab, Add-Ins panel.

Alternatively, copy or link the `SRExport` folder into `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` and restart Fusion. A directory junction works well: updating the clone and restarting the add-in (Stop, then Run) picks up the new files.

If Fusion does not list the add-in, confirm you pointed at `SRExport`, not the repo root. The helper library lives inside that folder (`SRExport/sr_fusion_common/`), so the add-in is self-contained.

## Uninstall

In the same Scripts and Add-Ins dialog, select **SR Export**, click **Stop**, then remove it from the list if Fusion provides that option. You can also delete a junction or copy under the AddIns folder. Settings in `%APPDATA%\SRExport\` are left in place unless you delete them yourself.

## Next

See [Usage](usage.md) after the add-in is installed.
