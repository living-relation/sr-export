"""In-Fusion smoke test for SR Export. Run from Fusion (Scripts and Add-Ins, or a Python bridge).
Works only in a NEW scratch document that it closes WITHOUT saving; your open documents are not
touched. Output goes to %TEMP%/srexport_fusion_smoke.
"""
import importlib
import json
import os
import sys
import tempfile

import adsk.core
import adsk.fusion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in globals() else os.environ['SREXPORT_ROOT']


def main():
    addin = os.path.join(ROOT, 'SRExport')
    for p in (ROOT, addin):
        if p not in sys.path:
            sys.path.insert(0, p)
    for m in [m for m in sys.modules if m.split('.')[0] in ('SRExport', 'sr_fusion_common', 'export_core', 'export_ops')]:
        del sys.modules[m]
    eops = importlib.import_module('SRExport.export_ops')
    emain = importlib.import_module('SRExport.SRExport')
    app = adsk.core.Application.get()
    out_dir = os.path.join(tempfile.gettempdir(), 'srexport_fusion_smoke')
    os.makedirs(out_dir, exist_ok=True)
    res = {}
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    try:
        des = adsk.fusion.Design.cast(app.activeProduct)
        root = des.rootComponent
        for i, (w, h) in enumerate(((2, 1), (1, 1))):
            sk = root.sketches.add(root.xYConstructionPlane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(i * 5, 0, 0),
                                                              adsk.core.Point3D.create(i * 5 + w, h, 0))
            root.features.extrudeFeatures.addSimple(sk.profiles.item(0), adsk.core.ValueInput.createByReal(1),
                                                    adsk.fusion.FeatureOperations.NewComponentFeatureOperation)
        occ = root.occurrences.item(0)
        body = occ.component.bRepBodies.item(0)
        face = max([body.faces.item(i) for i in range(body.faces.count)], key=lambda f: f.area)
        r1 = eops.export(des, ['step', 'f3d', 'stl', '3mf', 'iges', 'sat', 'dxf'], out_dir, 'smoke v2',
                         dxf_entity=face)
        r2 = eops.export(des, ['step', 'stl'], out_dir, 'smoke_occ', occ.component, occ)
        r3 = eops.export(des, ['step'], out_dir, 'smoke v3')
        res['export_all'] = {k: v[0] for k, v in r1.items()}
        res['export_errors'] = {k: v[1] for k, v in r1.items() if not v[0]}
        res['export_component'] = {k: v[0] for k, v in r2.items()}
        res['bom_json'] = r1.get('bom_json')
        res['overwrite_same_path'] = r3['step'][1] == r1['step'][1] and r3['step'][0]
        ui = app.userInterface
        emain.run(None)
        res['button_registered'] = bool(ui.commandDefinitions.itemById(emain.CMD_ID))
        emain.stop(None)
        res['button_removed'] = not ui.commandDefinitions.itemById(emain.CMD_ID)
    finally:
        doc.close(False)
    res['files'] = sorted(os.listdir(out_dir))
    print(json.dumps(res, indent=1, default=str))
    return res


def run(context):
    try:
        res = main()
        adsk.core.Application.get().userInterface.messageBox(json.dumps(res, indent=1, default=str)[:3000])
    except Exception:
        import traceback
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


if __name__ == '__main__' and 'SREXPORT_ROOT' in os.environ:
    main()
