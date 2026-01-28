# -*- coding: utf-8 -*-
from pyrevit import revit, forms, DB

def run_diagnostic():
    doc = revit.doc
    uidoc = revit.uidoc
    view = doc.ActiveView
    
    selection = uidoc.Selection.GetElementIds()
    if not selection:
        forms.alert("Select a foundation first.")
        return

    fnd = doc.GetElement(selection[0])
    print("--- Diagnostics for Element {} ---".format(fnd.Id))
    print("Category: {}".format(fnd.Category.Name))
    
    # 1. Check References from Geometry
    opt = DB.Options()
    opt.ComputeReferences = True
    opt.View = view
    opt.IncludeNonVisibleObjects = True
    
    geom = fnd.get_Geometry(opt)
    ref_count = 0
    if geom:
        for obj in geom:
            if isinstance(obj, DB.Solid):
                for face in obj.Faces:
                    if face.Reference:
                        ref_count += 1
                        print("Found Solid Face Reference: {}".format(face.Reference.ElementReferenceType))
            elif isinstance(obj, DB.GeometryInstance):
                inst_geom = obj.GetInstanceGeometry()
                for inst_obj in inst_geom:
                    if isinstance(inst_obj, DB.Solid):
                        for f in inst_obj.Faces:
                            if f.Reference:
                                ref_count += 1
                                # print("Found Inst Face Reference: {}".format(f.Reference.ElementReferenceType))

    print("Total geometric references found: {}".format(ref_count))

    # 2. Check Named References
    named_ref_types = [
        DB.FamilyInstanceReferenceType.StrongReference,
        DB.FamilyInstanceReferenceType.WeakReference,
        DB.FamilyInstanceReferenceType.CenterLeftRight,
        DB.FamilyInstanceReferenceType.CenterFrontBack,
        DB.FamilyInstanceReferenceType.Left,
        DB.FamilyInstanceReferenceType.Right,
        DB.FamilyInstanceReferenceType.Front,
        DB.FamilyInstanceReferenceType.Back
    ]
    
    for rt in named_ref_types:
        try:
            refs = fnd.GetReferences(rt)
            if refs:
                print("Named Reference Found: {} (Count: {})".format(rt, len(refs)))
        except: pass

    # 3. List Dimension Styles
    print("\n--- Available Dimension Styles ---")
    styles = DB.FilteredElementCollector(doc).OfClass(DB.DimensionType)
    for s in styles:
        print("- {}".format(DB.Element.Name.__get__(s)))

if __name__ == "__main__":
    run_diagnostic()
