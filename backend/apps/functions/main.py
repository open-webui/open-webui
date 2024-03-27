from pathlib import Path
import ast
import builtins


from fastapi import (
    FastAPI,
    Request,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)

from fastapi.middleware.cors import CORSMiddleware
from apps.functions.security import ALLOWED_MODULES, ALLOWED_BUILTINS, custom_import
from utils.utils import get_current_user, get_admin_user


from config import FUNCTIONS_DIR
from constants import ERROR_MESSAGES


from pydantic import BaseModel

from typing import Optional

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get_status():
    return {"status": True}


class FunctionForm(BaseModel):
    name: str
    content: str


@app.post("/add")
def add_function(
    form_data: FunctionForm,
    user=Depends(get_admin_user),
):
    try:
        filename = f"{FUNCTIONS_DIR}/{form_data.name}.py"
        if not Path(filename).exists():
            with open(filename, "w") as file:
                file.write(form_data.content)
            return f"{form_data.name}.py" in list(
                map(lambda x: x.name, Path(FUNCTIONS_DIR).rglob("./*"))
            )
        else:
            raise Exception("Function already exists")
    except Exception as e:
        print(e)
        return False


@app.post("/update")
def update_function(
    form_data: FunctionForm,
    user=Depends(get_admin_user),
):
    try:
        filename = f"{FUNCTIONS_DIR}/{form_data.name}.py"
        if Path(filename).exists():
            with open(filename, "w") as file:
                file.write(form_data.content)
            return f"{form_data.name}.py" in list(
                map(lambda x: x.name, Path(FUNCTIONS_DIR).rglob("./*"))
            )
        else:
            raise Exception("Function does not exist")
    except Exception as e:
        print(e)
        return False


@app.get("/check/{function}")
def check_function(
    function: str,
    user=Depends(get_admin_user),
):
    filename = f"{FUNCTIONS_DIR}/{function}.py"

    # Check if the function file exists
    if not Path(filename).is_file():
        raise HTTPException(status_code=404, detail="Function not found")

    # Read the code from the file
    with open(filename, "r") as file:
        code = file.read()

    return {"name": function, "content": code}


@app.get("/list")
def list_functions(
    user=Depends(get_admin_user),
):
    files = list(map(lambda x: x.name, Path(FUNCTIONS_DIR).rglob("./*")))
    return files


def validate_imports(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Syntax error in function: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            module_names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module_names = [node.module]
        else:
            continue

        for name in module_names:
            if name not in ALLOWED_MODULES:
                raise HTTPException(
                    status_code=400, detail=f"Import of module {name} is not allowed"
                )


@app.post("/exec/{function}")
def exec_function(
    function: str,
    kwargs: Optional[dict] = None,
    user=Depends(get_current_user),
):
    filename = f"{FUNCTIONS_DIR}/{function}.py"

    # Check if the function file exists
    if not Path(filename).is_file():
        raise HTTPException(status_code=404, detail="Function not found")

    # Read the code from the file
    with open(filename, "r") as file:
        code = file.read()

    validate_imports(code)

    try:
        # Execute the code within a restricted namespace
        namespace = {name: getattr(builtins, name) for name in ALLOWED_BUILTINS}
        namespace["__import__"] = custom_import
        exec(code, namespace)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Function: {e}")

    # Check if the function exists in the namespace
    if "main" not in namespace or not callable(namespace["main"]):
        raise HTTPException(status_code=400, detail="Invalid function")

    try:
        # Execute the function with provided kwargs
        result = namespace["main"](kwargs) if kwargs else namespace["main"]()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Function: {e}")
