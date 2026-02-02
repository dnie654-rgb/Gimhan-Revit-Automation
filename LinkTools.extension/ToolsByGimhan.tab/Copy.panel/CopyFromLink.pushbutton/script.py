#! ironpython
# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms, script
from System.Collections.Generic import List

doc = revit.doc
uidoc = revit.uidoc

class CategoryWrapper(forms.TemplateListItem):
    @property
    def name(self):
        return self.item.Name

def main():
    # 1. Collect all Link Instances
    collector = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance)
    links = list(collector)
    
    if not links:
        forms.alert("No linked models found in the current project.", exitscript=True)
    
    # Map Name -> LinkInstance
    link_dict = {}
    for link in links:
        link_doc = link.GetLinkDocument()
        if link_doc:
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
    
    # 3. Collect all elements in that link to find categories
    all_elements = DB.FilteredElementCollector(source_doc).WhereElementIsNotElementType().ToElements()
    
    category_map = {}
    for el in all_elements:
        if el.Category:
            cat_id = el.Category.Id.IntegerValue
            if cat_id not in category_map:
                category_map[cat_id] = el.Category

    # 4. Select Categories
    sorted_categories = sorted(category_map.values(), key=lambda c: c.Name)
    selected_categories = forms.SelectFromList.show(
        [CategoryWrapper(c) for c in sorted_categories],
        title="Select Categories to Copy from Link",
        multiselect=True,
        button_name="Select Categories"
    )

    if not selected_categories:
        script.exit()

    selected_cat_ids = [c.Id for c in selected_categories]

    # 5. Collect Elements of Selected Categories
    cat_filter = DB.ElementMulticategoryFilter(List[DB.ElementId](selected_cat_ids))
    elements_to_copy = DB.FilteredElementCollector(source_doc).WherePasses(cat_filter).WhereElementIsNotElementType().ToElementIds()

    if not elements_to_copy:
        forms.alert("No elements found in selected categories.", exitscript=True)

    # 6. Copy Elements
    t = DB.Transaction(doc, "Copy Linked Elements by Category")
    t.Start()
    
    try:
        options = DB.CopyPasteOptions()
        copied_ids = DB.ElementTransformUtils.CopyElements(
            source_doc,
            elements_to_copy,
            doc,
            transform, 
            options
        )
        
        print("Successfully copied {} elements from link.".format(len(copied_ids)))
        
    except Exception as e:
        print("Error during copy: {}".format(e))
        t.RollBack()
        return

    t.Commit()

if __name__ == '__main__':
    main()
