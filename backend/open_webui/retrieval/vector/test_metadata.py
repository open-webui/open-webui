import unittest
import sys
import os

# Set up python search path to import backend modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from open_webui.retrieval.vector.utils import process_metadata

class TestProcessMetadata(unittest.TestCase):
    def test_none_metadata(self):
        self.assertEqual(process_metadata(None), {})

    def test_non_dict_metadata(self):
        self.assertEqual(process_metadata("not-a-dict"), {})
        self.assertEqual(process_metadata(123), {})

    def test_empty_metadata(self):
        self.assertEqual(process_metadata({}), {})

    def test_valid_primitives(self):
        input_data = {
            "str_key": "valid string",
            "int_key": 42,
            "float_key": 3.14,
            "bool_key": True
        }
        # Primitives should be preserved in their native types (strings are sanitized)
        result = process_metadata(input_data)
        self.assertEqual(result["str_key"], "valid string")
        self.assertEqual(result["int_key"], 42)
        self.assertEqual(result["float_key"], 3.14)
        self.assertEqual(result["bool_key"], True)

    def test_excluded_keys(self):
        input_data = {
            "content": "some text content",
            "pages": 100,
            "valid_key": "keep me"
        }
        result = process_metadata(input_data)
        self.assertNotIn("content", result)
        self.assertNotIn("pages", result)
        self.assertEqual(result["valid_key"], "keep me")

    def test_none_values(self):
        input_data = {
            "none_key": None,
            "valid_key": "value"
        }
        result = process_metadata(input_data)
        self.assertNotIn("none_key", result)
        self.assertEqual(result["valid_key"], "value")

    def test_complex_types(self):
        import datetime
        dt = datetime.datetime(2026, 7, 21, 12, 0, 0)
        
        input_data = {
            "list_key": [1, 2, 3],
            "dict_key": {"nested": "value"},
            "tuple_key": (4, 5),
            "set_key": {6, 7},
            "datetime_key": dt
        }
        result = process_metadata(input_data)
        
        # All complex types should be coerced into string representations
        self.assertEqual(result["list_key"], "[1, 2, 3]")
        self.assertEqual(result["dict_key"], "{'nested': 'value'}")
        self.assertEqual(result["tuple_key"], "(4, 5)")
        # Set representation string ordering can vary, verify it converts to string and contains elements
        self.assertTrue(isinstance(result["set_key"], str))
        self.assertTrue("6" in result["set_key"] and "7" in result["set_key"])
        self.assertEqual(result["datetime_key"], str(dt))

    def test_null_byte_sanitization(self):
        input_data = {
            "dirty_str": "hello\x00world",
            "dirty_list": ["a\x00b"]
        }
        result = process_metadata(input_data)
        
        self.assertEqual(result["dirty_str"], "helloworld")
        # List becomes a string, and null bytes are sanitized inside it
        self.assertEqual(result["dirty_list"], "['a\\x00b']")  # str(['a\x00b']) is "['a\x00b']" which doesn't have literal \x00 but escaped string

if __name__ == '__main__':
    unittest.main()
