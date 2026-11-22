"""Tests for the BOM sidecar: pure helpers plus sidecar_ops against a small fake adsk module."""
import json
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDIN = os.path.join(ROOT, 'SRExport')
sys.path.insert(0, ADDIN)

import sidecar_core as core  # noqa: E402

ISO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ThreadType><Name>ISO Metric profile</Name><CustomName>ISO Metric Profile</CustomName><Unit>mm</Unit>
 <ThreadSize><Size>4.0</Size><Designation><ThreadDesignation>M4x0.7</ThreadDesignation><CTD>M4x0.7</CTD>
  <Pitch>0.7</Pitch>
  <Thread><Gender>external</Gender><Class>6g</Class><MajorDia>3.978</MajorDia><PitchDia>3.523</PitchDia>
   <MinorDia>3.12</MinorDia></Thread>
  <Thread><Gender>internal</Gender><Class>6H</Class><MajorDia>4.0</MajorDia><PitchDia>3.545</PitchDia>
   <MinorDia>3.242</MinorDia><TapDrill>3.3</TapDrill></Thread>
 </Designation></ThreadSize></ThreadType>"""

UN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ThreadType><Name>ANSI Unified Screw Threads</Name><CustomName>ANSI Unified Screw Threads</CustomName>
 <Unit>in</Unit><ThreadSize><Size>0.25</Size><Designation><ThreadDesignation>1/4-20 UNC</ThreadDesignation>
  <TPI>20.0</TPI><Thread><Gender>internal</Gender><Class>2B</Class><MajorDia>0.25</MajorDia>
  <TapDrill>0.201</TapDrill></Thread></Designation></ThreadSize></ThreadType>"""


def _tables(tmp_path):
    d = tmp_path / 'Fusion' / 'Server' / 'Fusion' / 'Configuration' / 'ThreadData'
    d.mkdir(parents=True)
    (d / 'ISOMetricprofile.xml').write_text(ISO_XML, encoding='utf-8')
    (d / 'ANSIUnifiedScrewThreads.xml').write_text(UN_XML, encoding='utf-8')
    (d / 'broken.xml').write_text('<not xml', encoding='utf-8')
    return d


# ---- pure helpers -----------------------------------------------------------------------------------

def test_sidecar_path_overwrites_in_place():
    assert core.sidecar_path(os.path.join('out', 'Part.step')) == os.path.join('out', 'Part.bom.json')
    assert core.thumb_dir(os.path.join('out', 'Part.step')) == os.path.join('out', 'Part.thumbs')


def test_count_components_extractbom_rule_keeps_first_seen_order():
    assert list(core.count_components(['b', 'a', 'b', 'c', 'b']).items()) == [('b', 3), ('a', 1), ('c', 1)]


def test_unit_conversions_from_fusion_internal_units():
    p = core.physical(0.25, 12.5, 30.0, 0.0027, (1.0, -2.0, 0.5))
    assert p['volume_mm3'] == 12500.0 and p['area_mm2'] == 3000.0
    assert p['center_of_mass_mm'] == [10.0, -20.0, 5.0]
    assert abs(p['density_kg_mm3'] - 2.7e-6) < 1e-12
    assert core.deg(3.141592653589793) == 180.0


def test_thread_tables_find_load_and_tap_drill(tmp_path):
    d = _tables(tmp_path)
    exe_dir = str(tmp_path)
    assert core.find_thread_data_dir([exe_dir], env={}) == str(d)
    assert core.find_thread_data_dir([str(tmp_path / 'nope')], env={'SREXPORT_THREAD_DATA': str(d)}) == str(d)
    t = core.load_thread_tables(str(d))
    assert 'iso metric profile' in t and 'ansi unified screw threads' in t
    td = core.lookup_tap_drill(t, 'ISO Metric profile', 'M4x0.7', '6H')
    assert td['diameter_mm'] == 3.3 and td['source'] == 'fusion_thread_table'
    assert td['table_file'] == 'ISOMetricprofile.xml'
    inch = core.lookup_tap_drill(t, 'ANSI Unified Screw Threads', '1/4-20 UNC', '2B')
    assert inch['diameter_mm'] == round(0.201 * 25.4, 4) and inch['diameter_native'] == 0.201
    # class not in table -> any internal class of the same designation
    assert core.lookup_tap_drill(t, 'ISO Metric Profile', 'M4x0.7', '')['diameter_mm'] == 3.3
    assert core.lookup_tap_drill(t, 'Nope', 'M4x0.7', '6H')['source'] == 'not_found'
    assert core.lookup_tap_drill(t, 'ISO Metric profile', 'M99', '6H')['diameter_mm'] is None


