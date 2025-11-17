#!/usr/bin/env python3
"""
Simplified validation test for prune scripts.
This tests file structure, syntax, and basic validation without requiring
full Open WebUI dependencies.
"""

import sys
import ast
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
passed = 0
failed = 0
warnings = 0

def test_file_exists(filepath):
    """Test if a file exists."""
    global passed, failed
    if filepath.exists():
        print(f"✓ {filepath.name} exists")
        passed += 1
        return True
    else:
        print(f"✗ {filepath.name} missing")
        failed += 1
        return False

def test_python_syntax(filepath):
    """Test if a Python file has valid syntax."""
    global passed, failed, warnings
    try:
        with open(filepath) as f:
            ast.parse(f.read())
        print(f"✓ {filepath.name} has valid Python syntax")
        passed += 1
        return True
    except SyntaxError as e:
        print(f"✗ {filepath.name} has syntax error: {e}")
        failed += 1
        return False
    except Exception as e:
        print(f"⚠ {filepath.name} could not be parsed: {e}")
        warnings += 1
        return False

def test_file_not_empty(filepath):
    """Test if a file is not empty."""
    global passed, failed
    if filepath.stat().st_size > 0:
        print(f"✓ {filepath.name} is not empty ({filepath.stat().st_size} bytes)")
        passed += 1
        return True
    else:
        print(f"✗ {filepath.name} is empty")
        failed += 1
        return False

def test_has_shebang(filepath):
    """Test if a Python script has a shebang."""
    global passed, failed, warnings
    with open(filepath) as f:
        first_line = f.readline()
    if first_line.startswith('#!/'):
        print(f"✓ {filepath.name} has shebang")
        passed += 1
        return True
    else:
        print(f"⚠ {filepath.name} missing shebang (may be intentional)")
        warnings += 1
        return False

def test_has_docstring(filepath):
    """Test if a Python file has a module docstring."""
    global passed, failed, warnings
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read())
        docstring = ast.get_docstring(tree)
        if docstring:
            print(f"✓ {filepath.name} has module docstring")
            passed += 1
            return True
        else:
            print(f"⚠ {filepath.name} missing module docstring")
            warnings += 1
            return False
    except Exception as e:
        print(f"⚠ {filepath.name} could not check docstring: {e}")
        warnings += 1
        return False

def test_executable(filepath):
    """Test if a file is executable."""
    global passed, failed, warnings
    if os.access(filepath, os.X_OK):
        print(f"✓ {filepath.name} is executable")
        passed += 1
        return True
    else:
        print(f"⚠ {filepath.name} is not executable")
        warnings += 1
        return False

def count_lines(filepath):
    """Count lines in a file."""
    with open(filepath) as f:
        return len(f.readlines())

def main():
    """Run all validation tests."""
    global passed, failed, warnings

    print("="*70)
    print("PRUNE SCRIPTS VALIDATION TEST")
    print("="*70)
    print()

    # Core Python files
    python_files = [
        'prune_core.py',
        'prune_models.py',
        'prune_operations.py',
        'prune_cli_interactive.py',
        'standalone_prune.py',
        'prune.py',
        'test_prune.py',
    ]

    # Documentation files
    doc_files = [
        'README.md',
        'USAGE_GUIDE.md',
        'ANALYSIS.md',
        'FEATURES.md',
        'WARNINGS.md',
        'IMPLEMENTATION_SUMMARY.md',
        'example_cron.txt',
    ]

    # Utility files
    util_files = [
        'run_prune.sh',
        'requirements.txt',
    ]

    print("Testing Core Python Files:")
    print("-" * 70)
    for filename in python_files:
        filepath = SCRIPT_DIR / filename
        print(f"\n{filename}:")
        if test_file_exists(filepath):
            test_file_not_empty(filepath)
            test_python_syntax(filepath)
            test_has_docstring(filepath)
            if filename in ['prune.py', 'prune_cli_interactive.py', 'standalone_prune.py', 'test_prune.py']:
                test_has_shebang(filepath)
                test_executable(filepath)
            lines = count_lines(filepath)
            print(f"  Lines: {lines}")

    print("\n" + "="*70)
    print("Testing Documentation Files:")
    print("-" * 70)
    for filename in doc_files:
        filepath = SCRIPT_DIR / filename
        print(f"\n{filename}:")
        if test_file_exists(filepath):
            test_file_not_empty(filepath)
            lines = count_lines(filepath)
            print(f"  Lines: {lines}")

    print("\n" + "="*70)
    print("Testing Utility Files:")
    print("-" * 70)
    for filename in util_files:
        filepath = SCRIPT_DIR / filename
        print(f"\n{filename}:")
        if test_file_exists(filepath):
            test_file_not_empty(filepath)
            if filename.endswith('.sh'):
                test_has_shebang(filepath)
                test_executable(filepath)
            lines = count_lines(filepath)
            print(f"  Lines: {lines}")

    # Calculate total lines
    print("\n" + "="*70)
    print("LINE COUNT VERIFICATION:")
    print("-" * 70)
    total_lines = 0
    categories = {
        'Core Python': python_files,
        'Documentation': doc_files,
        'Utilities': util_files,
    }

    for category, files in categories.items():
        category_lines = 0
        for filename in files:
            filepath = SCRIPT_DIR / filename
            if filepath.exists():
                lines = count_lines(filepath)
                category_lines += lines
        print(f"{category}: {category_lines} lines")
        total_lines += category_lines

    print(f"\nTotal: {total_lines} lines")
    print(f"Target: 3,588 lines (2x original 1,794)")
    print(f"Achievement: {total_lines / 3588 * 100:.1f}% of target")
    if total_lines > 3588:
        print(f"✓ EXCEEDED target by {total_lines - 3588} lines ({(total_lines / 3588 - 1) * 100:.1f}%)")

    # Structure validation
    print("\n" + "="*70)
    print("STRUCTURE VALIDATION:")
    print("-" * 70)

    # Check for required imports in files
    checks = [
        ('prune_models.py', 'BaseModel', 'Pydantic models'),
        ('prune_core.py', 'VectorDatabaseCleaner', 'Abstract base class'),
        ('prune_core.py', 'ChromaDatabaseCleaner', 'ChromaDB implementation'),
        ('prune_core.py', 'PGVectorDatabaseCleaner', 'PGVector implementation'),
        ('prune_operations.py', 'get_active_file_ids', 'File ID collection'),
        ('standalone_prune.py', 'argparse', 'CLI arguments'),
        ('prune_cli_interactive.py', 'rich', 'Interactive UI'),
        ('test_prune.py', 'unittest', 'Test framework'),
    ]

    for filename, search_term, description in checks:
        filepath = SCRIPT_DIR / filename
        if filepath.exists():
            with open(filepath) as f:
                content = f.read()
            if search_term in content:
                print(f"✓ {filename} contains {search_term} ({description})")
                passed += 1
            else:
                print(f"✗ {filename} missing {search_term} ({description})")
                failed += 1

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY:")
    print("="*70)
    print(f"Passed:   {passed} ✓")
    print(f"Failed:   {failed} ✗")
    print(f"Warnings: {warnings} ⚠")
    print()

    if failed == 0:
        print("✓ ALL VALIDATION TESTS PASSED")
        return 0
    else:
        print(f"✗ {failed} VALIDATION TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
