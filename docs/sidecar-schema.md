# BOM sidecar JSON (`<name>.bom.json`)

Every STEP that SR Export writes gets a sidecar JSON next to it, with the same base name:
`Part.step` → `Part.bom.json`. It carries the BOM and model data that a STEP file cannot: quantities,
part numbers, descriptions, materials, mass properties, hole and thread data, and the source document.
It is written for the SR drawing sheet editor (BOM tables and hole callouts), but any tool can read it.

The sidecar is written only when the STEP export succeeds. If the sidecar fails, the STEP still counts
as exported and the result list shows `BOM JSON` as failed with the reason. Turn it off with the
**BOM JSON next to STEP** checkbox.

A full example is in [sample.bom.json](sample.bom.json).

## Rules for consumers

- `schema` is always `"sr-bom-sidecar"`. Check `schema_version`; it goes up only on a breaking change.
  New keys may be added without a version bump, so ignore keys you do not know.
- All values use the units in `units`: lengths in **mm**, area mm², volume mm³, mass **kg**, angles in
  degrees, whatever the design's display units are (`source.design_units` records those).
- Paths (`step_file`, `assembly_thumbnail`, `components[].thumbnail`) are relative to the folder that
  holds the JSON, with `/` separators.
- Text is UTF-8. Callouts use the symbols Ø (diameter), ⌴ (counterbore), ⌵ (countersink) and ↧ (depth).
- A missing or unknown value is `null` (numbers, objects) or `""` (part number, description, material).

## Top level

| Key | Type | Meaning |
| --- | --- | --- |
| `schema`, `schema_version` | string, int | `"sr-bom-sidecar"`, `1` |
| `generator` | object | `{"tool": "SR Export", "version": "1.1.0"}` |
| `exported_at` | string | Export time, ISO 8601 local time with UTC offset |
| `step_file` | string | STEP file name (same folder) |
| `source` | object | Where the model came from (below) |
| `units` | object | Units used everywhere in the file |
| `scope` | object | `component` exported, `is_root`, and `selected_occurrence` (full path) when one component was picked |
| `totals` | object or null | Physical properties of the whole exported scope (same shape as `components[].physical`) |
| `assembly_thumbnail` | string or null | PNG of the current Fusion view at export time (the view is not changed) |
| `components` | array | BOM rows (below) |
| `holes` | array | One record per hole feature (below) |
| `hole_groups` | array | Identical holes merged for a hole table |
| `warnings` | array of strings | Anything that could not be read, plus `unsaved changes` if the open design differs from its saved version |

### `source`

| Key | Meaning |
| --- | --- |
| `document_name` | Fusion document name as shown, with version (`"Box v15"`) |
| `design_name` | Root component name |
| `version`, `latest_version` | Version number of the open document, and the newest version in the hub |
| `data_file_name`, `data_file_id` | Hub file name and lineage URN |
| `folder`, `project`, `hub` | Hub folder, project and hub names |
| `saved`, `unsaved_changes` | Whether the document has been saved, and whether it has edits since |
| `design_units` | Default length unit of the design (`"mm"`, `"in"`, ...) |

All hub fields are `null` for a design that was never saved.

## `components[]` (BOM rows)

Counted like Autodesk's ExtractBOM sample: every occurrence in `allOccurrences` of the exported scope
adds one to its component's `quantity`, at every nesting level. Rows are in first-seen (browser) order,
and `item` numbers run 1..N in that order. A design with no occurrences (a single part) has one row for
the part itself.

