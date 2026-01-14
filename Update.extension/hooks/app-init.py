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

def check_updates():
    try:
        script_dir = os.path.dirname(__file__)
        repo_root = find_git_root(script_dir)
        if not repo_root:
            return

        # Fetch in background
        subprocess.Popen(["git", "fetch", "origin"], cwd=repo_root, shell=True).wait()

        # Check what changed
        diff = subprocess.check_output(
            ["git", "diff", "--name-only", "master", "origin/master"],
            cwd=repo_root, shell=True
        ).decode('utf-8')
        
        if not diff.strip():
            return

        lines = diff.splitlines()
        changed_exts = set()
        for line in lines:
            parts = line.split("/")
            for p in parts:
                if p.endswith(".extension"):
                    changed_exts.add(p.replace(".extension", ""))
                    break
        
        if changed_exts:
            ext_list = "\n- ".join(sorted(list(changed_exts)))
            msg = "New updates are available for the following extensions:\n\n- {}\n\nWould you like to sync and update these tools now?".format(ext_list)
            
            res = forms.alert(msg, title="ToolsByGimhan Updates", yes=True, no=True)
            
            if res:
                subprocess.check_call(["git", "reset", "--hard", "origin/master"], cwd=repo_root, shell=True)
                forms.alert("Updates installed! Please reload pyRevit to apply changes.", title="Update Success")
                
    except Exception:
        pass

if __name__ == "__main__":
    check_updates()
