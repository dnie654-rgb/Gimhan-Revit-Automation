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
        deleted_exts = set()
        
        # Check for deletions
        status = subprocess.check_output(
            ["git", "diff", "--name-status", "master", "origin/master"],
            cwd=repo_root, shell=True
        ).decode('utf-8')
        
        for line in status.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                st = parts[0]
                path = parts[1]
                ext_name = next((p.replace(".extension", "") for p in path.split("/") if p.endswith(".extension")), None)
                if ext_name:
                    if st == 'D':
                        deleted_exts.add(ext_name)
                    else:
                        changed_exts.add(ext_name)

        if changed_exts or deleted_exts:
            msg_lines = []
            if changed_exts:
                msg_lines.append("Updated extensions:\n- " + "\n- ".join(sorted(list(changed_exts))))
            if deleted_exts:
                msg_lines.append("Extensions to be removed:\n- " + "\n- ".join(sorted(list(deleted_exts))))
            
            msg = "New updates are available!\n\n" + "\n\n".join(msg_lines) + "\n\nWould you like to sync and clean these tools now?"
            
            res = forms.alert(msg, title="ToolsByGimhan Updates", yes=True, no=True)
            
            if res:
                subprocess.check_call(["git", "reset", "--hard", "origin/master"], cwd=repo_root, shell=True)
                subprocess.check_call(["git", "clean", "-fd"], cwd=repo_root, shell=True)
                forms.alert("Updates installed and deleted tools removed! Please reload pyRevit.", title="Update Success")
                
    except Exception:
        pass

if __name__ == "__main__":
    check_updates()
