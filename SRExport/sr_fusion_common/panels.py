"""Toolbar panel placement for SR Fusion add-ins.

Config loading is pure Python and unit-tested. Functions that take `ui` talk to
Fusion. Default placement is several Design-workspace panels plus a custom
SR Tools panel, not a single Manage or Add-Ins tab. Edit panel_ids in
panels.json under the add-in's settings folder to change it.
"""
from . import settings

# Built-in Design workspace panels. SolidScriptsAddinsPanel is Utilities/Add-Ins
# (in some Fusion builds it sits under the Manage tab).
DEFAULT_PANEL_IDS = [
    'SolidScriptsAddinsPanel',
    'SolidMakePanel',
    'InsertPanel',
    'SRToolsPanel',
]

SR_TOOLS_PANEL_ID = 'SRToolsPanel'
SR_TOOLS_PANEL_NAME = 'SR Tools'
SR_TOOLS_TAB_ID = 'SRToolsTab'
SR_TOOLS_TAB_NAME = 'SR Tools'
DESIGN_WORKSPACE_ID = 'FusionSolidEnvironment'
SETTINGS_NAME = 'panels'
DEFAULTS = {'panel_ids': list(DEFAULT_PANEL_IDS)}

# Pin to the toolbar only on these panels. Other configured panels still get a
# button inside the panel, but we do not force the pin on every start.
DEFAULT_PROMOTE_ON = (SR_TOOLS_PANEL_ID, 'SolidScriptsAddinsPanel')


def normalize_panel_ids(raw, defaults=None):
    """Return a de-duplicated list of panel id strings, or defaults if empty/invalid."""
    defaults = list(defaults or DEFAULT_PANEL_IDS)
    if not isinstance(raw, list):
        return defaults
    ids = []
    seen = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        pid = item.strip()
        if not pid or pid in seen:
            continue
        ids.append(pid)
        seen.add(pid)
    return ids or defaults


def load_panel_ids(folder=None):
    data = settings.load(SETTINGS_NAME, DEFAULTS, folder)
    return normalize_panel_ids(data.get('panel_ids'))


def save_panel_ids(panel_ids, folder=None):
    ids = normalize_panel_ids(panel_ids)
    return settings.save(SETTINGS_NAME, {'panel_ids': ids}, folder)


def ensure_sr_tools_panel(ui):
    """Create the SR Tools tab and panel in the Design workspace if they are missing."""
    ws = ui.workspaces.itemById(DESIGN_WORKSPACE_ID)
    if not ws:
        return None
    tab = ws.toolbarTabs.itemById(SR_TOOLS_TAB_ID)
    if not tab:
        tab = ws.toolbarTabs.add(SR_TOOLS_TAB_ID, SR_TOOLS_TAB_NAME)
    panel = tab.toolbarPanels.itemById(SR_TOOLS_PANEL_ID)
    if not panel:
        panel = tab.toolbarPanels.add(SR_TOOLS_PANEL_ID, SR_TOOLS_PANEL_NAME)
    return panel


def add_command(ui, cmd_def, cmd_id, panel_ids=None, promote_on=None):
    """Add cmd_def to each configured panel. Missing built-in panels are skipped.

    The SR Tools panel is created when it is in the list. Returns the panel ids
    that actually received a control.
    """
    panel_ids = list(panel_ids if panel_ids is not None else load_panel_ids())
    promote_on = set(promote_on if promote_on is not None else DEFAULT_PROMOTE_ON)
    placed = []
    for pid in panel_ids:
        panel = ui.allToolbarPanels.itemById(pid)
        if panel is None and pid == SR_TOOLS_PANEL_ID:
            panel = ensure_sr_tools_panel(ui)
        if panel is None:
            continue
        old = panel.controls.itemById(cmd_id)
        while old:
            old.deleteMe()
            old = panel.controls.itemById(cmd_id)
        ctl = panel.controls.addCommand(cmd_def)
        # Default pin only, set once on the new control; never isPromoted, so Fusion
        # keeps the user's own pin/unpin choice across restarts.
        ctl.isPromotedByDefault = pid in promote_on
        placed.append(pid)
    return placed


def remove_command(ui, cmd_id):
    """Delete every toolbar control for cmd_id, not just the currently configured list.

    Settings may have changed since start, so we walk all panels. If the SR Tools
    panel (and its tab) are empty afterwards, they are removed too.
    """
    all_panels = ui.allToolbarPanels
    for i in range(all_panels.count):
        panel = all_panels.item(i)
        if not panel:
            continue
        ctl = panel.controls.itemById(cmd_id)
        while ctl:
            ctl.deleteMe()
            ctl = panel.controls.itemById(cmd_id)
    _remove_empty_sr_tools(ui)


def _remove_empty_sr_tools(ui):
    panel = ui.allToolbarPanels.itemById(SR_TOOLS_PANEL_ID)
    if panel and panel.controls.count == 0:
        try:
            panel.deleteMe()
        except Exception:
            return
    ws = ui.workspaces.itemById(DESIGN_WORKSPACE_ID)
    if not ws:
        return
    tab = ws.toolbarTabs.itemById(SR_TOOLS_TAB_ID)
    if not tab:
        return
    if tab.toolbarPanels.count == 0:
        try:
            tab.deleteMe()
        except Exception:
            pass
