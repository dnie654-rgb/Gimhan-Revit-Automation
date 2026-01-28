# -*- coding: utf-8 -*-
"""
Foundation Dimension Tool
Automatically adds length and width dimensions to rectangular foundations in plan views.
"""

from pyrevit import revit, forms, DB
import traceback

def find_strong_references(foundation, view, direction):
    """Find references parallel to a given direction."""
    refs = []
    opt = DB.Options()
    opt.ComputeReferences = True
    opt.View = view
    opt.IncludeNonVisibleObjects = True # Important for family references
    
    geom = foundation.get_Geometry(opt)
    
    def walk_geom(g_elem):
        found_refs = []
        for obj in g_elem:
            if isinstance(obj, DB.Solid):
                for face in obj.Faces:
                    if not face.Reference: continue
                    try:
                        normal = face.ComputeNormal(DB.UV(0.5, 0.5))
                        if abs(abs(normal.DotProduct(direction)) - 1.0) < 0.01:
                            found_refs.append(face.Reference)
                    except: pass
            elif isinstance(obj, DB.GeometryInstance):
                found_refs.extend(walk_geom(obj.GetInstanceGeometry()))
        return found_refs

    if geom:
        refs = walk_geom(geom)
    
    # Also check named references (often more stable)
    for ref_type in [DB.FamilyInstanceReferenceType.StrongReference, 
                    DB.FamilyInstanceReferenceType.WeakReference,
                    DB.FamilyInstanceReferenceType.CenterLeftRight,
                    DB.FamilyInstanceReferenceType.CenterFrontBack,
                    DB.FamilyInstanceReferenceType.Left,
                    DB.FamilyInstanceReferenceType.Right,
                    DB.FamilyInstanceReferenceType.Front,
                    DB.FamilyInstanceReferenceType.Back]:
        try:
            named_refs = foundation.GetReferences(ref_type)
            for r in named_refs:
                # We can't easily check the direction of a named reference without a bit move work,
                # but we'll collect them to see if they work as fallbacks if needed.
                pass
        except: pass

    return refs

def create_dimensions_for_foundation(doc, view, foundation):
    """Refined dimension creation for a foundation."""
    created_ids = []
    
    # 1. Get directions
    x_dir = view.RightDirection
    y_dir = view.UpDirection
    level_elev = view.GenLevel.Elevation if view.GenLevel else view.Origin.Z
    
    bbox = foundation.get_BoundingBox(view)
    if not bbox: return created_ids
    center = (bbox.Min + bbox.Max) / 2.0
    
    # 2. Get Width Dims (Dimensions to Y-facing faces, line is Horizontal along X)
    y_refs = find_strong_references(foundation, view, y_dir)
    if len(y_refs) >= 2:
        ref_array = DB.ReferenceArray()
        # Find the two references furthest apart in Y
        # For simplicity in this tool, we'll try to find any pair that works
        ref_array.Append(y_refs[0])
        ref_array.Append(y_refs[-1])
        
        # Placement: Bottom of foundation (-Y)
        offset = (bbox.Max.Y - bbox.Min.Y) / 2.0 + 1.5
        line_orig = DB.XYZ(center.X, center.Y - offset, level_elev)
        line = DB.Line.CreateBound(line_orig - x_dir, line_orig + x_dir)
        
        try:
            dim = doc.Create.NewDimension(view, line, ref_array)
            if dim: created_ids.append(dim.Id)
        except Exception as e:
            print("Width Dim Failed: {}".format(e))

    # 3. Get Length Dims (Dimensions to X-facing faces, line is Vertical along Y)
    x_refs = find_strong_references(foundation, view, x_dir)
    if len(x_refs) >= 2:
        ref_array = DB.ReferenceArray()
        ref_array.Append(x_refs[0])
        ref_array.Append(x_refs[-1])
        
        # Placement: Right of foundation (+X)
        offset = (bbox.Max.X - bbox.Min.X) / 2.0 + 1.5
        line_orig = DB.XYZ(center.X + offset, center.Y, level_elev)
        line = DB.Line.CreateBound(line_orig - y_dir, line_orig + y_dir)
        
        try:
            dim = doc.Create.NewDimension(view, line, ref_array)
            if dim: created_ids.append(dim.Id)
        except Exception as e:
            print("Length Dim Failed: {}".format(e))
            
    return created_ids

def main():
    doc = revit.doc
    uidoc = revit.uidoc
    view = doc.ActiveView

    if not isinstance(view, DB.ViewPlan):
        forms.alert("Please run this tool in a Floor Plan view.", exitscript=True)

    selection = uidoc.Selection.GetElementIds()
    if not selection:
        forms.alert("Please select one or more foundations.", exitscript=True)

    foundations = []
    for eid in selection:
        el = doc.GetElement(eid)
        if el.Category and el.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_StructuralFoundation):
            foundations.append(el)

    if not foundations:
        forms.alert("No Structural Foundations selected.", exitscript=True)

    created_dims = []
    with revit.Transaction("Dimension Foundations"):
        for fnd in foundations:
            ids = create_dimensions_for_foundation(doc, view, fnd)
            if ids:
                created_dims.extend(ids)

    if created_dims:
        print("Created {} dimensions. SELECTING them now...".format(len(created_dims)))
        # SELECT the created dimensions so user can see them highlighted
        uidoc.Selection.SetElementIds(List[DB.ElementId](created_dims))
    else:
        forms.alert("No dimensions could be created.")

if __name__ == "__main__":
    # Import List for selection
    import clr
    clr.AddReference('System')
    from System.Collections.Generic import List
    main()
