import ast
import unittest
from pathlib import Path


ROUTER_PATH = Path(__file__).resolve().parents[4] / "routers" / "files.py"


def get_list_files_node() -> ast.AsyncFunctionDef:
    tree = ast.parse(ROUTER_PATH.read_text())
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "list_files":
            return node
    raise AssertionError("list_files not found")


class TestListFilesPaginationRegression(unittest.TestCase):
    def test_list_files_exposes_skip_and_limit_query_params(self):
        list_files = get_list_files_node()
        arg_names = [arg.arg for arg in list_files.args.args]

        self.assertIn("skip", arg_names)
        self.assertIn("limit", arg_names)

        defaults = {
            arg.arg: ast.unparse(default)
            for arg, default in zip(
                list_files.args.args[-len(list_files.args.defaults) :],
                list_files.args.defaults,
            )
        }
        self.assertIn("Query(0", defaults["skip"])
        self.assertIn("Query(100", defaults["limit"])

    def test_list_files_uses_paginated_search_query(self):
        list_files = get_list_files_node()

        search_calls = [
            node
            for node in ast.walk(list_files)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "Files"
            and node.func.attr == "search_files"
        ]
        self.assertEqual(len(search_calls), 1)

        call = search_calls[0]
        keywords = {
            keyword.arg: ast.unparse(keyword.value) for keyword in call.keywords
        }

        self.assertEqual(keywords["filename"], "'*'")
        self.assertEqual(keywords["skip"], "skip")
        self.assertEqual(keywords["limit"], "limit")
        self.assertEqual(keywords["db"], "db")

    def test_list_files_no_longer_uses_full_table_helpers(self):
        list_files = get_list_files_node()
        old_calls = [
            node.func.attr
            for node in ast.walk(list_files)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "Files"
            and node.func.attr in {"get_files", "get_files_by_user_id"}
        ]

        self.assertEqual(old_calls, [])


if __name__ == "__main__":
    unittest.main()
