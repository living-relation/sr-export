"""Pure helpers for the BOM + model-data sidecar JSON written next to every STEP export.

No adsk import, so everything here is unit-tested in tests/test_sidecar.py. The Fusion side lives in
sidecar_ops.py. The schema is documented in docs/sidecar-schema.md; bump SCHEMA_VERSION on any
breaking change.
"""
import datetime
import json
import os
import re
import xml.etree.ElementTree as ET

SCHEMA = 'sr-bom-sidecar'
SCHEMA_VERSION = 1
SIDECAR_SUFFIX = '.bom.json'
THUMB_SUFFIX = '.thumbs'
UNITS = {'length': 'mm', 'area': 'mm2', 'volume': 'mm3', 'mass': 'kg', 'density': 'kg/mm3', 'angle': 'deg'}

# Fusion API internal units are cm, cm2, cm3, kg, kg/cm3 and radians.
CM_TO_MM = 10.0

HOLE_TYPES = {0: 'simple', 1: 'counterbore', 2: 'countersink'}          # adsk.fusion.HoleTypes
TAP_TYPES = {0: 'simple', 1: 'clearance', 2: 'tapped', 3: 'taper_tapped'}  # adsk.fusion.HoleTapTypes


def sidecar_path(step_path):
    """'C:/out/Part.step' -> 'C:/out/Part.bom.json' (same folder, same base name, so it overwrites in place)."""
    return os.path.splitext(step_path)[0] + SIDECAR_SUFFIX


def thumb_dir(step_path):
    """Folder for per-component thumbnails: 'C:/out/Part.thumbs'."""
    return os.path.splitext(step_path)[0] + THUMB_SUFFIX


def safe_file_part(text):
    """File-safe slug for a component id or name."""
    s = re.sub(r'[^A-Za-z0-9_-]+', '_', text or '').strip('_')
    return s or 'item'


def now_iso(now=None):
    """Local time with UTC offset, seconds precision: '2026-11-22T13:50:00-05:00'."""
    now = now or datetime.datetime.now().astimezone()
    return now.replace(microsecond=0).isoformat()


def mm(v_cm, nd=4):
    return None if v_cm is None else round(float(v_cm) * CM_TO_MM, nd)


def mm2(v_cm2, nd=3):
    return None if v_cm2 is None else round(float(v_cm2) * 100.0, nd)


def mm3(v_cm3, nd=3):
    return None if v_cm3 is None else round(float(v_cm3) * 1000.0, nd)


def deg(v_rad, nd=3):
    import math
    return None if v_rad is None else round(math.degrees(float(v_rad)), nd)


def physical(mass_kg, volume_cm3, area_cm2, density_kg_cm3, com_cm, accuracy='high'):
    """Physical properties block in sidecar units. com_cm is an (x, y, z) tuple in cm or None."""
    return {
        'mass_kg': None if mass_kg is None else round(float(mass_kg), 9),
        'volume_mm3': mm3(volume_cm3),
        'area_mm2': mm2(area_cm2),
        'density_kg_mm3': None if density_kg_cm3 is None else float(density_kg_cm3) / 1000.0,
        'center_of_mass_mm': None if com_cm is None else [mm(c) for c in com_cm],
        'accuracy': accuracy,
    }


def count_components(occurrence_component_ids):
    """Autodesk ExtractBOM rule: one count per occurrence in rootComponent.allOccurrences.
    Returns an ordered {component id: quantity} in first-seen (browser) order."""
    out = {}
    for cid in occurrence_component_ids:
        out[cid] = out.get(cid, 0) + 1
    return out


# ---- thread tables ---------------------------------------------------------------------------------

