from pyrevit import revit, DB, forms

# Select Families
selection = forms.select_families(use_selection=True)
if not selection:
    forms.alert('No families selected.', exitscript=True)

# Ask for Parameter Name
param_name = forms.ask_for_string(
    default='NewParam',
    prompt='Enter Parameter Name:',
    title='Add Parameter'
)
if not param_name:
    forms.alert('Parameter name is required.', exitscript=True)

# Define simple types mapping (targeting Revit 2022+)
# Using SpecTypeId which is the modern replacement for ParameterType
try:
    # Revit 2022+
    param_types = {
        'Text': DB.SpecTypeId.String.Text,
        'Integer': DB.SpecTypeId.Int.Integer,
        'Length': DB.SpecTypeId.Length,
        'Yes/No': DB.SpecTypeId.Boolean.YesNo
    }
    group_type = DB.GroupTypeId.General
except AttributeError:
    # Older Revit fallback (approximate, might need adjustment if user is on very old revit)
    forms.alert("This script is optimized for Revit 2022+. Please update Revit or contact support.", exitscript=True)

selected_type_name = forms.SelectFromList.show(
    sorted(param_types.keys()),
    title='Select Parameter Type',
    button_name='Select'
)
if not selected_type_name:
    forms.alert('Parameter type is required.', exitscript=True)

target_type = param_types[selected_type_name]

# Instance or Type
# forms.alert returns True/False/None. yes_text mapped to True?
# Wait, forms.alert returns True if 'Yes/OK' clicked, False if 'No'.
# We want Instance=True (Yes) or Type=False (No).
is_instance = forms.alert(
    'Create as Instance Parameter? (No = Type)',
    yes_text='Instance',
    no_text='Type'
)

# Load Options Handler
class IDontWantToBePrompted(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

# Process
doc = revit.doc

# Start Group Transaction for the project context
t_group = DB.TransactionGroup(doc, "Add Family Parameters")
t_group.Start()

try:
    for family in selection:
        print("Processing family: {}".format(family.Name))
        
        # Open Family Doc
        try:
            fam_doc = doc.EditFamily(family)
        except Exception as e:
            print(" - Could not edit family: {}".format(e))
            continue
        
        # Start Transaction in Family Doc
        t_fam = DB.Transaction(fam_doc, "Add Parameter to Family")
        t_fam.Start()
        
        try:
            # Check if parameter already exists?
            # FamilyManager.get_Parameter(name) might work? Or look through Parameters property.
            # Simplified: just try adding.
            
            fam_doc.FamilyManager.AddParameter(
                param_name,
                group_type,
                target_type,
                is_instance
            )
            print(" - Parameter '{}' added.".format(param_name))
            t_fam.Commit()
            
            # Load back
            fam_doc.LoadFamily(doc, IDontWantToBePrompted())
            print(" - Family reloaded.")
            
        except Exception as e:
            print(" - Error adding parameter: {}".format(e))
            t_fam.RollBack()
        finally:
            # Close the family document without saving to disk (changes were loaded to project)
            fam_doc.Close(False)

    t_group.Assimilate()
    forms.alert("Completed processing families!", warn_icon=False)

except Exception as e:
    t_group.RollBack()
    forms.alert("Critical Error: {}".format(e))
