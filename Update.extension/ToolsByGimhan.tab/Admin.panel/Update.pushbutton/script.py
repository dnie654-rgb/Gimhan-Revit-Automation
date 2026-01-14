
"""
Update Gimhan Extensions from GitHub
"""
import os
import sys
import shutil
import zipfile
import tempfile
import time
from pyrevit import script, forms

# Configuration
REPO_URL = "https://github.com/dnie654-rgb/Gimhan-Revit-Automation/archive/refs/heads/master.zip"
EXTENSIONS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) # .../pyRevit/Extensions
# EXTENSIONS_DIR is calculated relative to:
# Extension/Tab/Panel/Pushbutton/script.py -> 4 levels up

logger = script.get_logger()
output = script.get_output()

def update_extensions():
    # Confirm with user
    res = forms.alert(
        "This will update all Gimhan Extensions from the latest GitHub version.\n"
        "Any local changes to these extensions will be overwritten.\n\n"
        "Do you want to proceed?",
        title="Update Gimhan Extensions",
        yes=True, no=True
    )
    
    if not res:
        return

    output.print_md("### Starting Update Process...")
    output.print_md("Target Directory: `{}`".format(EXTENSIONS_DIR))

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "update.zip")
    
    try:
        # 1. Download
        output.print_md("Downloading latest version from GitHub...")
        
        # Use .NET WebClient for https support often better than urllib in IronPython
        from System.Net import WebClient
        client = WebClient()
        client.DownloadFile(REPO_URL, zip_path)
        
        output.print_md("Download complete.")

        # 2. Extract
        output.print_md("Extracting files...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # Find the inner folder (Repo-master)
        extracted_root = os.path.join(temp_dir, "Gimhan-Revit-Automation-master")
        if not os.path.exists(extracted_root):
            # Fallback if structure is different
            extracted_root = temp_dir

        # 3. Update Extensions
        extensions_to_update = [
            "ParamTransfer.extension",
            "LinkTools.extension",
            "HostTools.extension",
            "Update.extension" 
        ]

        for ext_name in extensions_to_update:
            src_path = os.path.join(extracted_root, ext_name)
            dest_path = os.path.join(EXTENSIONS_DIR, ext_name)

            if os.path.exists(src_path):
                output.print_md("**Updating {}...**".format(ext_name))
                
                # Check if we are updating THIS extension
                # Updating the running script can be tricky, but file ops usually work in Windows 
                # as long as the file isn't locked (Python scripts are read into memory).
                # However, pyRevit locks dlls. pure python should be fine.
                
                if os.path.exists(dest_path):
                    try:
                        shutil.rmtree(dest_path)
                    except Exception as e:
                        output.print_md(":warning: Could not remove old version of {}: {}".format(ext_name, e))
                        output.print_md("Trying to overwrite...")
                
                try:
                    shutil.copytree(src_path, dest_path)
                    output.print_md(":white_check_mark: {} Updated.".format(ext_name))
                except Exception as e:
                    output.print_md(":x: Failed to copy {}: {}".format(ext_name, e))

            else:
                output.print_md(":warning: Attempted to update {}, but it was not found in the downloaded update.".format(ext_name))

        output.print_md("### Update Completed Successfully!")
        output.print_md("Please **Reload pyRevit** to apply changes.")
        
        # reload_button = forms.alert("Update Complete. Reload pyRevit now?", yes=True, no=True)
        # if reload_button:
        #     from pyrevit.loader import sessionmgr
        #     sessionmgr.reload_pyrevit()

    except Exception as e:
        output.print_md(":x: **Error during update**:")
        output.print_md(str(e))
        import traceback
        output.print_md(traceback.format_exc())

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == '__main__':
    update_extensions()
