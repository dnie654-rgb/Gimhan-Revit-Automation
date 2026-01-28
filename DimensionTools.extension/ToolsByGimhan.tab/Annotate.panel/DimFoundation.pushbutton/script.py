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
    """Greedy Dimensioning Strategy: Named References -> Centers -> Geometry Fallback."""
    created_ids = []
    # Use view origin Z as the definitive anchor for the dimension line
    level_elev = view.Origin.Z 
    
    dim_style_name = "Diagonal - 2.5mm Arial"
    dim_type = get_dimension_type_by_name(doc, dim_style_name)

    bbox = foundation.get_BoundingBox(view)
    if not bbox: return created_ids
    center = (bbox.Min + bbox.Max) / 2.0

    # Ensure the "Dimensions" category is forced to ON
    cat = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Dimensions)
    try:
        if view.GetCategoryHidden(cat.Id):
            view.SetCategoryHidden(cat.Id, False)
    except: pass

    # --- Dimension Factory ---
    def make_dim(ref_list, is_width_dim):
        """Creates a dimension from references. is_width_dim = measures Y, line is horizontal."""
        if len(ref_list) < 2: return None
        ref_array = DB.ReferenceArray()
        for r in ref_list: ref_array.Append(r)
        
        if is_width_dim: # measures Y dist (Places line at Bottom -Y)
            placement_normal = DB.XYZ(0, -1, 0)
            offset = (bbox.Max.Y - bbox.Min.Y) / 2.0 + 3.0
            dim_line_dir = DB.XYZ(1, 0, 0)
        else: # measures X dist (Places line at Right +X)
            placement_normal = DB.XYZ(1, 0, 0)
            offset = (bbox.Max.X - bbox.Min.X) / 2.0 + 3.0
            dim_line_dir = DB.XYZ(0, 1, 0)

        # Line setup (Force exact coplanar alignment)
        line_orig = center + placement_normal * offset
        line_orig = DB.XYZ(line_orig.X, line_orig.Y, level_elev)
        line = DB.Line.CreateBound(line_orig - dim_line_dir, line_orig + dim_line_dir)

        try:
            # Draw visual debug line
            try: doc.Create.NewDetailCurve(view, line)
            except: pass
            
            if dim_type:
                return doc.Create.NewDimension(view, line, ref_array, dim_type)
            return doc.Create.NewDimension(view, line, ref_array)
        except Exception as e:
            print("Strategy Attempt Error: {}".format(e))
            return None

    # --- PRIORITY 1: Named Family References ---
    # Revit families often have named planes built-in. These are the most stable.
    # Front/Back usually define the depth (Y), Left/Right define width (X).
    r_front = foundation.GetReferences(DB.FamilyInstanceReferenceType.Front)
    r_back = foundation.GetReferences(DB.FamilyInstanceReferenceType.Back)
    r_left = foundation.GetReferences(DB.FamilyInstanceReferenceType.Left)
    r_right = foundation.GetReferences(DB.FamilyInstanceReferenceType.Right)

    if r_front and r_back:
        d = make_dim([r_front[0], r_back[0]], True)
        if d: created_ids.append(d.Id)
    
    if r_left and r_right:
        d = make_dim([r_left[0], r_right[0]], False)
        if d: created_ids.append(d.Id)

    if created_ids:
        print(">>> Success: Dimensions created using Named Family References.")
        return created_ids

    # --- PRIORITY 2: Center Planes Fallback ---
    # Sometimes planes are named CenterLeftRight or CenterFrontBack
    r_cfb = foundation.GetReferences(DB.FamilyInstanceReferenceType.CenterFrontBack)
    r_clr = foundation.GetReferences(DB.FamilyInstanceReferenceType.CenterLeftRight)

    if not created_ids:
        if r_cfb and r_front:
            d = make_dim([r_cfb[0], r_front[0]], True)
            if d: created_ids.append(d.Id)
        if r_clr and r_left:
            d = make_dim([r_clr[0], r_left[0]], False)
            if d: created_ids.append(d.Id)

    if created_ids:
        print(">>> Success: Dimensions created using Center Fallbacks.")
        return created_ids

    # --- PRIORITY 3: Geometry Scraping (Final Fallback) ---
    print(">>> Strategy 1 & 2 failed. Falling back to Geometry Scraping...")
    side_faces = get_side_faces(foundation, view)
    if side_faces:
        pairs = []
        used = set()
        for i in range(len(side_faces)):
            if i in used: continue
            f1, n1 = side_faces[i]
            for j in range(i + 1, len(side_faces)):
                if j in used: continue
                f2, n2 = side_faces[j]
                if abs(abs(n1.DotProduct(n2)) - 1.0) < 0.01:
                    # Sort references (ensure low-to-high)
                    p1 = f1.Evaluate(DB.UV(0.5, 0.5))
                    p2 = f2.Evaluate(DB.UV(0.5, 0.5))
                    is_x_aligned = abs(n1.X) > abs(n1.Y)
                    if is_x_aligned:
                        pair = [(f1, n1), (f2, n2)] if p1.X < p2.X else [(f2, n2), (f1, n1)]
                    else:
                        pair = [(f1, n1), (f2, n2)] if p1.Y < p2.Y else [(f2, n2), (f1, n1)]
                    pairs.append(pair)
                    used.add(i); used.add(j)
                    break
        
        for p in pairs:
            fl, fh = p[0][0], p[1][0]
            is_horiz = abs(p[0][1].Y) > abs(p[0][1].X)
            d = make_dim([fl.Reference, fh.Reference], is_horiz)
            if d: created_ids.append(d.Id)

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
