from pyrevit import script, forms
import os
import subprocess

def find_git_root(path):
    current_dir = path
    while current_dir:
        if os.path.exists(os.path.join(current_dir, ".git")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return None

def run_sync():
    script_dir = os.path.dirname(__file__)
    repo_root = find_git_root(script_dir)
    if not repo_root:
        forms.alert("Git repository not found.", title="Error")
        return

    try:
        subprocess.check_call(["git", "fetch", "origin"], cwd=repo_root, shell=True)
        # Check if behind
        counts = subprocess.check_output(
            ["git", "rev-list", "--left-right", "--count", "master...origin/master"],
            cwd=repo_root, shell=True
        ).decode('utf-8').split()
        
        if len(counts) >= 2 and int(counts[1]) > 0:
            res = forms.alert("Updates found. Would you like to sync now?", yes=True, no=True)
            if res:
                # Use clean -fd to remove folders that are gone from Git
                subprocess.check_call(["git", "reset", "--hard", "origin/master"], cwd=repo_root, shell=True)
                subprocess.check_call(["git", "clean", "-fd"], cwd=repo_root, shell=True)
                forms.alert("Successfully updated and cleaned! Please reload pyRevit.", title="Success")
        else:
            forms.alert("Extensions are already up to date.", title="Status")
    except Exception as e:
        forms.alert("Error: " + str(e))

if __name__ == "__main__":
    run_sync()
