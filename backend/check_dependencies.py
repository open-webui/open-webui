#!/usr/bin/env python3
"""
Runtime dependency checker and installer.
This script attempts to import the main application module and automatically
installs any missing dependencies that are in requirements.txt.
"""

import sys
import subprocess
import importlib.util

# Some Python imports don't match their pip package names.
# Add common mappings here to avoid brute-force/manual fixes.
MODULE_TO_PIP = {
    "bs4": "beautifulsoup4",
    "jwt": "PyJWT",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "PIL": "Pillow",
    "cv2": "opencv-python-headless",
    "sklearn": "scikit-learn",
    # Open WebUI-specific helpers
    "langchain_text_splitters": "langchain-text-splitters",
    "sentence_transformers": "sentence-transformers",
}


def _norm(name: str) -> str:
    return (name or "").strip().lower().replace("-", "_")


def get_requirements_packages():
    """Read packages from requirements.txt"""
    packages = []
    try:
        with open("/app/backend/requirements.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before ==, >=, <=, etc.)
                    package_name = (
                        line.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split("[")[0]
                        .strip()
                    )
                    if package_name:
                        packages.append((package_name, line.strip()))
    except Exception as e:
        print(f"Warning: Could not read requirements.txt: {e}")
    return dict(packages)


def install_package(package_spec):
    """Install a package using pip"""
    try:
        print(f"Installing {package_spec}...")
        p = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", package_spec],
            text=True,
            capture_output=True,
        )
        if p.returncode == 0:
            return True
        print(f"Failed to install {package_spec} (exit {p.returncode})")
        if p.stdout:
            print("pip stdout (tail):")
            print("\n".join(p.stdout.splitlines()[-25:]))
        if p.stderr:
            print("pip stderr (tail):")
            print("\n".join(p.stderr.splitlines()[-25:]))
        return False
    except Exception as e:
        print(f"Failed to install {package_spec}: {e}")
        return False


def check_and_install_missing():
    """Try to import the main module and install missing dependencies"""
    requirements = get_requirements_packages()
    # In minimal images it can take many iterations to satisfy deep, chained imports.
    # We keep this finite so a truly broken environment doesn't loop forever.
    max_attempts = 60
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        print(f"\n=== Dependency check attempt {attempt}/{max_attempts} ===")

        try:
            # Try to import the main module
            spec = importlib.util.spec_from_file_location(
                "open_webui.main", "/app/backend/open_webui/main.py"
            )
            if spec is None:
                print("ERROR: Could not load main.py")
                return False

            # This will trigger all imports and reveal missing modules
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            print("✓ All dependencies satisfied!")
            return True

        except ModuleNotFoundError as e:
            missing_module = (
                str(e).split("'")[1]
                if "'" in str(e)
                else str(e).split('"')[1] if '"' in str(e) else None
            )

            if missing_module:
                print(f"Missing module: {missing_module}")

                # Try to find the package in requirements.txt (including known module->pip mappings)
                mapped_pip = MODULE_TO_PIP.get(missing_module) or MODULE_TO_PIP.get(
                    missing_module.split(".")[0]
                )
                candidates = [missing_module]
                if mapped_pip and mapped_pip not in candidates:
                    candidates.append(mapped_pip)

                package_spec = None

                # Pass 1: prefer exact normalized matches from requirements
                for cand in candidates:
                    for req_name, req_spec in requirements.items():
                        if _norm(req_name) == _norm(cand):
                            package_spec = req_spec
                            break
                    if package_spec:
                        break

                # Pass 2: only if no exact match, fall back to fuzzy contains()
                if not package_spec:
                    for cand in candidates:
                        for req_name, req_spec in requirements.items():
                            if _norm(cand) in _norm(req_name) or _norm(
                                req_name
                            ) in _norm(cand):
                                package_spec = req_spec
                                break
                        if package_spec:
                            break

                if package_spec:
                    if install_package(package_spec):
                        continue  # Retry import
                    else:
                        print(
                            f"Failed to install {package_spec}, trying package name only..."
                        )
                        # Try installing mapped pip name first, then module name
                        if mapped_pip and install_package(mapped_pip):
                            continue
                        if install_package(missing_module):
                            continue
                else:
                    # Try installing by module name
                    if mapped_pip:
                        print(
                            f"Package not found in requirements.txt, trying to install {mapped_pip} for module {missing_module}..."
                        )
                        if install_package(mapped_pip):
                            continue
                    print(
                        f"Package not found in requirements.txt, trying to install {missing_module}..."
                    )
                    if install_package(missing_module):
                        continue

            print(f"ERROR: Could not resolve missing dependency: {e}")
            if attempt >= max_attempts:
                return False

        except Exception as e:
            print(f"ERROR during import check: {e}")
            import traceback

            traceback.print_exc()
            if attempt >= max_attempts:
                return False

    return False


if __name__ == "__main__":
    success = check_and_install_missing()
    sys.exit(0 if success else 1)
