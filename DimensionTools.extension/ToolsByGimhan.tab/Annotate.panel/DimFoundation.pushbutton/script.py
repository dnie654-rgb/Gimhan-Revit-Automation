# -*- coding: utf-8 -*-
"""
Foundation Dimension Tool
Automatically adds length and width dimensions to rectangular foundations in plan views.
"""

from pyrevit import revit, forms, DB
import traceback

def get_dimension_type_by_name(doc, name):
    """Find a DimensionType by its name."""
    collector = DB.FilteredElementCollector(doc).OfClass(DB.DimensionType)
    for dt in collector:
        if DB.Element.Name.__get__(dt) == name:
            return dt
    return None

def create_dimensions_for_foundation(doc, view, foundation):
    """Bulletproof dimension creation using named references and specific style."""
    created_ids = []
    
    # 1. Setup Directions and Style
    x_dir = view.RightDirection
    y_dir = view.UpDirection
    level_elev = view.GenLevel.Elevation if view.GenLevel else view.Origin.Z
    
    # Specific Style requested by user
    dim_style_name = "Diagonal - 2.5mm Arial"
    dim_type = get_dimension_type_by_name(doc, dim_style_name)
    if dim_type:
        print("Using Dimension Style: {}".format(dim_style_name))
    else:
        print("Warning: Style '{}' not found. Using default.".format(dim_style_name))

    bbox = foundation.get_BoundingBox(view)
    if not bbox: return created_ids
    center = (bbox.Min + bbox.Max) / 2.0
    
    # 2. Strategy: Use Named References (Most reliable for FamilyInstances)
    # We map Revit's built-in reference types to our directions
    # Width (Horizontal Dim): Needs Front and Back references
    # Length (Vertical Dim): Needs Left and Right references
    
    def try_create(ref1_type, ref2_type, is_horizontal):
        try:
            r1 = foundation.GetReferences(ref1_type)
            r2 = foundation.GetReferences(ref2_type)
            
            if r1 and r2:
                ref_array = DB.ReferenceArray()
                ref_array.Append(r1[0])
                ref_array.Append(r2[0])
                
                if is_horizontal: # Width Dim (Placed at Bottom)
                    offset = (bbox.Max.Y - bbox.Min.Y) / 2.0 + 1.5
                    line_orig = DB.XYZ(center.X, center.Y - offset, level_elev)
                    line = DB.Line.CreateBound(line_orig - x_dir, line_orig + x_dir)
                else: # Length Dim (Placed at Right)
                    offset = (bbox.Max.X - bbox.Min.X) / 2.0 + 1.5
                    line_orig = DB.XYZ(center.X + offset, center.Y, level_elev)
                    line = DB.Line.CreateBound(line_orig - y_dir, line_orig + y_dir)
                
                # Draw Debug Line
                try: doc.Create.NewDetailCurve(view, line)
                except: pass
                
                # Create Dimension
                if dim_type:
                    dim = doc.Create.NewDimension(view, line, ref_array, dim_type)
                else:
                    dim = doc.Create.NewDimension(view, line, ref_array)
                
                if dim:
                    print(">>> Dimension created using {}/{} references.".format(ref1_type, ref2_type))
                    return dim.Id
        except Exception as e:
            print("!!! Failed pair {}/{}: {}".format(ref1_type, ref2_type, e))
        return None

    # Try Width (Bottom)
    wid = try_create(DB.FamilyInstanceReferenceType.Front, DB.FamilyInstanceReferenceType.Back, True)
    if wid: created_ids.append(wid)
    
    # Try Length (Right)
    len_id = try_create(DB.FamilyInstanceReferenceType.Left, DB.FamilyInstanceReferenceType.Right, False)
    if len_id: created_ids.append(len_id)
    
    # FALLBACK: If named references failed, try Center references
    if not wid:
        wid = try_create(DB.FamilyInstanceReferenceType.CenterFrontBack, DB.FamilyInstanceReferenceType.Front, True)
        if wid: created_ids.append(wid)
    
    if not len_id:
        len_id = try_create(DB.FamilyInstanceReferenceType.CenterLeftRight, DB.FamilyInstanceReferenceType.Left, False)
        if len_id: created_ids.append(len_id)

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
