import os
import subprocess
from collections import Counter

CONFIG_FILE_EXTENSIONS = (".json", ".yml", ".yaml", ".ini", ".conf", ".toml")


def is_text_file(filepath):
    # Check for binary file by scanning for null bytes.
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(4096)
        if b"\0" in chunk:
            return False
        return True
    except Exception:
        return False


def should_skip_file(path):
    base = os.path.basename(path)
    # Skip dotfiles and dotdirs
    if base.startswith("."):
        return True
    # Skip config files by extension
    if base.lower().endswith(CONFIG_FILE_EXTENSIONS):
        return True
    return False


def get_tracked_files():
    try:
        output = subprocess.check_output(["git", "ls-files"], text=True)
        files = output.strip().split("\n")
        files = [f for f in files if f and os.path.isfile(f)]
        return files
    except subprocess.CalledProcessError:
        print("Error: Are you in a git repository?")
        return []


def main():
    files = get_tracked_files()
    email_counter = Counter()
    total_lines = 0

    for file in files:
        if should_skip_file(file):
            continue
        if not is_text_file(file):
            continue
        try:
            blame = subprocess.check_output(
                ["git", "blame", "-e", file], text=True, errors="replace"
            )
            for line in blame.splitlines():
                # The email always inside <>
                if "<" in line and ">" in line:
                    try:
                        email = line.split("<")[1].split(">")[0].strip()
                    except Exception:
                        continue
                    email_counter[email] += 1
                    total_lines += 1
        except subprocess.CalledProcessError:
            continue

    for email, lines in email_counter.most_common():
        percent = (lines / total_lines * 100) if total_lines else 0
        print(f"{email}: {lines}/{total_lines} {percent:.2f}%")


if __name__ == "__main__":
    main()
