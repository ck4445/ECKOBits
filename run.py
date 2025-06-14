import os
import subprocess
import sys


def run_command(cmd):
    """Run a command and exit on failure."""
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}")
        sys.exit(1)



def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    req_file = os.path.join(script_dir, 'requirements.txt')
    if os.path.isfile(req_file):
        run_command([sys.executable, '-m', 'pip', 'install', '-r', req_file])

    run_command([sys.executable, os.path.join(script_dir, 'main.py')])


if __name__ == '__main__':
    main()
