import os
import subprocess
import sys
import hashlib

DEFAULT_REPO_URL = "https://github.com/ck4445/ECKOBits.git"

def run_command(cmd, cwd=None):
    try:
        subprocess.check_call(cmd, cwd=cwd)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}")
        sys.exit(1)

def file_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def ensure_repo(script_dir):
    if os.path.isdir(os.path.join(script_dir, '.git')):
        repo_dir = script_dir
    else:
        repo_dir = os.path.join(script_dir, 'ECKOBits')
        if not os.path.isdir(repo_dir):
            repo_url = os.environ.get('REPO_URL', DEFAULT_REPO_URL)
            run_command(['git', 'clone', repo_url, repo_dir])
    run_command(['git', 'config', 'pull.rebase', 'false'], cwd=repo_dir)
    run_command(['git', 'pull'], cwd=repo_dir)
    return repo_dir

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = ensure_repo(script_dir)

    req_file = os.path.join(repo_dir, 'requirements.txt')
    checksum_file = os.path.join(repo_dir, '.requirements.sha256')

    need_install = True
    if os.path.isfile(checksum_file) and os.path.isfile(req_file):
        saved_checksum = None
        with open(checksum_file, "r") as f:
            saved_checksum = f.read().strip()
        current_checksum = file_sha256(req_file)
        if saved_checksum == current_checksum:
            print("Requirements file unchanged, skipping pip install.")
            need_install = False
        else:
            print("Requirements file changed, will reinstall packages.")
            need_install = True

    if need_install and os.path.isfile(req_file):
        run_command([sys.executable, '-m', 'pip', 'install', '-r', req_file])
        # Save current checksum
        with open(checksum_file, "w") as f:
            f.write(file_sha256(req_file))

    run_command([sys.executable, os.path.join(repo_dir, 'main.py')])

if __name__ == '__main__':
    main()
