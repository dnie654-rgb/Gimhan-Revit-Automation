from pyrevit import script, forms
import os
import subprocess
import datetime

def log(msg):
    try:
        log_path = os.path.join(os.environ['TEMP'], 'pyRevitUpdateCheck.log')
        with open(log_path, 'a') as f:
            f.write("[{}] {}\n".format(datetime.datetime.now(), msg))
    except:
        pass

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

def check_for_updates():
    log("--- Starting New Update Check ---")
    script_dir = os.path.dirname(__file__)
    repo_root = find_git_root(script_dir)
    log("Location: " + script_dir)

    if not repo_root:
        log("No git root found.")
        return

    try:
        # 1. Fetch from remote
        log("Fetching...")
        subprocess.check_call(["git", "fetch", "origin"], cwd=repo_root, shell=True)

        # 2. Get commit counts (ahead/behind)
        # Output format: ahead <tab> behind
        log("Checking counts...")
        counts = subprocess.check_output(
            ["git", "rev-list", "--left-right", "--count", "master...origin/master"],
            cwd=repo_root,
            shell=True
        ).decode('utf-8').split()

        if len(counts) >= 2:
            ahead = int(counts[0])
            behind = int(counts[1])
            log("Ahead: {}, Behind: {}".format(ahead, behind))

            if behind > 0:
                log("Update available! Showing notification.")
                res = forms.alert(
                    "New updates are available for ToolsByGimhan extensions!\n\n"
                    "You are {} commits behind the remote version.\n\n"
                    "Would you like to install them now?".format(behind),
                    title="Updates Available",
                    yes=True, 
                    no=True
                )
                
                if res:
                    log("User chose Yes. Pulling...")
                    # We use reset hard + pull to ensure a clean state if diverged
                    subprocess.check_call(["git", "reset", "--hard", "origin/master"], cwd=repo_root, shell=True)
                    log("Update success.")
                    forms.alert(
                        "Extensions have been updated successfully!\n"
                        "Please reload pyRevit to see the changes.",
                        title="Update Complete"
                    )
        else:
            log("No divergence found.")
                    
    except Exception as e:
        log("ERROR: " + str(e))

if __name__ == "__main__":
    check_for_updates()
