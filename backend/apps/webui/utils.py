from importlib import util
import os

from config import TOOLS_DIR


def load_toolkit_module_by_id(toolkit_id):
    toolkit_path = os.path.join(TOOLS_DIR, f"{toolkit_id}.py")
    spec = util.spec_from_file_location(toolkit_id, toolkit_path)
    module = util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
        print(f"Loaded module: {module.__name__}")
        if hasattr(module, "Tools"):
            return module.Tools()
        else:
            raise Exception("No Tools class found")
    except Exception as e:
        print(f"Error loading module: {toolkit_id}")
        # Move the file to the error folder
        os.rename(toolkit_path, f"{toolkit_path}.error")
        raise e
