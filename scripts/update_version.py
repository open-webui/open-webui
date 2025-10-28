"""
Update version across Open WebUI project files.

Usage:
    uv run python scripts/update_version.py <new_version>

Example:
    uv run python scripts/update_version.py 0.7.0
"""

import json
import re
import sys
from pathlib import Path


def update_version(new_version: str) -> None:
    """Update version in package.json and pyproject.toml."""

    # Validate version format (basic semver check)
    if not re.match(r"^\d+\.\d+\.\d+(-\w+)?$", new_version):
        print(f"❌ Invalid version format: {new_version}")
        print("   Expected format: X.Y.Z or X.Y.Z-tag (e.g., 0.7.0 or 0.7.0-beta)")
        sys.exit(1)

    project_root = Path(__file__).parent.parent

    # Update package.json
    package_json_path = project_root / "package.json"
    if package_json_path.exists():
        with open(package_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        old_version = data.get("version", "unknown")
        data["version"] = new_version

        with open(package_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent="\t")
            f.write("\n")  # Ensure trailing newline

        print(f"✅ Updated package.json: {old_version} → {new_version}")
    else:
        print("⚠️  package.json not found")

    # Update pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")

        # Find current version
        current_match = re.search(r'version = "([^"]+)"', content)
        old_version = current_match.group(1) if current_match else "unknown"

        # Replace version
        content = re.sub(
            r'(version = ")[^"]+(")(\s*# Static version)',
            f'\\1{new_version}\\2\\3',
            content
        )

        pyproject_path.write_text(content, encoding="utf-8")
        print(f"✅ Updated pyproject.toml: {old_version} → {new_version}")
    else:
        print("⚠️  pyproject.toml not found")

    print(f"\n🎉 Version successfully updated to {new_version}")
    print("\n📝 Next steps:")
    print("   1. Review the changes: git diff")
    print("   2. Commit: git add package.json pyproject.toml && git commit -m 'chore: bump version to " + new_version + "'")
    print("   3. Tag: git tag v" + new_version)
    print("   4. Build frontend: npm run build")
    print("   5. Build package: uv build")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/update_version.py <new_version>")
        print("Example: uv run python scripts/update_version.py 0.7.0")
        sys.exit(1)

    new_version = sys.argv[1]
    update_version(new_version)

