"""Fusion side of the BOM + model-data sidecar (see sidecar_core.py and docs/sidecar-schema.md).

Everything here only reads the design, except the optional per-component thumbnails, which briefly
isolate one occurrence at a time and then put isolation and the camera back. That option is off by
default because it touches view state; it also fails cleanly (a warning, no thumbnails) in a
read-only script context.
"""
import os
import sys

import adsk.core
import adsk.fusion

try:
    from . import sidecar_core as core
except ImportError:  # loaded as a plain module (tests, scripts)
    import sidecar_core as core

VERSION = '1.1.0'


def _val(p):
    """ModelParameter / ValueInput / plain number -> float (internal units) or None."""
    if p is None:
        return None
    v = getattr(p, 'value', p)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


# ---- source document --------------------------------------------------------------------------------

def source_info(design):
    doc = _safe(lambda: design.parentDocument)
    df = _safe(lambda: doc.dataFile) if doc else None
    proj = _safe(lambda: df.parentProject) if df else None
    return {
        'document_name': _safe(lambda: doc.name, ''),
        'design_name': _safe(lambda: design.rootComponent.name, ''),
        'version': _safe(lambda: df.versionNumber) if df else None,
        'latest_version': _safe(lambda: df.latestVersionNumber) if df else None,
        'data_file_name': _safe(lambda: df.name) if df else None,
        'data_file_id': _safe(lambda: df.id) if df else None,
        'folder': _safe(lambda: df.parentFolder.name) if df else None,
        'project': _safe(lambda: proj.name) if proj else None,
        'hub': _safe(lambda: proj.parentHub.name) if proj else None,
        'saved': bool(_safe(lambda: doc.isSaved, False)) if doc else False,
        'unsaved_changes': bool(_safe(lambda: doc.isModified, False)) if doc else False,
        'design_units': _safe(lambda: design.unitsManager.defaultLengthUnits),
    }


# ---- components -------------------------------------------------------------------------------------

def physical_of(comp, warnings):
    acc = adsk.fusion.CalculationAccuracy.HighCalculationAccuracy
    try:
        pp = comp.getPhysicalProperties(acc)
        com = pp.centerOfMass
        return core.physical(pp.mass, pp.volume, pp.area, pp.density,
                             (com.x, com.y, com.z) if com else None, 'high')
    except Exception as e:
        warnings.append('physical properties failed for %s: %s' % (comp.name, str(e).splitlines()[0] if str(e) else e))
        return None


def _linked_source(occ):
    ref = _safe(lambda: occ.documentReference)
    if not ref:
        return None
    df = _safe(lambda: ref.dataFile)
    return {'document': _safe(lambda: df.name) if df else None, 'version': _safe(lambda: ref.version)}


def collect_components(scope_comp, warnings):
    """[(component, record)] counted from scope_comp.allOccurrences (ExtractBOM rule). A design with no
    occurrences (a single part) gets one row for the scope component itself."""
    occs = scope_comp.allOccurrences
    order, comps, recs = [], {}, {}
    for i in range(occs.count):
        occ = occs.item(i)
        c = occ.component
        order.append(c.id)
        if c.id not in comps:
            comps[c.id] = c
            recs[c.id] = {'is_linked': bool(_safe(lambda: occ.isReferencedComponent, False)),
                          'linked_source': _linked_source(occ) if _safe(lambda: occ.isReferencedComponent, False) else None,
                          'occurrences': []}
        recs[c.id]['occurrences'].append(_safe(lambda: occ.fullPathName, occ.name))
    if not order:
        comps[scope_comp.id] = scope_comp
        recs[scope_comp.id] = {'is_linked': False, 'linked_source': None, 'occurrences': []}
        order = [scope_comp.id]
    out = []
    for cid, qty in core.count_components(order).items():
        c = comps[cid]
        r = recs[cid]
        bodies = _safe(lambda: c.bRepBodies.count, 0)
        body_mats = []
        for bi in range(bodies or 0):
            name = _safe(lambda: c.bRepBodies.item(bi).material.name)
            if name and name not in body_mats:
                body_mats.append(name)
        out.append((c, {
            'id': cid,
            'name': c.name,
            'part_number': _safe(lambda: c.partNumber, '') or '',
            'description': _safe(lambda: c.description, '') or '',
            'material': _safe(lambda: c.material.name, '') if _safe(lambda: c.material) else '',
            'quantity': qty,
            'is_linked': r['is_linked'],
            'linked_source': r['linked_source'],
            'is_assembly': _safe(lambda: c.occurrences.count, 0) > 0,
            'body_count': bodies,
            'body_materials': body_mats,
            'occurrences': r['occurrences'],
            'physical': physical_of(c, warnings),
            'thumbnail': None,
        }))
    return out


