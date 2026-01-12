import unittest
import sys
import os

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from open_webui.models.chats import ChatTable

class TestChatIntegrity(unittest.TestCase):
    def setUp(self):
        self.chat_table = ChatTable()

    def test_valid_chat_history(self):
        """Test a simple, valid chat history (linear)"""
        chat_data = {
            "history": {
                "currentId": "msg2",
                "messages": {
                    "msg1": {
                        "id": "msg1",
                        "parentId": None,
                        "content": "Hello"
                    },
                    "msg2": {
                        "id": "msg2",
                        "parentId": "msg1",
                        "content": "Hi there"
                    }
                }
            }
        }
        self.assertTrue(self.chat_table.validate_chat_history(chat_data))

    def test_broken_chain(self):
        """Test a chat history with a missing parent"""
        chat_data = {
            "history": {
                "currentId": "msg2",
                "messages": {
                    "msg2": {
                        "id": "msg2",
                        "parentId": "msg1", # msg1 missing
                        "content": "Broken parent"
                    }
                }
            }
        }
        self.assertFalse(self.chat_table.validate_chat_history(chat_data))

    def test_cycle_detection(self):
        """Test a chat history with a cycle"""
        chat_data = {
            "history": {
                "currentId": "msg1",
                "messages": {
                    "msg1": {
                        "id": "msg1",
                        "parentId": "msg2",
                        "content": "Loop 1"
                    },
                    "msg2": {
                        "id": "msg2",
                        "parentId": "msg1",
                        "content": "Loop 2"
                    }
                }
            }
        }
        self.assertFalse(self.chat_table.validate_chat_history(chat_data))

    def test_self_reference(self):
        """Test a message that is its own parent"""
        chat_data = {
            "history": {
                "currentId": "msg1",
                "messages": {
                    "msg1": {
                        "id": "msg1",
                        "parentId": "msg1",
                        "content": "Self loop"
                    }
                }
            }
        }
        self.assertFalse(self.chat_table.validate_chat_history(chat_data))

    def test_missing_current_id(self):
        """Test history where currentId is pointing to nothing"""
        chat_data = {
            "history": {
                "currentId": "ghost_msg",
                "messages": {
                    "msg1": {
                        "id": "msg1",
                        "parentId": None,
                        "content": "I am here"
                    }
                }
            }
        }
        self.assertFalse(self.chat_table.validate_chat_history(chat_data))

    def test_empty_history(self):
        """Test empty history (should be valid)"""
        chat_data = {"history": {}}
        self.assertTrue(self.chat_table.validate_chat_history(chat_data))

    def test_branching_path(self):
        """Test complex branching path (valid)"""
        # msg1 -> msg2 -> msg3
        #      -> msg4
        chat_data = {
            "history": {
                "currentId": "msg3",
                "messages": {
                    "msg1": {"id": "msg1", "parentId": None, "content": "Root"},
                    "msg2": {"id": "msg2", "parentId": "msg1", "content": "Branch A"},
                    "msg3": {"id": "msg3", "parentId": "msg2", "content": "Leaf A"},
                    "msg4": {"id": "msg4", "parentId": "msg1", "content": "Leaf B"}
                }
            }
        }
        self.assertTrue(self.chat_table.validate_chat_history(chat_data))

if __name__ == '__main__':
    unittest.main()
