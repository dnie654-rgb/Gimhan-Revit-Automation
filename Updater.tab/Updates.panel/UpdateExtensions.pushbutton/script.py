from pyrevit import script, forms
import os
import subprocess

logger = script.get_logger()
output = script.get_output()

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

def update_repo():
    """Runs git pull to update the repository."""
    script_dir = os.path.dirname(__file__)
    repo_root = find_git_root(script_dir)

    if not repo_root:
        forms.alert("Could not find git repository root.", exitscript=True)
        return

    logger.info("Found repo root: {}".format(repo_root))
    
    try:
        # Run git pull
        # Startups usually don't have console window, so we capture output
        logger.info("Running git pull...")
        
        # Using specific executable if needed, but 'git' should be in PATH
        process = subprocess.Popen(
            ["git", "pull"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True 
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info("Update successful!")
            print(stdout.decode('utf-8'))
            forms.alert("Extension updated successfully!\nPlease reload pyRevit to apply changes.", title="Success")
        else:
            logger.error("Update failed.")
            print(stderr.decode('utf-8'))
            forms.alert("Update failed. Check output for details.", title="Error")

    except Exception as e:
        logger.error("An error occurred: {}".format(e))
        forms.alert("An error occurred: {}".format(e))

if __name__ == "__main__":
    if forms.check_clickable_obj(True): # Simple check or just run
        update_repo()
