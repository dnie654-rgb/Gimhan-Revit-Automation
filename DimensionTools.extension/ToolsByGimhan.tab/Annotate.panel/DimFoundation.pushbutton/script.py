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

    count = 0
    bbox = foundation.get_BoundingBox(view)
    center = (bbox.Min + bbox.Max) / 2.0
    offset_dist = 1.0 # 1 foot offset for dimension line

    # Ensure the Dimensions category is visible in the view
    cat = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Dimensions)
    if not view.GetCategoryHidden(cat.Id):
        # We can't really "force" it on effectively without knowing if it's hidden by filter
        # but let's at least check if the category is hidden globally in the view.
        pass
    else:
        try:
            view.SetCategoryHidden(cat.Id, False)
            print("Notice: 'Dimensions' category was hidden and has been turned on.")
        except: pass

    for pair in pairs:
        (f1, n1), (f2, n2) = pair
        
        # Determine placement normal for Right/Bottom
        placement_normal = n1
        if abs(n1.X) > abs(n1.Y): # Horizontal pair (side faces)
            if n1.X < 0:
                placement_normal = n2
        else: # Vertical pair (top/bottom faces)
            if n1.Y > 0:
                placement_normal = n2

        ref_array = DB.ReferenceArray()
        ref_array.Append(f1.Reference)
        ref_array.Append(f2.Reference)
        
        # Calculate distance between faces
        p1 = f1.Evaluate(DB.UV(0.5, 0.5))
        p2 = f2.Evaluate(DB.UV(0.5, 0.5))
        dist = p1.DistanceTo(p2)
        
        # Position line outside the bounding box
        # Use a slightly bigger offset (2.0 feet) for clarity
        offset_dist = 2.0
        dim_line_origin = center + placement_normal * (dist/2.0 + offset_dist)
        
        # EXTREMELY IMPORTANT: The line must be in the plane of the view
        # We project the center onto the view's origin plane to ensure Z is consistent
        view_plane = DB.Plane.CreateByNormalAndOrigin(view.ViewDirection, view.Origin)
        # Project center to view plane
        projection = view_plane.Normal.DotProduct(dim_line_origin - view.Origin)
        dim_line_origin = dim_line_origin - view_plane.Normal * projection

        # The dimension line direction should be perpendicular to the placement normal 
        # but oriented relative to the view's Right/Up directions
        if abs(placement_normal.X) > abs(placement_normal.Y):
            perp_dir = view.UpDirection
        else:
            perp_dir = view.RightDirection
            
        line = DB.Line.CreateBound(dim_line_origin - perp_dir, dim_line_origin + perp_dir)
        
        try:
            dim = doc.Create.NewDimension(view, line, ref_array)
            if dim:
                count += 1
        except Exception as e:
            print("Failed to create dimension for element {}: {}".format(foundation.Id, e))

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
