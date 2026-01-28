# -*- coding: utf-8 -*-
"""
Automated Foundation Dimension Tool
Detects parallel edges and adds dimensions on the Right and Upper sides.
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

def create_dimensions_for_foundation(doc, view, fnd):
    """Automated dimensioning: Corrected Logic & Placement."""
    created_ids = []
    level_elev = view.Origin.Z
    
    # 200mm to feet conversion (200 / 304.8)
    OFFSET_FT = 0.656168 
    
    dim_style_name = "Diagonal - 2.5mm Arial"
    dim_type = get_dimension_type_by_name(doc, dim_style_name)

    # 1. Scrape Edges with View References
    opt = DB.Options()
    opt.ComputeReferences = True
    opt.View = view
    opt.IncludeNonVisibleObjects = True
    
    geom = fnd.get_Geometry(opt)
    if not geom: return []

    edges = []
    def walk_geom(g_elem):
        for obj in g_elem:
            if isinstance(obj, DB.Solid):
                for edge in obj.Edges:
                    if edge.Reference:
                        curve = edge.AsCurve()
                        if isinstance(curve, DB.Line):
                            edges.append((edge.Reference, curve))
            elif isinstance(obj, DB.GeometryInstance):
                walk_geom(obj.GetInstanceGeometry())

    walk_geom(geom)
    if not edges: 
        print("No edges found with references for foundation {}".format(fnd.Id))
        return []

    # 2. Extract Bounding Box for Placement
    bbox = fnd.get_BoundingBox(view)
    if not bbox: return []
    center = (bbox.Min + bbox.Max) / 2.0

    # Logic:
    # 1. Horizontal Edges (Up/Down) -> Measure Y-height -> Place on Right (+X)
    # 2. Vertical Edges (Left/Right) -> Measure X-width -> Place on Top (+Y)
    
    horiz_edges = [] # X-aligned
    vert_edges = []  # Y-aligned
    
    for ref, curve in edges:
        direction = curve.Direction
        if abs(direction.DotProduct(DB.XYZ.BasisX)) > 0.99:
            horiz_edges.append((ref, curve))
        elif abs(direction.DotProduct(DB.XYZ.BasisY)) > 0.99:
            vert_edges.append((ref, curve))

    def process_pair(edge_list, is_measuring_width):
        """is_measuring_width = True means we measure Left-to-Right (X)."""
        if len(edge_list) < 2: return None
        
        # Sort to find the outermost edges
        if is_measuring_width: # measuring X (between Vertical edges)
            edge_list.sort(key=lambda x: x[1].GetEndPoint(0).X)
        else: # measuring Y (between Horizontal edges)
            edge_list.sort(key=lambda x: x[1].GetEndPoint(0).Y)

        ref_array = DB.ReferenceArray()
        ref_array.Append(edge_list[0][0])
        ref_array.Append(edge_list[-1][0])
        
        if is_measuring_width:
            # Placement: Above the footing (Top side +Y)
            placement_normal = DB.XYZ(0, 1, 0)
            dim_line_dir = DB.XYZ(1, 0, 0)
            offset_dist = (bbox.Max.Y - bbox.Min.Y)/2.0 + OFFSET_FT
        else:
            # Placement: Right of the footing (Right side +X)
            placement_normal = DB.XYZ(1, 0, 0)
            dim_line_dir = DB.XYZ(0, 1, 0)
            offset_dist = (bbox.Max.X - bbox.Min.X)/2.0 + OFFSET_FT

        line_p1 = center + placement_normal * offset_dist
        line_p1 = DB.XYZ(line_p1.X, line_p1.Y, level_elev)
        dim_line = DB.Line.CreateBound(line_p1 - dim_line_dir, line_p1 + dim_line_dir)

        try:
            if dim_type:
                return doc.Create.NewDimension(view, dim_line, ref_array, dim_type)
            return doc.Create.NewDimension(view, dim_line, ref_array)
        except Exception as e:
            print("Auto-Dim Pair Error: {}".format(e))
            return None

    # Horizontal Dims (measuring X, using Vertical edges) -> Upper side
    d_width = process_pair(vert_edges, True)
    if d_width: created_ids.append(d_width.Id)
    
    # Vertical Dims (measuring Y, using Horizontal edges) -> Right side
    d_height = process_pair(horiz_edges, False)
    if d_height: created_ids.append(d_height.Id)

    return created_ids

def main():
    doc = revit.doc
    uidoc = revit.uidoc
    view = doc.ActiveView

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
    with revit.Transaction("Automated Foundations Dim"):
        for fnd in foundations:
            ids = create_dimensions_for_foundation(doc, view, fnd)
            if ids:
                created_dims.extend(ids)

    if created_dims:
        from System.Collections.Generic import List
        uidoc.Selection.SetElementIds(List[DB.ElementId](created_dims))
        print("Done. Created {} dimensions.".format(len(created_dims)))
    else:
        forms.alert("No dimensions could be created.")

if __name__ == "__main__":
    main()
