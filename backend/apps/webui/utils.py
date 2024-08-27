import os
import re
import subprocess
import sys
from importlib import util

from apps.webui.models.functions import Functions
from apps.webui.models.tools import Tools
from config import FUNCTIONS_DIR, TOOLS_DIR


def extract_frontmatter(file_path):
    """
    Extract frontmatter as a dictionary from the specified file path.
    """
    frontmatter = {}
    frontmatter_started = False
    frontmatter_ended = False
    frontmatter_pattern = re.compile(r"^\s*([a-z_]+):\s*(.*)\s*$", re.IGNORECASE)

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            first_line = file.readline()
            if first_line.strip() != '"""':
                # The file doesn't start with triple quotes
                return {}

            frontmatter_started = True

            for line in file:
                if '"""' in line:
                    if frontmatter_started:
                        frontmatter_ended = True
                        break

                if frontmatter_started and not frontmatter_ended:
                    match = frontmatter_pattern.match(line)
                    if match:
                        key, value = match.groups()
                        frontmatter[key.strip()] = value.strip()

    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
        return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

    return frontmatter


def load_toolkit_module_by_id(toolkit_id):
    toolkit_path = os.path.join(TOOLS_DIR, f"{toolkit_id}.py")

    if not os.path.exists(toolkit_path):
        tool = Tools.get_tool_by_id(toolkit_id)
        if tool:
            with open(toolkit_path, "w") as file:
                file.write(tool.content)
        else:
            raise Exception(f"Toolkit not found: {toolkit_id}")

    spec = util.spec_from_file_location(toolkit_id, toolkit_path)
    module = util.module_from_spec(spec)
    frontmatter = extract_frontmatter(toolkit_path)

    try:
        install_frontmatter_requirements(frontmatter.get("requirements", ""))
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

    if not os.path.exists(function_path):
        function = Functions.get_function_by_id(function_id)
        if function:
            with open(function_path, "w") as file:
                file.write(function.content)
        else:
            raise Exception(f"Function not found: {function_id}")

    spec = util.spec_from_file_location(function_id, function_path)
    module = util.module_from_spec(spec)
    frontmatter = extract_frontmatter(function_path)

    try:
        install_frontmatter_requirements(frontmatter.get("requirements", ""))
        spec.loader.exec_module(module)
        print(f"Loaded module: {module.__name__}")
        if hasattr(module, "Pipe"):
            return module.Pipe(), "pipe", frontmatter
        elif hasattr(module, "Filter"):
            return module.Filter(), "filter", frontmatter
        elif hasattr(module, "Action"):
            return module.Action(), "action", frontmatter
        else:
            raise Exception("No Function class found")
    except Exception as e:
        print(f"Error loading module: {function_id}")
        # Move the file to the error folder
        os.rename(function_path, f"{function_path}.error")
        raise e


def install_frontmatter_requirements(requirements):
    if requirements:
        req_list = [req.strip() for req in requirements.split(",")]
        for req in req_list:
            print(f"Installing requirement: {req}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", req])
    else:
        print("No requirements found in frontmatter.")