# ---- holes ------------------------------------------------------------------------------------------

def _depth(h):
    ext = _safe(lambda: h.extentDefinition)
    if ext is None:
        return {'kind': 'unknown', 'value_mm': None}
    d = adsk.fusion.DistanceExtentDefinition.cast(ext)
    if d:
        return {'kind': 'distance', 'value_mm': core.mm(_val(d.distance))}
    if adsk.fusion.ThroughAllExtentDefinition.cast(ext):
        return {'kind': 'through_all', 'value_mm': None}
    if adsk.fusion.ToEntityExtentDefinition.cast(ext):
        return {'kind': 'to_entity', 'value_mm': None}
    return {'kind': 'unknown', 'value_mm': None}


def _instances(h):
    pd = _safe(lambda: h.holePositionDefinition)
    pts = _safe(lambda: pd.sketchPoints) if pd else None
    n = _safe(lambda: pts.count) if pts is not None else None
    return int(n) if n else 1


def thread_record(info, thread_feature, tables):
    rec = {
        'type': _safe(lambda: info.threadType, ''),
        'designation': _safe(lambda: info.threadDesignation, ''),
        'class': _safe(lambda: info.threadClass, ''),
        'size': _safe(lambda: info.threadSize, ''),
        'right_handed': _safe(lambda: info.isRightHanded),
        'tapered': bool(_safe(lambda: info.isTapered, False)),
        'major_diameter_mm': core.mm(_safe(lambda: info.majorDiameter)),
        'pitch_diameter_mm': core.mm(_safe(lambda: info.pitchDiameter)),
        'minor_diameter_mm': core.mm(_safe(lambda: info.minorDiameter)),
        'full_length': _safe(lambda: thread_feature.isFullLength) if thread_feature else None,
        'thread_length_mm': core.mm(_val(_safe(lambda: thread_feature.threadLength))) if thread_feature else None,
    }
    if rec['tapered']:
        td = _safe(lambda: info.taperTapDrillDiameter)
        rec['tap_drill'] = {'diameter_mm': core.mm(td), 'diameter_native': td, 'unit': 'cm',
                            'source': 'thread_info_taper' if td else 'not_found', 'table_file': None, 'note': ''}
    else:
        rec['tap_drill'] = core.lookup_tap_drill(tables, rec['type'], rec['designation'], rec['class'])
    return rec


def _clearance(h):
    info = _safe(lambda: h.clearanceHoleInfo)
    if not info:
        return None
    out = {}
    for k in ('standard', 'fastenerType', 'size', 'fitType'):
        v = _safe(lambda: getattr(info, k))
        if v is not None:
            out[k] = v
    return out or None


def hole_record(h, comp_rec, n, tables):
    ht = core.HOLE_TYPES.get(_safe(lambda: int(h.holeType), -1), 'unknown')
    tt = core.TAP_TYPES.get(_safe(lambda: int(h.holeTapType), 0), 'simple')
    rec = {
        'id': '%s-H%d' % (comp_rec['item_hint'], n),
        'component_id': comp_rec['id'],
        'component_name': comp_rec['name'],
        'feature_name': _safe(lambda: h.name, ''),
        'type': ht,
        'tap_type': tt,
        'instances': _instances(h),
        'diameter_mm': core.mm(_val(_safe(lambda: h.holeDiameter))),
        'depth': _depth(h),
        'tip_angle_deg': core.deg(_val(_safe(lambda: h.tipAngle))),
        'counterbore': None,
        'countersink': None,
        'clearance': _clearance(h),
        'thread': None,
    }
    if ht == 'counterbore':
        rec['counterbore'] = {'diameter_mm': core.mm(_val(_safe(lambda: h.counterboreDiameter))),
                              'depth_mm': core.mm(_val(_safe(lambda: h.counterboreDepth)))}
    if ht == 'countersink':
        rec['countersink'] = {'diameter_mm': core.mm(_val(_safe(lambda: h.countersinkDiameter))),
                              'angle_deg': core.deg(_val(_safe(lambda: h.countersinkAngle)))}
    info = _safe(lambda: h.tappedHoleInfo)
    if info:
        rec['thread'] = thread_record(info, _safe(lambda: h.thread), tables)
    return rec


