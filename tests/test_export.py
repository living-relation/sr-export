"""Tests for the pure (no adsk) parts of the SR Export add-in."""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDIN = os.path.join(ROOT, 'SRExport')
sys.path.insert(0, ADDIN)

import export_core  # noqa: E402
from sr_fusion_common import settings  # noqa: E402
from sr_fusion_common.names import safe_name  # noqa: E402


def test_safe_name_strips_version_and_bad_chars():
    assert safe_name('Filament Cabinet v12') == 'Filament Cabinet'
    assert safe_name('a/b:c*?') == 'a_b_c__'
    assert safe_name('  ') == 'export'


def test_target_paths_order_and_overwrite_names(tmp_path):
    p = export_core.target_paths(str(tmp_path), 'Part v3', ['dxf', 'step', 'stl'])
    assert list(p) == ['step', 'stl', 'dxf']
    assert p['step'].endswith('Part.step')
    assert export_core.target_paths(str(tmp_path), 'Part v4', ['step']) == {'step': p['step']}


def test_summarize_marks_failures():
    txt = export_core.summarize({'iges': (False, 'blocked'), 'step': (True, 'x.step')})
    assert txt.splitlines() == ['OK      STEP: x.step', 'FAILED  IGES: blocked']


def test_settings_roundtrip_ignores_unknown_and_bad(tmp_path):
    settings.save('export', {'folder': '/tmp/x', 'junk': 1}, str(tmp_path))
    got = settings.load('export', export_core.DEFAULTS, str(tmp_path))
    assert got['folder'] == '/tmp/x' and 'junk' not in got
    (tmp_path / 'bad.json').write_text('{oops')
    assert settings.load('bad', {'a': 1}, str(tmp_path)) == {'a': 1}


def test_settings_dir_uses_srexport():
    assert settings.APP_FOLDER == 'SRExport'


def test_manifest_valid():
    with open(os.path.join(ADDIN, 'SRExport.manifest'), encoding='utf-8') as f:
        m = json.load(f)
    assert m['type'] == 'addin' and m['autodeskProduct'] == 'Fusion'
    assert m['author'] == 'Spark Robotic'
    assert 'SR Export' in m['description']['']


def _png_size(path):
    with open(path, 'rb') as f:
        assert f.read(8) == b'\x89PNG\r\n\x1a\n'
        length, typ = struct.unpack('>I4s', f.read(8))
        assert typ == b'IHDR'
        w, h = struct.unpack('>II', f.read(8))
        return w, h


def test_icons_present():
    d = os.path.join(ADDIN, 'resources', 'icon')
    for name, n in (('16x16', 16), ('32x32', 32)):
        assert _png_size(os.path.join(d, name + '.png')) == (n, n)
    src = open(os.path.join(ADDIN, 'SRExport.py'), encoding='utf-8').read()
    assert "'resources', 'icon'" in src
    assert 'SR Export' in src and 'HB Export' not in src
    assert "CMD_ID = 'srExportCmd'" in src


def test_pin_not_forced_each_start():
    texts = []
    for dirpath, _, files in os.walk(ADDIN):
        for name in files:
            if name.endswith('.py'):
                texts.append(open(os.path.join(dirpath, name), encoding='utf-8').read())
    blob = chr(10).join(texts)
    assert 'isPromotedByDefault' in blob
    assert 'isPromoted =' not in blob.replace('isPromotedByDefault', '')
