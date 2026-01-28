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
    opt.IncludeNonVisibleObjects = False
    
    geom = foundation.get_Geometry(opt)
    if not geom:
        return side_faces

    view_dir = view.ViewDirection # Should be (0,0,1) for plan views

    for obj in geom:
        if isinstance(obj, DB.Solid):
            for face in obj.Faces:
                if not face.Reference:
                    continue
                # Get normal at center
                normal = face.ComputeNormal(DB.UV(0.5, 0.5))
                # Check if face is vertical (normal is perpendicular to view direction)
                if abs(normal.DotProduct(view_dir)) < 0.01:
                    side_faces.append((face, normal))
        elif isinstance(obj, DB.GeometryInstance):
            inst_geom = obj.GetInstanceGeometry()
            for inst_obj in inst_geom:
                if isinstance(inst_obj, DB.Solid):
                    for face in inst_obj.Faces:
                        if not face.Reference:
                            continue
                        normal = face.ComputeNormal(DB.UV(0.5, 0.5))
                        if abs(normal.DotProduct(view_dir)) < 0.01:
                            side_faces.append((face, normal))
                            
    return side_faces

def create_dimensions(doc, view, foundation):
    """Create length and width dimensions for a rectangular foundation."""
    count = 0
    side_faces = get_side_faces(foundation, view)
    
    if len(side_faces) < 4:
        print("Found {} vertical faces for element {}. Need at least 4 for a rectangle.".format(len(side_faces), foundation.Id))
        return 0

    # Group faces by their normals (parallel faces)
    # We expect 2 pairs of parallel faces for a rectangle
    pairs = []
    used_indices = set()
    
    for i in range(len(side_faces)):
        if i in used_indices:
            continue
        face1, normal1 = side_faces[i]
        for j in range(i + 1, len(side_faces)):
            if j in used_indices:
                continue
            face2, normal2 = side_faces[j]
            # Parallel check (dot product is ~1 or ~-1)
            if abs(abs(normal1.DotProduct(normal2)) - 1.0) < 0.01:
                pairs.append(((face1, normal1), (face2, normal2)))
                used_indices.add(i)
                used_indices.add(j)
                break
    
    # We should have at least 2 pairs for a rectangle
    if len(pairs) < 2:
        print("Could not find 2 perpendicular pairs of parallel faces for element {}.".format(foundation.Id))
        return 0

    # --- Debug Information ---
    print("\n--- Processing Foundation {} ---".format(foundation.Id))
    
    # Get the level elevation of the view
    level_elev = 0.0
    if hasattr(view, 'GenLevel') and view.GenLevel:
        level_elev = view.GenLevel.Elevation
        print("View Level Elevation: {}".format(level_elev))
    else:
        level_elev = view.Origin.Z
        print("View Origin Z: {}".format(level_elev))

    bbox = foundation.get_BoundingBox(view)
    if bbox:
        print("Foundation BBox: Min({},{},{}), Max({},{},{})".format(bbox.Min.X, bbox.Min.Y, bbox.Min.Z, bbox.Max.X, bbox.Max.Y, bbox.Max.Z))
        center = (bbox.Min + bbox.Max) / 2.0
    else:
        # Fallback for center calculation
        center = view.Origin 

    # Ensure the Dimensions category is visible in the view
    cat = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Dimensions)
    try:
        if view.GetCategoryHidden(cat.Id):
            view.SetCategoryHidden(cat.Id, False)
            print("Notice: 'Dimensions' category was hidden and has been turned on.")
    except: pass

    for pair in pairs:
        (f1, n1), (f2, n2) = pair
        
        # Determine placement normal for Right/Bottom
        placement_normal = n1
        if abs(n1.X) > abs(n1.Y): # Horizontal pair
            if n1.X < 0: placement_normal = n2
        else: # Vertical pair
            if n1.Y > 0: placement_normal = n2

        ref_array = DB.ReferenceArray()
        ref_array.Append(f1.Reference)
        ref_array.Append(f2.Reference)
        
        # Calculate distance between faces
        p1 = f1.Evaluate(DB.UV(0.5, 0.5))
        p2 = f2.Evaluate(DB.UV(0.5, 0.5))
        dist = p1.DistanceTo(p2)
        
        # Position line outside the bounding box
        offset_dist = 1.5 # feet
        dim_line_origin = center + placement_normal * (dist/2.0 + offset_dist)
        
        # FORCE Z-LEVEL TO MATCH VIEW LEVEL
        dim_line_origin = DB.XYZ(dim_line_origin.X, dim_line_origin.Y, level_elev)

        # The dimension line direction perpendicular to placement normal
        if abs(placement_normal.X) > abs(placement_normal.Y):
            perp_dir = view.UpDirection
        else:
            perp_dir = view.RightDirection
            
        line = DB.Line.CreateBound(dim_line_origin - perp_dir * 3, dim_line_origin + perp_dir * 3)
        print("Creating Dimension Line at Point: ({}, {}, {})".format(dim_line_origin.X, dim_line_origin.Y, dim_line_origin.Z))

        try:
            dim = doc.Create.NewDimension(view, line, ref_array)
            if dim:
                count += 1
                print(">>> Dimension object created successfully.")
        except Exception as e:
            print("!!! Failed to create dimension: {}".format(e))

    return count

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

    total_created = 0
    with revit.Transaction("Dimension Foundations"):
        for fnd in foundations:
            total_created += create_dimensions(doc, view, fnd)

    if total_created > 0:
        print("Created {} dimensions.".format(total_created))
    else:
        forms.alert("No dimensions could be created. Check if foundations are rectangular and visible.")

if __name__ == "__main__":
    main()
