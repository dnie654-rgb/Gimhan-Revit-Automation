#! ironpython
# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.UI.Selection import ObjectType
from System.Collections.Generic import List

doc = revit.doc
uidoc = revit.uidoc

def main():
    # 1. Collect all Link Instances
    collector = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance)
    links = list(collector)
    
    if not links:
        forms.alert("No linked models found in the current project.", exitscript=True)
    
    # Map Name -> LinkInstance
    # Use GetLinkDocument() to check if it's loaded
    link_dict = {}
    for link in links:
        link_doc = link.GetLinkDocument()
        if link_doc:
            # Create a nice name: "Link Name - [Link Instance ID]"
            # Using Name property of instance, usually matches type name
            name = "{} (ID: {})".format(link.Name, link.Id)
            link_dict[name] = link
    
    if not link_dict:
        forms.alert("No LOADED links found.", exitscript=True)
        
    sorted_names = sorted(link_dict.keys())

    # 2. Select Link
    selected_name = forms.SelectFromList.show(
        sorted_names,
        title="Select Source Link",
        multiselect=False
    )
    
    if not selected_name:
        script.exit()
        
    selected_link_instance = link_dict[selected_name]
    source_doc = selected_link_instance.GetLinkDocument()
    transform = selected_link_instance.GetTotalTransform()
    
    # 3. Pick Elements from that Link
    # Note: PickObjects with LinkedElement allows picking nested elements
    try:
        references = uidoc.Selection.PickObjects(
            ObjectType.LinkedElement, 
            "Select elements in the Link to Copy"
        )
    except Exception as e:
        # Check if it was just a cancellation
        if "Operation canceled by user" in str(e):
             script.exit() # Clean exit
        else:
             forms.alert("Error during selection: {}".format(e))
             return

    if not references:
        return

    ids_to_copy = []
    
    for ref in references:
        # Validate that the pick comes from the SELECTED link
        # ref.ElementId is the ID of the Link Instance
        if ref.ElementId == selected_link_instance.Id:
            ids_to_copy.append(ref.LinkedElementId)
        else:
            print("Skipped selection from a different link instance.")

    if not ids_to_copy:
        forms.alert("No elements selected from the chosen link.", exitscript=True)

    # 4. Copy Elements
    t = DB.Transaction(doc, "Copy Linked Elements")
    t.Start()
    
    try:
        # CopyElements(sourceDoc, sourceElementIds, destinationDoc, transform, options)
        options = DB.CopyPasteOptions()
        copied_ids = DB.ElementTransformUtils.CopyElements(
            source_doc,
            List[DB.ElementId](ids_to_copy), # Create .NET List
            doc,
            transform, 
            options
        )
        
        print("Successfully copied {} elements.".format(len(copied_ids)))
        print("IDs: {}".format([i.IntegerValue for i in copied_ids]))
        
    except Exception as e:
        print("Error during copy: {}".format(e))
        t.RollBack()
        return

    t.Commit()

if __name__ == '__main__':
    main()
