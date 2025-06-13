import os
import subprocess
import sys

REPO_URL = "https://github.com/ck4445/ECKOBits.git"


def run_command(cmd):
    """Run a command and exit on failure."""
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}")
        sys.exit(1)


def ensure_repo(script_dir):
    if os.path.isdir(os.path.join(script_dir, '.git')):
        return script_dir
    repo_dir = os.path.join(script_dir, 'ECKOBits')
    if not os.path.isdir(repo_dir):
        run_command(['git', 'clone', REPO_URL, repo_dir])
    else:
        run_command(['git', '-C', repo_dir, 'pull'])
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
