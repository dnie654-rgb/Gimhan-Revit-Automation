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
    """Robust dimensioning: Handles rotation by calculating perpendicular directions."""
    created_ids = []
    
    # 1. Setup
    level_elev = view.GenLevel.Elevation if view.GenLevel else view.Origin.Z
    
    dim_style_name = "Diagonal - 2.5mm Arial"
    dim_type = get_dimension_type_by_name(doc, dim_style_name)

    bbox = foundation.get_BoundingBox(view)
    if not bbox: return created_ids
    center = (bbox.Min + bbox.Max) / 2.0

    # 2. Get Side Faces
    side_faces = get_side_faces(foundation, view)
    if not side_faces:
        print("!!! Face Scraping: No vertical side faces found.")
        return created_ids

    # 3. Group by Normals
    pairs = []
    used = set()
    for i in range(len(side_faces)):
        if i in used: continue
        f1, n1 = side_faces[i]
        for j in range(i + 1, len(side_faces)):
            if j in used: continue
            f2, n2 = side_faces[j]
            # Check for parallel faces (dot product 1 or -1)
            if abs(abs(n1.DotProduct(n2)) - 1.0) < 0.01:
                pairs.append(((f1, n1), (f2, n2)))
                used.add(i)
                used.add(j)
                break
    
    # 4. Create Dimensions
    for pair in pairs:
        (f1, n1), (f2, n2) = pair
        
        # Determine Placement Side
        # We'll use the one that is more "Right" (+X) or "Bottom" (-Y)
        placement_normal = n1
        if n1.X + n1.Y < n2.X + n2.Y:
            # This is a bit of a heuristic to find the "outer" normal
            # For Right/Bottom, let's just pick based on world coordinates
            if abs(n1.X) > abs(n1.Y): # Mostly Horizontal
                if n1.X < 0: placement_normal = n2
            else: # Mostly Vertical
                if n1.Y > 0: placement_normal = n2

        ref_array = DB.ReferenceArray()
        ref_array.Append(f1.Reference)
        ref_array.Append(f2.Reference)
        
        # PERPENDICULAR DIRECTION: Calculate exactly from normal to handle rotation
        # Dimension line must be perfectly perpendicular to the face normal
        perp_dir = DB.XYZ.BasisZ.CrossProduct(placement_normal).Normalize()
        
        # Position with offset
        # Distance between faces
        p1 = f1.Evaluate(DB.UV(0.5, 0.5))
        p2 = f2.Evaluate(DB.UV(0.5, 0.5))
        dist = p1.DistanceTo(p2)
        
        offset_dist = dist/2.0 + 3.0 # 3 feet away
        line_orig = center + placement_normal * offset_dist
        line_orig = DB.XYZ(line_orig.X, line_orig.Y, level_elev)

        line = DB.Line.CreateBound(line_orig - perp_dir * 2, line_orig + perp_dir * 2)
        
        try:
            # Draw visual debug line
            try: doc.Create.NewDetailCurve(view, line)
            except: pass
            
            dim = None
            if dim_type:
                dim = doc.Create.NewDimension(view, line, ref_array, dim_type)
            else:
                dim = doc.Create.NewDimension(view, line, ref_array)
            
            if dim:
                created_ids.append(dim.Id)
                print(">>> Dimension {} created successfully.".format(dim.Id))
        except Exception as e:
            print("!!! Revit Error creating dimension: {}".format(e))
            
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
