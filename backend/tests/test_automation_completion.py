import unittest
from unittest.mock import patch

from open_webui.utils import automations


class FinalMessageTests(unittest.TestCase):
    def test_accepts_visible_text(self):
        message = {
            'output': [
                {'type': 'reasoning', 'content': [{'type': 'output_text', 'text': 'thinking'}]},
                {'type': 'message', 'content': [{'type': 'output_text', 'text': 'done'}]},
            ]
        }

        self.assertTrue(automations._has_final_assistant_message(message))

    def test_rejects_non_final_output(self):
        cases = [
            {'output': [{'type': 'reasoning', 'content': [{'type': 'output_text', 'text': 'thinking'}]}]},
            {'output': [{'type': 'message', 'content': []}]},
            {'output': None},
        ]

        for message in cases:
            with self.subTest(message=message):
                self.assertFalse(automations._has_final_assistant_message(message))


class CompletionWaitTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_final_message(self):
        message = {
            'done': True,
            'error': None,
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'done'}]}],
        }

        async def get_message(chat_id, message_id):
            return message

        with patch.object(automations.Chats, 'get_message_by_id_and_message_id', get_message):
            self.assertEqual(
                await automations._wait_for_automation_completion('chat', 'message'),
                message,
            )

    async def test_rejects_reasoning_only(self):
        async def get_message(chat_id, message_id):
            return {'done': True, 'error': None, 'output': [{'type': 'reasoning', 'content': []}]}

        with patch.object(automations.Chats, 'get_message_by_id_and_message_id', get_message):
            with self.assertRaisesRegex(RuntimeError, 'without a final assistant message'):
                await automations._wait_for_automation_completion('chat', 'message')

    async def test_propagates_stored_error(self):
        async def get_message(chat_id, message_id):
            return {'done': True, 'error': {'message': 'tool failed'}, 'output': []}

        with patch.object(automations.Chats, 'get_message_by_id_and_message_id', get_message):
            with self.assertRaisesRegex(RuntimeError, 'tool failed'):
                await automations._wait_for_automation_completion('chat', 'message')


if __name__ == '__main__':
    unittest.main()