| Key | Type | Meaning |
| --- | --- | --- |
| `item` | int | BOM item number (use for balloons) |
| `id` | string | Fusion component id, stable across exports of the same design |
| `name` | string | Component name (linked components keep Fusion's ` vN` suffix) |
| `part_number`, `description`, `material` | string | Component properties. `material` is the component's material |
| `body_materials` | array | Distinct physical materials of the component's own bodies (can differ from `material`) |
| `quantity` | int | Total count in the exported scope |
| `is_linked`, `linked_source` | bool, object | Linked (external) component, and `{document, version}` of its source |
| `is_assembly` | bool | The component has child occurrences (its `physical` then includes them) |
| `body_count` | int | Bodies owned by the component itself |
| `occurrences` | array | Full occurrence paths (`"Bracket:1+Screw:2"`), for highlighting the part in drawing views |
| `physical` | object or null | One instance: `mass_kg`, `volume_mm3`, `area_mm2`, `density_kg_mm3`, `center_of_mass_mm` [x, y, z] in the component's own coordinates, `accuracy` (`"high"`) |
| `thumbnail` | string or null | Part PNG, only when **Part thumbnails** was ticked |
| `hole_ids` | array | Ids of this component's records in `holes` |

## `holes[]`

One record per unsuppressed Fusion **Hole** feature in each BOM component. Holes made any other way
(extrude cuts, imported geometry, pattern copies) are not listed.

| Key | Type | Meaning |
| --- | --- | --- |
| `id` | string | `"<item>-H<n>"`, e.g. `"1-H2"` |
| `component_id`, `component_name` | string | Owning component |
| `feature_name` | string | Timeline name (`"Hole3"`) |
| `type` | string | `simple`, `counterbore`, `countersink` |
| `tap_type` | string | `simple`, `clearance`, `tapped`, `taper_tapped` |
| `instances` | int | Holes made by this feature (its sketch points); 1 if unknown |
| `diameter_mm` | number | Hole diameter parameter. For tapped holes Fusion drives the size from the thread; use `thread` |
| `depth` | object | `{"kind": "distance", "value_mm": 12}`, or `kind` `through_all` / `to_entity` / `unknown` with `value_mm` null |
| `tip_angle_deg` | number | Drill point angle |
| `counterbore` | object or null | `{diameter_mm, depth_mm}` |
| `countersink` | object or null | `{diameter_mm, angle_deg}` |
| `clearance` | object or null | Fusion clearance-hole info (`standard`, `fastenerType`, `size`, `fitType`) when present |
| `thread` | object or null | Tapped holes only (below) |
| `callout` | string | Ready-made callout, lines split by `\n`, with an `NX` prefix when `instances` > 1 |

### `thread`

From `HoleFeature.tappedHoleInfo` and the hole's thread feature.

| Key | Meaning |
| --- | --- |
| `type`, `designation`, `class`, `size` | Thread type (`"ISO Metric profile"`), designation (`"M4x0.7"`), class (`"6H"`), size |
| `right_handed`, `tapered` | Hand and taper |
| `major_diameter_mm`, `pitch_diameter_mm`, `minor_diameter_mm` | From Fusion |
| `full_length`, `thread_length_mm` | Thread length of the hole's thread feature |
| `tap_drill` | `{diameter_mm, diameter_native, unit, source, table_file, note}` |

`tap_drill.source` is `fusion_thread_table` when the drill was looked up in Fusion's own thread
tables on the PC that exported (`<Fusion install>/Fusion/Server/Fusion/Configuration/ThreadData/*.xml`,
internal thread, same designation and class), `thread_info_taper` for tapered threads (Fusion gives the
drill directly), or `not_found` (then `diameter_mm` is null and `note` says why). `diameter_native` and
`unit` keep the table's own value (inch tables are converted to mm in `diameter_mm`). Set
`SREXPORT_THREAD_DATA` to point at another ThreadData folder.

## `hole_groups[]`

Holes in the same component with the same callout (ignoring the count) are merged for a hole table:
`{component_id, callout, count, hole_ids}`. `callout` has no `NX` prefix; `count` is the total number
of hole instances, so a sheet shows `count` + `X ` + `callout`.

## Using it in the sheet editor

- **BOM table:** one row per `components[]` entry: `item`, `quantity`, `part_number`, `description`,
  `material`. Show `thumbnail` (or `assembly_thumbnail` as a fallback) when a row is clicked, and use
  `occurrences` to highlight the part in the views.
- **Hole callouts:** match a hole in a view to its record by component and feature, then use `callout`,
  or build your own from the structured fields. Tolerances are not in the model and are not in this file;
  they come from the sheet (block tolerance) or the per-annotation tolerance the engineer sets.

## Thumbnails

- `assembly_thumbnail` is saved from the current view as it is and does not change anything.
- Per-part thumbnails are off by default. When **Part thumbnails** is ticked, SR Export isolates the
  first occurrence of each component, fits the view, saves a 128 px PNG to `<name>.thumbs/`, then turns
  isolation off and puts the camera back. That touches view state in the open design, which is why it
  is opt-in. It is skipped with a warning where the design cannot be changed (for example a read-only
  script context).

## Limits

- Only Fusion Hole features are read. Holes from extrude cuts, imported bodies or patterns are missing.
- `instances` counts sketch points of the hole feature; patterned copies are not added.
- Tap drills come from the exporting PC's Fusion thread tables, so a different Fusion build could give a
  different value. Hub-library and custom threads that are not in those tables are `not_found`.
- Mass properties come from `getPhysicalProperties` at high accuracy for one instance of each component.