def collect_holes(comp_pairs, tables, warnings):
    holes = []
    for idx, (c, rec) in enumerate(comp_pairs, 1):
        hf = _safe(lambda: c.features.holeFeatures)
        if hf is None:
            continue
        n = 0
        rec = dict(rec, item_hint=idx)
        for i in range(hf.count):
            h = hf.item(i)
            if _safe(lambda: h.isSuppressed, False):
                continue
            n += 1
            try:
                holes.append(hole_record(h, rec, n, tables))
            except Exception as e:
                warnings.append('hole %s in %s skipped: %s' % (_safe(lambda: h.name, '?'), c.name, str(e).splitlines()[0]))
    return holes


# ---- thumbnails -------------------------------------------------------------------------------------

def assembly_thumbnail(app, step_path, size=256):
    """Current view, unchanged, saved as <base>.thumbs/_assembly.png. Returns the relative path or None."""
    try:
        d = core.thumb_dir(step_path)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, '_assembly.png')
        if app.activeViewport.saveAsImageFile(p, size, size) and os.path.isfile(p):
            return os.path.relpath(p, os.path.dirname(step_path)).replace('\\', '/')
    except Exception:
        pass
    return None


def component_thumbnails(app, scope_comp, comp_pairs, step_path, warnings, size=128):
    """Optional: isolate the first occurrence of each component, fit, save, then restore isolation and the
    camera. Fills record['thumbnail'] with a path relative to the STEP folder."""
    vp = app.activeViewport
    cam = vp.camera
    d = core.thumb_dir(step_path)
    os.makedirs(d, exist_ok=True)
    first = {}
    occs = scope_comp.allOccurrences
    for i in range(occs.count):
        o = occs.item(i)
        first.setdefault(o.component.id, o)
    try:
        for c, rec in comp_pairs:
            occ = first.get(c.id)
            if occ is None:
                continue
            p = os.path.join(d, core.safe_file_part(c.id) + '.png')
            try:
                occ.isIsolated = True
                vp.fit()
                if vp.saveAsImageFile(p, size, size) and os.path.isfile(p):
                    rec['thumbnail'] = os.path.relpath(p, os.path.dirname(step_path)).replace('\\', '/')
            finally:
                try:
                    occ.isIsolated = False
                except Exception:
                    pass
    except Exception as e:
        warnings.append('component thumbnails skipped: ' + (str(e).splitlines()[0] if str(e) else repr(e)))
    finally:
        try:
            vp.camera = cam
            vp.refresh()
        except Exception:
            pass


# ---- entry point ------------------------------------------------------------------------------------

def thread_tables():
    start = [os.path.dirname(sys.executable)]
    return core.load_thread_tables(core.find_thread_data_dir(start))


def build(design, step_path, comp=None, occ=None, thumbnails=False, assembly_thumb=True, tables=None):
    """Collect everything for one STEP export and return the sidecar dict (not written)."""
    app = adsk.core.Application.get()
    warnings = []
    scope = comp or design.rootComponent
    pairs = collect_components(scope, warnings)
    if tables is None:
        tables = thread_tables()
        if not tables:
            warnings.append('Fusion thread tables not found; tap drills are empty')
    holes = collect_holes(pairs, tables, warnings)
    src = source_info(design)
    if src.get('unsaved_changes'):
        warnings.append('document has unsaved changes; the STEP reflects the open state, not the saved version')
    if thumbnails:
        component_thumbnails(app, scope, pairs, step_path, warnings)
    asm = assembly_thumbnail(app, step_path) if assembly_thumb else None
    scope_rec = {'component': scope.name, 'is_root': scope.id == design.rootComponent.id,
                 'selected_occurrence': _safe(lambda: occ.fullPathName) if occ else None}
    totals = physical_of(scope, warnings)
    return core.build_document(src, step_path, [r for _, r in pairs], holes, totals=totals, scope=scope_rec,
                               warnings=warnings, assembly_thumbnail=asm, generator_version=VERSION)


def write_sidecar(design, step_path, comp=None, occ=None, thumbnails=False, assembly_thumb=True):
    """Build and write <base>.bom.json next to step_path. Returns the JSON path."""
    doc = build(design, step_path, comp, occ, thumbnails, assembly_thumb)
    probs = core.validate(doc)
    if probs:
        doc['warnings'].extend('schema: ' + p for p in probs)
    return core.write_json(doc, core.sidecar_path(step_path))
