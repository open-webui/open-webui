import os
import re
import subprocess
import sys
import venv
from importlib import util
import types
import tempfile
import logging
from pathlib import Path

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.functions import Functions
from open_webui.models.tools import Tools

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def extract_frontmatter(content):
    """
    Extract frontmatter as a dictionary from the provided content string.
    """
    frontmatter = {}
    frontmatter_started = False
    frontmatter_ended = False
    frontmatter_pattern = re.compile(r"^\s*([a-z_]+):\s*(.*)\s*$", re.IGNORECASE)

    try:
        lines = content.splitlines()
        if len(lines) < 1 or lines[0].strip() != '"""':
            # The content doesn't start with triple quotes
            return {}

        frontmatter_started = True

        for line in lines[1:]:
            if '"""' in line:
                if frontmatter_started:
                    frontmatter_ended = True
                    break

            if frontmatter_started and not frontmatter_ended:
                match = frontmatter_pattern.match(line)
                if match:
                    key, value = match.groups()
                    frontmatter[key.strip()] = value.strip()

    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

    return frontmatter


def replace_imports(content):
    """
    Replace the import paths in the content.
    """
    replacements = {
        "from utils": "from open_webui.utils",
        "from apps": "from open_webui.apps",
        "from main": "from open_webui.main",
        "from config": "from open_webui.config",
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    return content


def load_tools_module_by_id(toolkit_id, content=None):

    if content is None:
        tool = Tools.get_tool_by_id(toolkit_id)
        if not tool:
            raise Exception(f"Toolkit not found: {toolkit_id}")

        content = tool.content

        content = replace_imports(content)
        Tools.update_tool_by_id(toolkit_id, {"content": content})
    else:
        frontmatter = extract_frontmatter(content)
        # Install required packages found within the frontmatter
        install_frontmatter_requirements(frontmatter.get("requirements", ""), toolkit_id)

    # Ensure venv exists
    venv_path = create_venv(toolkit_id)
    python_path = get_venv_python(venv_path)
    
    module_name = f"tool_{toolkit_id}"
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module

    # Create a temporary file for the module
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
    temp_file.close()
    try:
        with open(temp_file.name, "w", encoding="utf-8") as f:
            f.write(content)
        module.__dict__["__file__"] = temp_file.name

        # Execute the content using the venv's Python interpreter
        result = subprocess.run(
            [python_path, temp_file.name],
            capture_output=True,
            text=True,
            check=True
        )
        # Execute the content in the module namespace
        exec(content, module.__dict__)
        frontmatter = extract_frontmatter(content)
        log.info(f"Loaded module: {module.__name__}")

        # Create and return the object if the class 'Tools' is found in the module
        if hasattr(module, "Tools"):
            return module.Tools(), frontmatter
        else:
            raise Exception("No Tools class found in the module")
    except Exception as e:
        log.error(f"Error loading module: {toolkit_id}: {e}")
        del sys.modules[module_name]  # Clean up
        raise e
    finally:
        os.unlink(temp_file.name)


def load_function_module_by_id(function_id, content=None):
    if content is None:
        function = Functions.get_function_by_id(function_id)
        if not function:
            raise Exception(f"Function not found: {function_id}")
        content = function.content

        content = replace_imports(content)
        Functions.update_function_by_id(function_id, {"content": content})
    else:
        frontmatter = extract_frontmatter(content)
        install_frontmatter_requirements(frontmatter.get("requirements", ""), function_id)

    # Ensure venv exists
    venv_path = create_venv(function_id)
    python_path = get_venv_python(venv_path)
    
    module_name = f"function_{function_id}"
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module

    # Create a temporary file for the module
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
    temp_file.close()
    try:
        with open(temp_file.name, "w", encoding="utf-8") as f:
            f.write(content)
        module.__dict__["__file__"] = temp_file.name

        # Execute the content using the venv's Python interpreter
        result = subprocess.run(
            [python_path, temp_file.name],
            capture_output=True,
            text=True,
            check=True
        )
        # Execute the content in the module namespace
        exec(content, module.__dict__)
        frontmatter = extract_frontmatter(content)
        log.info(f"Loaded module: {module.__name__}")

        # Create appropriate object based on available class type in the module
        if hasattr(module, "Pipe"):
            return module.Pipe(), "pipe", frontmatter
        elif hasattr(module, "Filter"):
            return module.Filter(), "filter", frontmatter
        elif hasattr(module, "Action"):
            return module.Action(), "action", frontmatter
        else:
            raise Exception("No Function class found in the module")
    except Exception as e:
        log.error(f"Error loading module: {function_id}: {e}")
        del sys.modules[module_name]  # Cleanup by removing the module in case of error

        Functions.update_function_by_id(function_id, {"is_active": False})
        raise e
    finally:
        os.unlink(temp_file.name)


def get_venv_path(module_id):
    """Get the path to the virtual environment for a specific module"""
    log.info("Invoked get_venv_path")
    venv_base = Path(tempfile.gettempdir()) / "open-webui-venvs"
    return venv_base / f"venv_{module_id}"

def create_venv(module_id):
    """Create a virtual environment for a specific module"""
    venv_path = get_venv_path(module_id)
    log.info(f"Invoked create_venv @ {venv_path}")
    if not venv_path.exists():
        venv.create(venv_path, with_pip=True)
    return venv_path

def get_venv_python(venv_path):
    """Get the Python executable path from the virtual environment"""
    log.info(f"Invoked get_venv_python for {sys.platform}")
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"
    return str(python_path)

def install_frontmatter_requirements(requirements, module_id):
    """Install requirements in the module's virtual environment"""
    log.info(f"install_frontmatter_requirements @ {module_id}")
    if requirements:
        log.info(f"Installing requirements {requirements}")
        venv_path = create_venv(module_id)
        python_path = get_venv_python(venv_path)
        log.info(f"venv_path {venv_path}, python_path {python_path}")
        req_list = [req.strip() for req in requirements.split(",")]
        
        for req in req_list:
            log.info(f"Installing requirement in venv: {req}")
            subprocess.check_call([python_path, "-m", "pip", "install", req])
    else:
        log.info("No requirements found in frontmatter.")
