import os
import subprocess
import sys

DEFAULT_REPO_URL = "https://github.com/ck4445/ECKOBits.git"

def run_command(cmd, cwd=None):
    """Run a command and exit on failure."""
    try:
        subprocess.check_call(cmd, cwd=cwd)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}")
        sys.exit(1)

def ensure_repo(script_dir):
    """Clone the repo if needed and ensure pulls succeed."""
    if os.path.isdir(os.path.join(script_dir, '.git')):
        repo_dir = script_dir
    else:
        repo_dir = os.path.join(script_dir, 'ECKOBits')
        if not os.path.isdir(repo_dir):
            repo_url = os.environ.get('REPO_URL', DEFAULT_REPO_URL)
            run_command(['git', 'clone', repo_url, repo_dir])

    # Configure pull behavior to avoid divergence errors and update the repo
    run_command(['git', 'config', 'pull.rebase', 'false'], cwd=repo_dir)
    run_command(['git', 'pull'], cwd=repo_dir)
    return repo_dir

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    repo_dir = ensure_repo(script_dir)

    req_file = os.path.join(repo_dir, 'requirements.txt')
    if os.path.isfile(req_file):
        run_command([sys.executable, '-m', 'pip', 'install', '-r', req_file])

    run_command([sys.executable, os.path.join(repo_dir, 'main.py')])

if __name__ == '__main__':
    main()