def test_hole_callouts():
    simple = {'instances': 4, 'diameter_mm': 5.5, 'depth': {'kind': 'through_all'}}
    assert core.hole_callout(simple) == '4X \u00d85.5 THRU'
    cb = {'instances': 1, 'diameter_mm': 4.5, 'depth': {'kind': 'distance', 'value_mm': 10},
          'counterbore': {'diameter_mm': 8.0, 'depth_mm': 4.4}}
    assert core.hole_callout(cb) == '\u00d84.5 \u21a710\n\u2334\u00d88 \u21a74.4'
    cs = {'diameter_mm': 4.5, 'depth': {'kind': 'through_all'}, 'countersink': {'diameter_mm': 9, 'angle_deg': 90}}
    assert core.hole_callout(cs).endswith('\u2335\u00d89 X 90\u00b0')
    tapped = {'instances': 2, 'diameter_mm': 3.3, 'depth': {'kind': 'distance', 'value_mm': 12},
              'thread': {'designation': 'M4x0.7', 'class': '6H', 'thread_length_mm': 10,
                         'tap_drill': {'diameter_mm': 3.3}}}
    assert core.hole_callout(tapped) == '2X \u00d83.3 \u21a712\nM4x0.7 - 6H \u21a710'


def test_build_document_items_holes_groups_and_validate(tmp_path):
    comps = [{'id': 'c1', 'name': 'Plate', 'part_number': 'P-1', 'description': 'plate', 'material': 'Al',
              'quantity': 1},
             {'id': 'c2', 'name': 'Screw', 'part_number': 'S-1', 'description': '', 'material': '', 'quantity': 14}]
    holes = [{'id': '1-H1', 'component_id': 'c1', 'instances': 2, 'diameter_mm': 5, 'depth': {'kind': 'through_all'}},
             {'id': '1-H2', 'component_id': 'c1', 'instances': 3, 'diameter_mm': 5, 'depth': {'kind': 'through_all'}}]
    doc = core.build_document({'document_name': 'X v3'}, os.path.join('o', 'X.step'), comps, holes,
                              generator_version='t', exported_at='2026-11-22T13:50:00-05:00')
    assert doc['schema'] == 'sr-bom-sidecar' and doc['schema_version'] == 1 and doc['step_file'] == 'X.step'
    assert [c['item'] for c in doc['components']] == [1, 2]
    assert doc['components'][0]['hole_ids'] == ['1-H1', '1-H2'] and doc['components'][1]['hole_ids'] == []
    assert doc['hole_groups'] == [{'component_id': 'c1', 'callout': '\u00d85 THRU', 'count': 5,
                                   'hole_ids': ['1-H1', '1-H2']}]
    assert core.validate(doc) == []
    p = core.write_json(doc, str(tmp_path / 'X.bom.json'))
    assert json.loads(open(p, encoding='utf-8').read()) == doc
    assert not os.path.exists(p + '.tmp')
    bad = dict(doc, components=[dict(comps[0], quantity=0)])
    assert 'bad quantity for Plate' in core.validate(bad)
    assert any('unknown component' in e for e in core.validate(dict(doc, components=[])))


def test_now_iso_has_offset():
    s = core.now_iso()
    assert s[10] == 'T' and (s[-6] in '+-')


# ---- sidecar_ops against a fake adsk --------------------------------------------------------------

class Coll:
    def __init__(self, items):
        self._i = list(items)

    @property
    def count(self):
        return len(self._i)

    def item(self, i):
        return self._i[i]


class Param:
    def __init__(self, v):
        self.value = v


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _cast_factory(cls_name):
    def cast(o):
        return o if getattr(o, '_kind', None) == cls_name else None
    return staticmethod(cast)


