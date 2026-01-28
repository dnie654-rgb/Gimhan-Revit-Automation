# -*- coding: utf-8 -*-
"""
Foundation Dimension Tool
Automatically adds length and width dimensions to rectangular foundations in plan views.
"""

from pyrevit import revit, forms, DB
import traceback

def get_side_faces(foundation, view):
    """Get the vertical side faces of a foundation."""
    side_faces = []
    opt = DB.Options()
    opt.ComputeReferences = True
    opt.View = view
    opt.IncludeNonVisibleObjects = True
    
    geom = foundation.get_Geometry(opt)
    if not geom: return side_faces

    view_dir = view.ViewDirection

    def walk_geom(g_elem):
        found = []
        for obj in g_elem:
            if isinstance(obj, DB.Solid):
                for face in obj.Faces:
                    if not face.Reference: continue
                    normal = face.ComputeNormal(DB.UV(0.5, 0.5))
                    if abs(normal.DotProduct(view_dir)) < 0.01:
                        found.append((face, normal))
            elif isinstance(obj, DB.GeometryInstance):
                found.extend(walk_geom(obj.GetInstanceGeometry()))
        return found
    
    return walk_geom(geom)

def get_dimension_type_by_name(doc, name):
    """Find a DimensionType by its name."""
    collector = DB.FilteredElementCollector(doc).OfClass(DB.DimensionType)
    for dt in collector:
        if DB.Element.Name.__get__(dt) == name:
            return dt
    return None

def create_dimensions_for_foundation(doc, view, foundation):
    """Refined Dimensioning: Sorted References + Strict Plane Alignment."""
    created_ids = []
    
    # 1. Setup Directions and Style
    x_dir = view.RightDirection
    y_dir = view.UpDirection
    level_elev = view.GenLevel.Elevation if view.GenLevel else view.Origin.Z
    
    dim_style_name = "Diagonal - 2.5mm Arial"
    dim_type = get_dimension_type_by_name(doc, dim_style_name)

    # 2. Scrape Faces with View-Specific Options
    opt = DB.Options()
    opt.ComputeReferences = True
    opt.View = view
    opt.IncludeNonVisibleObjects = True
    
    geom = foundation.get_Geometry(opt)
    if not geom: return created_ids

    side_faces = []
    def walk_geom(g_elem):
        for obj in g_elem:
            if isinstance(obj, DB.Solid):
                for face in obj.Faces:
                    if not face.Reference: continue
                    normal = face.ComputeNormal(DB.UV(0.5, 0.5))
                    # Normal must be perpendicular to view direction (usually Z)
                    if abs(normal.DotProduct(view.ViewDirection)) < 0.01:
                        side_faces.append((face, normal))
            elif isinstance(obj, DB.GeometryInstance):
                walk_geom(obj.GetInstanceGeometry())

    walk_geom(geom)
    if not side_faces: return created_ids

    # 3. Group and SORT pairs
    # Sorting ensures ReferenceArray order: [Left, Right] or [Bottom, Top]
    pairs = []
    used = set()
    for i in range(len(side_faces)):
        if i in used: continue
        f1, n1 = side_faces[i]
        for j in range(i + 1, len(side_faces)):
            if j in used: continue
            f2, n2 = side_faces[j]
            # Parallel check
            if abs(abs(n1.DotProduct(n2)) - 1.0) < 0.01:
                # Get center points for sorting
                p1 = f1.Evaluate(DB.UV(0.5, 0.5))
                p2 = f2.Evaluate(DB.UV(0.5, 0.5))
                
                # Determine "Order" (e.g., sort by X or Y)
                if abs(n1.X) > abs(n1.Y): # Faces are X-facing (Vertical sides)
                    sorted_pair = [(f1, n1), (f2, n2)] if p1.X < p2.X else [(f2, n2), (f1, n1)]
                else: # Faces are Y-facing (Horizontal sides)
                    sorted_pair = [(f1, n1), (f2, n2)] if p1.Y < p2.Y else [(f2, n2), (f1, n1)]
                
                pairs.append(sorted_pair)
                used.add(i)
                used.add(j)
                break

    # 4. Create Dimensions
    for pair in pairs:
        (f_low, n_low), (f_high, n_high) = pair
        
        # Decide placement side: 
        # For X-facing (vertical) pairs -> Right of high face (+X)
        # For Y-facing (horizontal) pairs -> Bottom of low face (-Y)
        is_x_facing = abs(n_low.X) > abs(n_low.Y)
        
        ref_array = DB.ReferenceArray()
        ref_array.Append(f_low.Reference)
        ref_array.Append(f_high.Reference)
        
        bbox = foundation.get_BoundingBox(view)
        if not bbox: continue
        center = (bbox.Min + bbox.Max) / 2.0
        
        if is_x_facing:
            # Length Dim (Placed on Right)
            dim_line_dir = y_dir
            placement_normal = DB.XYZ(1, 0, 0) # Right
            offset = (bbox.Max.X - bbox.Min.X) / 2.0 + 3.0
        else:
            # Width Dim (Placed on Bottom)
            dim_line_dir = x_dir
            placement_normal = DB.XYZ(0, -1, 0) # Bottom
            offset = (bbox.Max.Y - bbox.Min.Y) / 2.0 + 3.0

        line_orig = center + placement_normal * offset
        line_orig = DB.XYZ(line_orig.X, line_orig.Y, level_elev)
        line = DB.Line.CreateBound(line_orig - dim_line_dir, line_orig + dim_line_dir)

        try:
            # Final attempt creation
            dim = None
            if dim_type:
                dim = doc.Create.NewDimension(view, line, ref_array, dim_type)
            else:
                dim = doc.Create.NewDimension(view, line, ref_array)
            
            if dim:
                created_ids.append(dim.Id)
                print(">>> Dimension {} successfully created at {}.".format(dim.Id, line_orig))
        except Exception as e:
            print("!!! Dimension Creation Error: {}".format(e))
            
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
    # Using TransactionGroup for better interaction
    tg = DB.TransactionGroup(doc, "Dim Foundation Strategy")
    tg.Start()
    
    with revit.Transaction("Dimension Details"):
        for fnd in foundations:
            ids = create_dimensions_for_foundation(doc, view, fnd)
            if ids:
                created_dims.extend(ids)

    tg.Commit()

    if created_dims:
        print("Done. Created {} dimensions. SELECTING them now...".format(len(created_dims)))
        from System.Collections.Generic import List
        uidoc.Selection.SetElementIds(List[DB.ElementId](created_dims))
    else:
        forms.alert("No dimensions could be created.")

if __name__ == "__main__":
    # Import List for selection
    import clr
    clr.AddReference('System')
    main()
