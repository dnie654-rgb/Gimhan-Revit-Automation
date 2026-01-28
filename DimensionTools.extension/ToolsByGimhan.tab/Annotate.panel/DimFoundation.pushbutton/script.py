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
    """Automated dimensioning based on edges."""
    created_ids = []
    level_elev = view.Origin.Z
    
    # 200mm in feet (standard Revit units)
    OFFSET = 200.0 / 304.8 
    
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
    if not edges: return []

    # 2. Extract Bounding Box for Placement
    bbox = fnd.get_BoundingBox(view)
    if not bbox: return []
    center = (bbox.Min + bbox.Max) / 2.0

    # 3. Create Pairs for Vertical and Horizontal measurements
    # Vertical Dims (measuring Y-distance, line is Horizontal)
    # Horizontal Dims (measuring X-distance, line is Vertical)
    
    # Let's filter for unique lines based on normal directions
    horiz_edges = [] # Edges aligned with X (measures X distance)
    vert_edges = []  # Edges aligned with Y (measures Y distance)
    
    for ref, curve in edges:
        direction = curve.Direction
        if abs(direction.DotProduct(DB.XYZ.BasisX)) > 0.99:
            horiz_edges.append((ref, curve))
        elif abs(direction.DotProduct(DB.XYZ.BasisY)) > 0.99:
            vert_edges.append((ref, curve))

    def create_dim_pair(edge_list, is_horizontal_measurement):
        """Creates a dimension between extremist edges in the given list."""
        if len(edge_list) < 2: return None
        
        # Sort by coordinate to find extremities
        if is_horizontal_measurement: # measuring X (horiz) distance
            edge_list.sort(key=lambda x: x[1].GetEndPoint(0).Y)
        else: # measuring Y (vertical) distance
            edge_list.sort(key=lambda x: x[1].GetEndPoint(0).X)

        e_low = edge_list[0][0]
        e_high = edge_list[-1][0]
        
        ref_array = DB.ReferenceArray()
        ref_array.Append(e_low)
        ref_array.Append(e_high)
        
        if is_horizontal_measurement:
            # Placement: Above the footing (Top)
            placement_normal = DB.XYZ(0, 1, 0)
            dim_line_dir = DB.XYZ(1, 0, 0)
            offset_val = (bbox.Max.Y - bbox.Min.Y)/2.0 + OFFSET
        else:
            # Placement: Right of the footing
            placement_normal = DB.XYZ(1, 0, 0)
            dim_line_dir = DB.XYZ(0, 1, 0)
            offset_val = (bbox.Max.X - bbox.Min.X)/2.0 + OFFSET

        line_p1 = center + placement_normal * offset_val
        line_p1 = DB.XYZ(line_p1.X, line_p1.Y, level_elev)
        dim_line = DB.Line.CreateBound(line_p1 - dim_line_dir, line_p1 + dim_line_dir)

        try:
            if dim_type:
                return doc.Create.NewDimension(view, dim_line, ref_array, dim_type)
            return doc.Create.NewDimension(view, dim_line, ref_array)
        except Exception as e:
            print("Auto-Dim Error: {}".format(e))
            return None

    # Measure Vertical (Y) -> Place on Right
    d1 = create_dim_pair(vert_edges, False)
    if d1: created_ids.append(d1.Id)
    
    # Measure Horizontal (X) -> Place on Top
    d2 = create_dim_pair(horiz_edges, True)
    if d2: created_ids.append(d2.Id)

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