def _install_fake_adsk(monkeypatch):
    adsk = types.ModuleType('adsk')
    acore = types.ModuleType('adsk.core')
    afus = types.ModuleType('adsk.fusion')
    app = Obj(activeViewport=Obj(saveAsImageFile=lambda p, w, h: False))
    acore.Application = Obj(get=lambda: app)
    afus.CalculationAccuracy = Obj(HighCalculationAccuracy=3)
    for n in ('DistanceExtentDefinition', 'ThroughAllExtentDefinition', 'ToEntityExtentDefinition'):
        setattr(afus, n, type(n, (), {'cast': _cast_factory(n)}))
    adsk.core, adsk.fusion = acore, afus
    monkeypatch.setitem(sys.modules, 'adsk', adsk)
    monkeypatch.setitem(sys.modules, 'adsk.core', acore)
    monkeypatch.setitem(sys.modules, 'adsk.fusion', afus)
    monkeypatch.delitem(sys.modules, 'sidecar_ops', raising=False)
    import sidecar_ops
    return sidecar_ops


def _pp(mass, vol, com):
    return lambda acc: Obj(mass=mass, volume=vol, area=1.0, density=0.0027,
                           centerOfMass=Obj(x=com[0], y=com[1], z=com[2]))


def _fake_design():
    tapped = Obj(name='Hole1', isSuppressed=False, holeType=0, holeTapType=2,
                 holeDiameter=Param(0.33), extentDefinition=Obj(_kind='DistanceExtentDefinition', distance=Param(1.2)),
                 tipAngle=Param(2.0943951), holePositionDefinition=Obj(sketchPoints=Coll([1, 2, 3, 4])),
                 clearanceHoleInfo=None,
                 tappedHoleInfo=Obj(threadType='ISO Metric profile', threadDesignation='M4x0.7', threadClass='6H',
                                    threadSize='4.0', isRightHanded=True, isTapered=False, majorDiameter=0.4,
                                    pitchDiameter=0.3545, minorDiameter=0.3242),
                 thread=Obj(isFullLength=False, threadLength=Param(1.0)))
    cbore = Obj(name='Hole2', isSuppressed=False, holeType=1, holeTapType=0, holeDiameter=Param(0.45),
                extentDefinition=Obj(_kind='ThroughAllExtentDefinition'), tipAngle=Param(2.0943951),
                holePositionDefinition=Obj(), counterboreDiameter=Param(0.8), counterboreDepth=Param(0.44),
                clearanceHoleInfo=None, tappedHoleInfo=None)
    gone = Obj(name='Hole3', isSuppressed=True)
    plate = Obj(id='plate-id', name='Plate', partNumber='CPDM-1', description='base plate',
                material=Obj(name='Aluminum 6061'), occurrences=Coll([]),
                bRepBodies=Coll([Obj(material=Obj(name='Aluminum 6061')), Obj(material=Obj(name='Steel'))]),
                features=Obj(holeFeatures=Coll([tapped, cbore, gone])), getPhysicalProperties=_pp(0.2, 74.0, (5, 2, 0.3)))
    screw = Obj(id='screw-id', name='SHCS M4x10', partNumber='91290A140', description='', material=None,
                occurrences=Coll([]), bRepBodies=Coll([1]), features=Obj(holeFeatures=Coll([])),
                getPhysicalProperties=_pp(0.002, 0.2, (0, 0, 0.5)))

    def occ(c, path, ref=False):
        return Obj(component=c, name=path.split('+')[-1], fullPathName=path, isReferencedComponent=ref,
                   documentReference=Obj(dataFile=Obj(name='91290A140'), version=2) if ref else None)
    occs = Coll([occ(plate, 'Plate:1'), occ(screw, 'SHCS M4x10:1', True), occ(screw, 'SHCS M4x10:2', True)])
    root = Obj(id='root-id', name='Box', allOccurrences=occs, getPhysicalProperties=_pp(0.204, 74.4, (5, 2, 0.31)))
    df = Obj(name='Box', versionNumber=15, latestVersionNumber=15, id='urn:x',
             parentFolder=Obj(name='enclosures'), parentProject=Obj(name='custom-pdm', parentHub=Obj(name='hub-a')))
    design = Obj(rootComponent=root, unitsManager=Obj(defaultLengthUnits='mm'),
                 parentDocument=Obj(name='Box v15', dataFile=df, isSaved=True, isModified=False))
    return design


