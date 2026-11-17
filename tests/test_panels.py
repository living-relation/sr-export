"""Unit tests for configurable toolbar panel placement (no Fusion)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDIN = os.path.join(ROOT, os.environ.get('SR_ADDIN_FOLDER', 'SRExport'))
sys.path.insert(0, ADDIN)

from sr_fusion_common import panels  # noqa: E402
from sr_fusion_common import settings  # noqa: E402


def test_defaults_cover_several_panels_including_sr_tools():
    ids = panels.DEFAULT_PANEL_IDS
    assert 'SolidScriptsAddinsPanel' in ids
    assert 'SolidMakePanel' in ids
    assert 'InsertPanel' in ids
    assert panels.SR_TOOLS_PANEL_ID in ids
    assert len(ids) >= 3
    assert ids.count(panels.SR_TOOLS_PANEL_ID) == 1


def test_normalize_rejects_empty_and_junk():
    assert panels.normalize_panel_ids(None) == list(panels.DEFAULT_PANEL_IDS)
    assert panels.normalize_panel_ids('InsertPanel') == list(panels.DEFAULT_PANEL_IDS)
    assert panels.normalize_panel_ids([]) == list(panels.DEFAULT_PANEL_IDS)
    assert panels.normalize_panel_ids([12, '', '  ', None]) == list(panels.DEFAULT_PANEL_IDS)
    assert panels.normalize_panel_ids(['InsertPanel', 'InsertPanel', ' SolidMakePanel ']) == [
        'InsertPanel', 'SolidMakePanel'
    ]


def test_load_and_save_panel_ids_roundtrip(tmp_path):
    path = panels.save_panel_ids(['InsertPanel', 'SRToolsPanel'], str(tmp_path))
    assert os.path.basename(path) == 'panels.json'
    assert panels.load_panel_ids(str(tmp_path)) == ['InsertPanel', 'SRToolsPanel']
    settings.save('export', {'folder': '/tmp/x'}, str(tmp_path))
    assert panels.load_panel_ids(str(tmp_path)) == ['InsertPanel', 'SRToolsPanel']


def test_product_code_never_forces_pin():
    texts = []
    for dirpath, _, files in os.walk(ADDIN):
        for name in files:
            if name.endswith('.py'):
                texts.append(open(os.path.join(dirpath, name), encoding='utf-8').read())
    blob = '\n'.join(texts)
    assert 'isPromotedByDefault' in blob
    assert 'isPromoted =' not in blob.replace('isPromotedByDefault', '')
