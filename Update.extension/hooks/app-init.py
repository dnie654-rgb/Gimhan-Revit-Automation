from pyrevit import script, forms
import os
import subprocess

def find_git_root(path):
    """Finds the root of the git repository."""
    current_dir = path
    while current_dir:
        if os.path.exists(os.path.join(current_dir, ".git")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return None

def check_for_updates():
    """Checks if the local repository is behind the remote."""
    # This hook runs when Revit starts.
    script_dir = os.path.dirname(__file__)
    repo_root = find_git_root(script_dir)

    if not repo_root:
        return

    try:
        # 1. Fetch from remote in background
        # Note: 'timeout' is not supported in IronPython 2.7 subprocess
        subprocess.check_call(
            ["git", "fetch", "origin"],
            cwd=repo_root,
            shell=True
        )

        # 2. Check status
        output = subprocess.check_output(
            ["git", "status", "-uno"],
            cwd=repo_root,
            shell=True,
            stderr=subprocess.STDOUT
        ).decode('utf-8')

        if "Your branch is behind" in output:
            # Found updates!
            res = forms.alert(
                "New updates are available for ToolsByGimhan extensions!\n\n"
                "Would you like to download and install them now?",
                title="Updates Available",
                yes=True, 
                no=True
            )
            
            if res:
                # Trigger the update script logic
                update_process = subprocess.Popen(
                    ["git", "pull"],
                    cwd=repo_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )
                stdout, stderr = update_process.communicate()
                
                if update_process.returncode == 0:
                    forms.alert(
                        "Extensions have been updated successfully!\n"
                        "Please reload pyRevit to see the changes.",
                        title="Update Complete"
                    )
                else:
                    forms.alert(
                        "Automatic update failed.\n"
                        "Please use the manual 'Update Extensions' button in the ribbon.",
                        title="Update Error"
                    )
                    
    except Exception:
        # Ignore all errors during startup to avoid annoying the user
        pass

if __name__ == "__main__":
    check_for_updates()
