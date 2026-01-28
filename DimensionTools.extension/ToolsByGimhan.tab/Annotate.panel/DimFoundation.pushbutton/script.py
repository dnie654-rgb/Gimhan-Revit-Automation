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
    """Refined dimensioning using user-requested style and high-priority references."""
    created_ids = []
    
    # 1. Setup
    x_dir = view.RightDirection
    y_dir = view.UpDirection
    level_elev = view.GenLevel.Elevation if view.GenLevel else view.Origin.Z
    
    # User's Style
    dim_style_name = "Diagonal - 2.5mm Arial"
    dim_type = get_dimension_type_by_name(doc, dim_style_name)

    bbox = foundation.get_BoundingBox(view)
    if not bbox: return created_ids
    
    # Calculate Center
    center = (bbox.Min + bbox.Max) / 2.0
    
    # Get Faces
    side_faces = get_side_faces(foundation, view)
    if not side_faces: return created_ids

    # Group into pairs
    pairs = []
    used = set()
    for i in range(len(side_faces)):
        if i in used: continue
        f1, n1 = side_faces[i]
        for j in range(i + 1, len(side_faces)):
            if j in used: continue
            f2, n2 = side_faces[j]
            if abs(abs(n1.DotProduct(n2)) - 1.0) < 0.01:
                pairs.append(((f1, n1), (f2, n2)))
                used.add(i)
                used.add(j)
                break
    
    # Create Dimensions
    for pair in pairs:
        (f1, n1), (f2, n2) = pair
        
        # Determine Placement (Right or Bottom)
        is_x_side = abs(n1.DotProduct(x_dir)) > 0.9
        placement_normal = n1
        
        if is_x_side: # X-aligned faces -> Needs Vertical Dim on Right
            if n1.DotProduct(x_dir) < 0: placement_normal = n2
            is_horizontal_dim = False
        else: # Y-aligned faces -> Needs Horizontal Dim on Bottom
            if n1.DotProduct(y_dir) > 0: placement_normal = n2
            is_horizontal_dim = True

        ref_array = DB.ReferenceArray()
        ref_array.Append(f1.Reference)
        ref_array.Append(f2.Reference)
        
        # Position with LARGER offset (4 feet) for clear visibility
        face_dist = bbox.Max.X - bbox.Min.X if not is_horizontal_dim else bbox.Max.Y - bbox.Min.Y
        offset_val = face_dist/2.0 + 3.0 # 3 feet clear offset
        
        line_orig = center + placement_normal * offset_val
        # Force Z slightly above level for visibility (0.1 feet)
        line_orig = DB.XYZ(line_orig.X, line_orig.Y, level_elev + 0.1)

        perp_dir = y_dir if not is_horizontal_dim else x_dir
        line = DB.Line.CreateBound(line_orig - perp_dir, line_orig + perp_dir)
        
        try:
            # OPTIONAL: Draw a detail line for verification (User says these are visible!)
            try: doc.Create.NewDetailCurve(view, line)
            except: pass
            
            dim = None
            if dim_type:
                dim = doc.Create.NewDimension(view, line, ref_array, dim_type)
            else:
                dim = doc.Create.NewDimension(view, line, ref_array)
            
            if dim:
                created_ids.append(dim.Id)
                print(">>> Created dim {}. Normal: {}".format(dim.Id, placement_normal))
        except Exception as e:
            print("!!! Failed to create dimension: {}".format(e))
            
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
