from importlib import util
import os
import re

from config import TOOLS_DIR, FUNCTIONS_DIR


def extract_frontmatter(file_path):
    """
    Extract frontmatter as a dictionary from the specified file path.
    """
    frontmatter = {}
    frontmatter_pattern = re.compile(r"^([a-z_]+):\s*(.*)\s*$", re.IGNORECASE)

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip() == '"""':
                # End of frontmatter section
                break
            match = frontmatter_pattern.match(line)
            if match:
                key, value = match.groups()
                frontmatter[key] = value

    return frontmatter


def load_toolkit_module_by_id(toolkit_id):
    toolkit_path = os.path.join(TOOLS_DIR, f"{toolkit_id}.py")
    spec = util.spec_from_file_location(toolkit_id, toolkit_path)
    module = util.module_from_spec(spec)
    frontmatter = extract_frontmatter(toolkit_path)

    try:
        spec.loader.exec_module(module)
        print(f"Loaded module: {module.__name__}")
        if hasattr(module, "Tools"):
            return module.Tools(), frontmatter
        else:
            raise Exception("No Tools class found")
    except Exception as e:
        print(f"Error loading module: {toolkit_id}")
        # Move the file to the error folder
        os.rename(toolkit_path, f"{toolkit_path}.error")
        raise e


def load_function_module_by_id(function_id):
    function_path = os.path.join(FUNCTIONS_DIR, f"{function_id}.py")

    spec = util.spec_from_file_location(function_id, function_path)
    module = util.module_from_spec(spec)
    frontmatter = extract_frontmatter(function_path)

    try:
        spec.loader.exec_module(module)
        print(f"Loaded module: {module.__name__}")
        if hasattr(module, "Pipe"):
            return module.Pipe(), "pipe", frontmatter
        elif hasattr(module, "Filter"):
            return module.Filter(), "filter", frontmatter
        else:
            raise Exception("No Function class found")
    except Exception as e:
        print(f"Error loading module: {function_id}")
        # Move the file to the error folder
        os.rename(function_path, f"{function_path}.error")
        raise e