def _num(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_thread_xml(text, file_name=''):
    """Parse one Fusion ThreadData XML file (e.g. ISOMetricprofile.xml).

    Returns {'name', 'custom_name', 'unit', 'file', 'threads': {(designation, class, gender): {...}}}."""
    root = ET.fromstring(text)
    unit = (root.findtext('Unit') or 'mm').strip()
    table = {
        'name': (root.findtext('Name') or '').strip(),
        'custom_name': (root.findtext('CustomName') or '').strip(),
        'unit': unit,
        'file': file_name,
        'threads': {},
    }
    for size in root.findall('ThreadSize'):
        size_txt = (size.findtext('Size') or '').strip()
        for des in size.findall('Designation'):
            name = (des.findtext('ThreadDesignation') or '').strip()
            ctd = (des.findtext('CTD') or '').strip()
            pitch = _num(des.findtext('Pitch'))
            tpi = _num(des.findtext('TPI'))
            for th in des.findall('Thread'):
                key = (name, (th.findtext('Class') or '').strip(), (th.findtext('Gender') or '').strip().lower())
                table['threads'][key] = {
                    'size': size_txt,
                    'designation': name,
                    'ctd': ctd,
                    'pitch': pitch,
                    'tpi': tpi,
                    'major_dia': _num(th.findtext('MajorDia')),
                    'pitch_dia': _num(th.findtext('PitchDia')),
                    'minor_dia': _num(th.findtext('MinorDia')),
                    'tap_drill': _num(th.findtext('TapDrill')),
                }
    return table


def load_thread_tables(folder):
    """All *.xml thread tables in a Fusion ThreadData folder, keyed by lower-case type name and custom name."""
    tables = {}
    if not folder or not os.path.isdir(folder):
        return tables
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith('.xml'):
            continue
        try:
            with open(os.path.join(folder, f), encoding='utf-8') as fh:
                t = parse_thread_xml(fh.read(), f)
        except (OSError, ET.ParseError, ValueError):
            continue
        for k in (t['name'], t['custom_name']):
            if k:
                tables.setdefault(k.lower(), t)
    return tables


def find_thread_data_dir(start_dirs, env=None):
    """Fusion keeps its thread tables in <install>/Fusion/Server/Fusion/Configuration/ThreadData.
    SREXPORT_THREAD_DATA overrides. start_dirs: folders to search upward from (e.g. the Fusion exe folder)."""
    env = os.environ if env is None else env
    if env.get('SREXPORT_THREAD_DATA') and os.path.isdir(env['SREXPORT_THREAD_DATA']):
        return env['SREXPORT_THREAD_DATA']
    rel = os.path.join('Fusion', 'Server', 'Fusion', 'Configuration', 'ThreadData')
    for start in start_dirs:
        d = start
        for _ in range(6):
            if not d:
                break
            cand = os.path.join(d, rel)
            if os.path.isdir(cand):
                return cand
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None


def _to_mm(v, unit):
    if v is None:
        return None
    return round(v * 25.4, 4) if unit.lower().startswith('in') else round(v, 4)


def lookup_tap_drill(tables, thread_type, designation, thread_class):
    """Tap drill for an internal thread from Fusion's tables. Returns a tap_drill dict (always a dict)."""
    t = tables.get((thread_type or '').lower())
    if not t:
        return {'diameter_mm': None, 'diameter_native': None, 'unit': None, 'source': 'not_found',
                'table_file': None, 'note': 'thread type not in the thread tables'}
    row = t['threads'].get((designation, thread_class, 'internal'))
    if row is None:  # class missing (or blank): take any internal class of this designation that has a drill
        for (d, _c, g), r in t['threads'].items():
            if d == designation and g == 'internal' and r['tap_drill'] is not None:
                row = r
                break
    if row is None or row['tap_drill'] is None:
        return {'diameter_mm': None, 'diameter_native': None, 'unit': t['unit'], 'source': 'not_found',
                'table_file': t['file'], 'note': 'designation or class not in the table'}
    return {'diameter_mm': _to_mm(row['tap_drill'], t['unit']), 'diameter_native': row['tap_drill'],
            'unit': t['unit'], 'source': 'fusion_thread_table', 'table_file': t['file'], 'note': ''}


# ---- holes and callouts ----------------------------------------------------------------------------

def _fmt(v, nd=2):
    s = ('%.' + str(nd) + 'f') % v
    return s.rstrip('0').rstrip('.') if '.' in s else s


def hole_callout(h):
    """One-line ASME-style hole callout in mm from a sidecar hole record. The sheet editor may format its
    own; this is a ready default. Symbols: Ø diameter, ⌴ counterbore, ⌵ countersink, ↧ depth."""
    n = h.get('instances') or 1
    parts = []
    pre = ('%dX ' % n) if n > 1 else ''
    depth = h.get('depth') or {}
    thr = h.get('thread')
    if thr:
        td = (thr.get('tap_drill') or {}).get('diameter_mm')
        if td:
            parts.append(pre + '\u00d8' + _fmt(td) + (' \u21a7' + _fmt(depth['value_mm']) if depth.get('value_mm') else
                                                       ' THRU' if depth.get('kind') == 'through_all' else ''))
            pre = ''
        tl = thr.get('thread_length_mm')
        cls = (' - ' + thr['class']) if thr.get('class') else ''
        txt = pre + (thr.get('designation') or '') + cls
        if thr.get('full_length') and depth.get('kind') == 'through_all':
            txt += ' THRU'
        elif tl:
            txt += ' \u21a7' + _fmt(tl)
        parts.append(txt)
    else:
        txt = pre + '\u00d8' + _fmt(h['diameter_mm']) if h.get('diameter_mm') is not None else pre + '\u00d8?'
        if depth.get('kind') == 'through_all':
            txt += ' THRU'
        elif depth.get('value_mm'):
            txt += ' \u21a7' + _fmt(depth['value_mm'])
        parts.append(txt)
    cb = h.get('counterbore')
    if cb and cb.get('diameter_mm'):
        parts.append('\u2334\u00d8' + _fmt(cb['diameter_mm']) + (' \u21a7' + _fmt(cb['depth_mm']) if cb.get('depth_mm') else ''))
    cs = h.get('countersink')
    if cs and cs.get('diameter_mm'):
        parts.append('\u2335\u00d8' + _fmt(cs['diameter_mm']) + (' X ' + _fmt(cs['angle_deg'], 1) + '\u00b0' if cs.get('angle_deg') else ''))
    return '\n'.join(parts)


def group_holes(holes):
    """Group identical holes for a hole table: [{'component_id', 'callout', 'count', 'hole_ids'}].
    The group callout has no 'NX' prefix; count is the total number of hole instances in the group."""
    groups = {}
    for h in holes:
        key = (h['component_id'], hole_callout(dict(h, instances=1)))
        g = groups.setdefault(key, {'component_id': h['component_id'], 'callout': key[1], 'count': 0, 'hole_ids': []})
        g['count'] += h.get('instances') or 1
        g['hole_ids'].append(h['id'])
    return list(groups.values())


# ---- document ---------------------------------------------------------------------------------------

def build_document(source, step_file, components, holes, totals=None, scope=None, warnings=None,
                   assembly_thumbnail=None, generator_version='', exported_at=None):
    """Assemble the sidecar dict. components and holes are lists of records (see docs/sidecar-schema.md).
    Item numbers are assigned 1..N in the given order; each component lists its hole ids."""
    by_comp = {}
    for h in holes:
        h.setdefault('callout', hole_callout(h))
        by_comp.setdefault(h['component_id'], []).append(h['id'])
    comps = []
    for i, c in enumerate(components, 1):
        c = dict(c)
        c['item'] = i
        c['hole_ids'] = by_comp.get(c['id'], [])
        comps.append(c)
    return {
        'schema': SCHEMA,
        'schema_version': SCHEMA_VERSION,
        'generator': {'tool': 'SR Export', 'version': generator_version},
        'exported_at': exported_at or now_iso(),
        'step_file': os.path.basename(step_file) if step_file else None,
        'source': source,
        'units': dict(UNITS),
        'scope': scope or {},
        'totals': totals,
        'assembly_thumbnail': assembly_thumbnail,
        'components': comps,
        'holes': holes,
        'hole_groups': group_holes(holes),
        'warnings': list(warnings or []),
    }


def validate(doc):
    """Light structural check used by tests and before writing. Returns a list of problems (empty = ok)."""
    errs = []
    for k in ('schema', 'schema_version', 'exported_at', 'source', 'units', 'components', 'holes'):
        if k not in doc:
            errs.append('missing ' + k)
    ids = set()
    for c in doc.get('components', []):
        for k in ('item', 'id', 'name', 'part_number', 'description', 'material', 'quantity'):
            if k not in c:
                errs.append('component missing ' + k)
        if not isinstance(c.get('quantity'), int) or c.get('quantity', 0) < 1:
            errs.append('bad quantity for %s' % c.get('name'))
        ids.add(c.get('id'))
    for h in doc.get('holes', []):
        if h.get('component_id') not in ids:
            errs.append('hole %s points at unknown component' % h.get('id'))
    return errs


def write_json(doc, path):
    """Atomic write (tmp + replace), UTF-8, stable key order for clean diffs."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write('\n')
    os.replace(tmp, path)
    return path
