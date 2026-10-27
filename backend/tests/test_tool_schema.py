import copy
import importlib
import os
import unittest

from jsonschema import Draft202012Validator
from open_webui.tools.builtin import create_skill, update_skill_files

tools = importlib.import_module(os.environ.get('TOOL_SCHEMA_MODULE', 'open_webui.utils.tools'))


class ToolSchemaCompatibilityTests(unittest.TestCase):
    def test_skill_encoding_remains_base64_only(self):
        for function, field in ((create_skill, 'files'), (update_skill_files, 'operations')):
            with self.subTest(tool=function.__name__):
                spec = tools.get_builtin_tool_spec(function)
                encoding = spec['parameters']['properties'][field]['items']['properties']['encoding']
                self.assertNotIn('const', encoding)
                self.assertEqual(encoding['enum'], ['base64'])
                validator = Draft202012Validator(encoding)
                self.assertTrue(validator.is_valid('base64'))
                self.assertFalse(validator.is_valid('utf-8'))

    def test_schema_containers_are_visited_without_altering_data(self):
        schema = {
            'properties': {'const': {'const': 'literal property'}, 'nested': {'items': {'const': 'base64'}}},
            '$defs': {'choice': {'oneOf': [{'const': 'a'}, {'const': 'b'}]}},
            'additionalProperties': {'const': 'extra'},
            'default': {'const': 'example data'},
            'examples': [{'const': 'more data'}],
        }
        tools._normalize_schema_constants(schema)
        self.assertEqual(schema['properties']['const']['enum'], ['literal property'])
        self.assertEqual(schema['properties']['nested']['items']['enum'], ['base64'])
        self.assertEqual(schema['$defs']['choice']['oneOf'][1]['enum'], ['b'])
        self.assertEqual(schema['additionalProperties']['enum'], ['extra'])
        self.assertEqual(schema['default'], {'const': 'example data'})
        self.assertEqual(schema['examples'], [{'const': 'more data'}])

    def test_constraint_semantics_are_preserved(self):
        for value in ['base64', 0, False, None, {'const': True}, [1, False]]:
            with self.subTest(value=value):
                original = {'const': value}
                normalized = copy.deepcopy(original)
                tools._normalize_schema_constants(normalized)
                before, after = Draft202012Validator(original), Draft202012Validator(normalized)
                for candidate in ['base64', 'utf-8', 0, 1, False, True, None, {'const': True}, [1, False]]:
                    self.assertEqual(before.is_valid(candidate), after.is_valid(candidate))

    def test_existing_enum_is_not_weakened(self):
        schema = {'const': True, 'enum': [1, False]}
        tools._normalize_schema_constants(schema)
        self.assertEqual(schema['enum'], [])
        schema = {'const': {'value': True}, 'enum': [{'value': 1}]}
        tools._normalize_schema_constants(schema)
        self.assertEqual(schema['enum'], [])

    def test_cleaning_does_not_mutate_shared_specs(self):
        spec = {
            'name': 'sample',
            'parameters': {'type': 'object', 'properties': {'encoding': {'type': 'string', 'const': 'base64'}}},
        }
        original = copy.deepcopy(spec)
        cleaned = tools.clean_openai_tool_schema(spec)
        self.assertEqual(spec, original)
        self.assertEqual(cleaned['parameters']['properties']['encoding']['enum'], ['base64'])


if __name__ == '__main__':
    unittest.main()