def test_ops_build_full_document(monkeypatch, tmp_path):
    ops = _install_fake_adsk(monkeypatch)
    tables = core.load_thread_tables(str(_tables(tmp_path)))
    step = str(tmp_path / 'Box.step')
    doc = ops.build(_fake_design(), step, tables=tables)
    assert core.validate(doc) == []
    src = doc['source']
    assert (src['document_name'], src['version'], src['project'], src['hub']) == ('Box v15', 15, 'custom-pdm', 'hub-a')
    c = {x['name']: x for x in doc['components']}
    assert c['Plate']['quantity'] == 1 and c['SHCS M4x10']['quantity'] == 2
    assert c['SHCS M4x10']['is_linked'] and c['SHCS M4x10']['linked_source'] == {'document': '91290A140', 'version': 2}
    assert c['Plate']['material'] == 'Aluminum 6061' and c['SHCS M4x10']['material'] == ''
    assert c['Plate']['body_materials'] == ['Aluminum 6061', 'Steel'] and c['SHCS M4x10']['body_materials'] == []
    assert c['Plate']['physical']['volume_mm3'] == 74000.0 and c['Plate']['physical']['accuracy'] == 'high'
    assert c['SHCS M4x10']['occurrences'] == ['SHCS M4x10:1', 'SHCS M4x10:2']
    h1, h2 = doc['holes']
    assert len(doc['holes']) == 2  # suppressed hole skipped
    assert h1['tap_type'] == 'tapped' and h1['instances'] == 4 and h1['depth'] == {'kind': 'distance', 'value_mm': 12.0}
    assert h1['thread']['designation'] == 'M4x0.7' and h1['thread']['class'] == '6H'
    assert h1['thread']['tap_drill']['diameter_mm'] == 3.3 and h1['thread']['thread_length_mm'] == 10.0
    assert h1['callout'] == '4X \u00d83.3 \u21a712\nM4x0.7 - 6H \u21a710'
    assert round(h1['tip_angle_deg']) == 120
    assert h2['type'] == 'counterbore' and h2['counterbore'] == {'diameter_mm': 8.0, 'depth_mm': 4.4}
    assert h2['depth']['kind'] == 'through_all' and h2['thread'] is None
    assert c['Plate']['hole_ids'] == [h1['id'], h2['id']]
    assert doc['totals']['mass_kg'] == 0.204 and doc['scope']['is_root'] is True
    assert doc['assembly_thumbnail'] is None  # fake viewport returns False


def test_ops_single_part_and_warnings(monkeypatch, tmp_path):
    ops = _install_fake_adsk(monkeypatch)
    d = _fake_design()
    part = d.rootComponent
    part.allOccurrences = Coll([])
    part.partNumber, part.description, part.material = 'P', 'd', None
    part.occurrences, part.bRepBodies = Coll([]), Coll([1])
    part.features = Obj(holeFeatures=Coll([]))
    d.parentDocument.isModified = True
    p = ops.write_sidecar(d, str(tmp_path / 'Box.step'), assembly_thumb=False)
    doc = json.load(open(p, encoding='utf-8'))
    assert p.endswith('Box.bom.json')
    assert [(x['name'], x['quantity']) for x in doc['components']] == [('Box', 1)]
    assert any('unsaved changes' in w for w in doc['warnings'])


def test_ops_thumbnails_fail_cleanly_in_read_only_context(monkeypatch, tmp_path):
    ops = _install_fake_adsk(monkeypatch)
    d = _fake_design()

    class RO:
        def __setattr__(self, k, v):
            raise RuntimeError('Cannot modify the design from a read-only context')
    for i in range(d.rootComponent.allOccurrences.count):
        o = d.rootComponent.allOccurrences.item(i)
        o.__class__ = type('ROOcc', (Obj,), {'__setattr__': RO.__setattr__})
    import adsk.core as ac
    ac.Application.get().activeViewport.camera = 'cam'
    ac.Application.get().activeViewport.fit = lambda: None
    ac.Application.get().activeViewport.refresh = lambda: None
    doc = ops.build(d, str(tmp_path / 'Box.step'), thumbnails=True, tables={})
    assert all(c['thumbnail'] is None for c in doc['components'])
    assert core.validate(doc) == []
