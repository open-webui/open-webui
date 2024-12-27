import os
import re
import subprocess
import sys
import venv
from importlib import util
import types
import tempfile
import logging
import json
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

        # Write a wrapper to import and instantiate the class
        with open(temp_file.name, "a", encoding="utf-8") as f:
            f.write("\n\n# Auto-generated wrapper code\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    import json\n")
            f.write("    tool = Tools()\n")
            f.write("    print('TOOL_INSTANCE=' + json.dumps({\n")
            f.write("        'methods': [m for m in dir(tool) if not m.startswith('_')],\n")
            f.write("        'doc': tool.__doc__ or ''\n")
            f.write("    }))\n")

        # Execute in the venv and capture output
        result = subprocess.run(
            [python_path, temp_file.name],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the output to get tool instance info
        for line in result.stdout.splitlines():
            if line.startswith('TOOL_INSTANCE='):
                tool_info = json.loads(line.replace('TOOL_INSTANCE=', ''))
                break
        else:
            raise Exception("Failed to instantiate Tools class in venv")

        # Create a proxy object that will execute methods in the venv
        class ToolProxy:
            def __init__(self, python_path, temp_file_path, methods):
                self._python_path = python_path
                self._temp_file_path = temp_file_path
                self._methods = methods
                self.__doc__ = tool_info['doc']

            def __getattr__(self, name):
                if name not in self._methods:
                    raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
                
                def method_proxy(*args, **kwargs):
                    # Write a temporary runner that calls the specific method
                    with open(self._temp_file_path, "a", encoding="utf-8") as f:
                        f.write(f"\n\ntool = Tools()\n")
                        f.write(f"result = tool.{name}(*{args}, **{kwargs})\n")
                        f.write("print('RESULT=' + json.dumps(result))\n")
                    
                    # Execute in venv
                    proc_result = subprocess.run(
                        [self._python_path, self._temp_file_path],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Parse result
                    for line in proc_result.stdout.splitlines():
                        if line.startswith('RESULT='):
                            return json.loads(line.replace('RESULT=', ''))
                    raise Exception(f"Method {name} execution failed")
                
                return method_proxy

        proxy = ToolProxy(python_path, temp_file.name, tool_info['methods'])
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

        # Determine which class to use
        class_types = ['Pipe', 'Filter', 'Action']
        class_name = None
        
        # Write a wrapper to detect and instantiate the correct class
        with open(temp_file.name, "a", encoding="utf-8") as f:
            f.write("\n\n# Auto-generated wrapper code\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    import json\n")
            for cls in class_types:
                f.write(f"    if '{cls}' in globals():\n")
                f.write(f"        instance = {cls}()\n")
                f.write(f"        print('FUNCTION_INSTANCE=' + json.dumps({{\n")
                f.write(f"            'type': '{cls.lower()}',\n")
                f.write("            'methods': [m for m in dir(instance) if not m.startswith('_')],\n")
                f.write("            'doc': instance.__doc__ or ''\n")
                f.write("        }))\n")
                f.write("        break\n")

        # Execute in the venv and capture output
        result = subprocess.run(
            [python_path, temp_file.name],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the output to get function instance info
        for line in result.stdout.splitlines():
            if line.startswith('FUNCTION_INSTANCE='):
                func_info = json.loads(line.replace('FUNCTION_INSTANCE=', ''))
                break
        else:
            raise Exception("Failed to instantiate Function class in venv")

        # Create a proxy object that will execute methods in the venv
        class FunctionProxy:
            def __init__(self, python_path, temp_file_path, func_type, methods):
                self._python_path = python_path
                self._temp_file_path = temp_file_path
                self._type = func_type
                self._methods = methods
                self.__doc__ = func_info['doc']

            def __getattr__(self, name):
                if name not in self._methods:
                    raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
                
                def method_proxy(*args, **kwargs):
                    # Write a temporary runner that calls the specific method
                    with open(self._temp_file_path, "a", encoding="utf-8") as f:
                        f.write(f"\n\ninstance = {self._type.capitalize()}()\n")
                        f.write(f"result = instance.{name}(*{args}, **{kwargs})\n")
                        f.write("print('RESULT=' + json.dumps(result))\n")
                    
                    # Execute in venv
                    proc_result = subprocess.run(
                        [self._python_path, self._temp_file_path],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Parse result
                    for line in proc_result.stdout.splitlines():
                        if line.startswith('RESULT='):
                            return json.loads(line.replace('RESULT=', ''))
                    raise Exception(f"Method {name} execution failed")
                
                return method_proxy

        proxy = FunctionProxy(python_path, temp_file.name, func_info['type'], func_info['methods'])
        return proxy, func_info['type'], frontmatter
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
