#! ironpython
# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List

doc = revit.doc
uidoc = revit.uidoc

def get_selected_elements():
    selection = uidoc.Selection.GetElementIds()
    if not selection:
         # Optional: Prompt to pick
         try:
             refs = uidoc.Selection.PickObjects(DB.ObjectType.Element, "Select elements to change Level")
             return [doc.GetElement(r.ElementId) for r in refs]
         except:
             return []
    return [doc.GetElement(id) for id in selection]

def get_level_param(element):
    # Try different parameter sources for "Level"
    # 1. FAMILY_LEVEL_PARAM (Most common for instances)
    p = element.get_Parameter(DB.BuiltInParameter.FAMILY_LEVEL_PARAM)
    if p and not p.IsReadOnly: return p
    
    # 2. WALL_BASE_CONSTRAINT (Walls)
    p = element.get_Parameter(DB.BuiltInParameter.WALL_BASE_CONSTRAINT)
    if p and not p.IsReadOnly: return p
    
    # 3. SCHEDULE_BASE_LEVEL_PARAM (Columns, etc)
    p = element.get_Parameter(DB.BuiltInParameter.SCHEDULE_BASE_LEVEL_PARAM)
    if p and not p.IsReadOnly: return p
    
    # 4. Name lookup fallback
    p = element.LookupParameter("Level")
    if p and not p.IsReadOnly: return p
    
    p = element.LookupParameter("Base Level")
    if p and not p.IsReadOnly: return p
    
    p = element.LookupParameter("Base Constraint")
    if p and not p.IsReadOnly: return p

    return None

def get_offset_param(element):
    # Try different offset parameters
    # Common built-ins
    p = element.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET)
    if p and not p.IsReadOnly: return p
    
    p = element.get_Parameter(DB.BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM)
    if p and not p.IsReadOnly: return p
    
    p = element.get_Parameter(DB.BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM)
    if p and not p.IsReadOnly: return p
    
    # Name lookup
    names = ["Base Offset", "Offset", "Height Offset From Level", "Offset from Host"]
    for name in names:
        p = element.LookupParameter(name)
        if p and not p.IsReadOnly: return p
        
    return None

def main():
    # 1. Get Elements
    elements = get_selected_elements()
    if not elements:
        forms.alert("No elements selected.", exitscript=True)

    # 2. Get Levels
    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements())
    levels.sort(key=lambda l: l.Elevation)
    
    level_dict = {}
    for l in levels:
        name = l.Name
        level_dict[name] = l

    selected_level_name = forms.SelectFromList.show(
        sorted(level_dict.keys(), key=lambda n: level_dict[n].Elevation),
        title="Select Target Level",
        multiselect=False
    )
    
    if not selected_level_name:
        script.exit()
        
    target_level = level_dict[selected_level_name]
    target_level_id = target_level.Id
    target_elevation = target_level.Elevation

    # 3. Transaction
    t = DB.Transaction(doc, "Change Element Level (Keep Position)")
    t.Start()
    
    success_count = 0
    fail_count = 0
    
    for el in elements:
        try:
            # A. Get Level Param
            p_level = get_level_param(el)
            if not p_level:
                print("Element {}: No Level parameter found.".format(el.Id))
                fail_count += 1
                continue
                
            # B. Get Current Level info
            # We can try to get the element's current level from the parameter or LevelId property
            current_level_id = el.LevelId
            if current_level_id == DB.ElementId.InvalidElementId:
                # Try getting from parameter if LevelId property is invalid (some families)
                 if p_level.StorageType == DB.StorageType.ElementId:
                     current_level_id = p_level.AsElementId()
            
            if current_level_id == DB.ElementId.InvalidElementId:
                print("Element {}: Could not determine current Level.".format(el.Id))
                fail_count += 1
                continue
                
            current_level = doc.GetElement(current_level_id)
            if not current_level:
                 # valid ID but element null?
                 print("Element {}: Current Level not found.".format(el.Id))
                 fail_count += 1
                 continue

            current_elevation_base = current_level.Elevation
            
            # C. Get Offset Param & Value
            p_offset = get_offset_param(el)
            current_offset_val = 0.0
            if p_offset:
                current_offset_val = p_offset.AsDouble()
            
            # D. Calculate Position
            # Absolute Z = CurrentLevelZ + CurrentOffset
            absolute_z = current_elevation_base + current_offset_val
            
            # New Offset = Absolute Z - TargetLevelZ
            new_offset_val = absolute_z - target_elevation
            
            # E. Apply
            p_level.Set(target_level_id)
            if p_offset:
                p_offset.Set(new_offset_val)
            elif abs(new_offset_val) > 0.001:
                # If we need an offset but found no parameter, warn user
                print("Element {}: Changed Level, but could not set Offset to maintain position.".format(el.Id))
            
            success_count += 1

        except Exception as e:
            print("Element {}: Error - {}".format(el.Id, e))
            fail_count += 1

    t.Commit()
    
    print("--------------------------")
    print("Success: {}".format(success_count))
    print("Failed/Skipped: {}".format(fail_count))

if __name__ == '__main__':
    main()
