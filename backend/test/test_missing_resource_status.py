import ast
from pathlib import Path


ROUTERS = Path(__file__).parents[1] / 'open_webui' / 'routers'


def test_missing_resources_use_not_found_status() -> None:
    for router_name in ('functions.py', 'tools.py', 'models.py'):
        tree = ast.parse((ROUTERS / router_name).read_text(encoding='utf-8'))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != 'HTTPException':
                continue

            detail = next(
                (keyword.value for keyword in node.keywords if keyword.arg == 'detail'),
                None,
            )
            if detail is None or ast.unparse(detail) != 'ERROR_MESSAGES.NOT_FOUND':
                continue

            status_code = next(
                (keyword.value for keyword in node.keywords if keyword.arg == 'status_code'),
                node.args[0] if node.args else None,
            )
            assert ast.unparse(status_code) == 'status.HTTP_404_NOT_FOUND', (
                f'{router_name}:{node.lineno} uses {ast.unparse(status_code)} ' 'for a missing resource'
            )
