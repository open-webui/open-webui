from unittest import TestCase

from open_webui.utils.ask_user import normalize_ask_user_request


class TestNormalizeAskUserRequest(TestCase):
    @staticmethod
    def question(question_id=None, header='Course format', option_count=2):
        question = {
            'header': header,
            'question': 'How should the course be structured?',
            'options': [
                {'label': f'Option {index}', 'description': f'Description {index}'}
                for index in range(option_count)
            ],
        }
        if question_id is not None:
            question['id'] = question_id
        return question

    def test_preserves_explicit_id_format(self):
        normalized = normalize_ask_user_request(
            {'questions': [self.question('course.format')]}
        )

        self.assertEqual(normalized['questions'][0]['id'], 'course.format')

    def test_generates_non_content_id_and_resolves_collisions(self):
        normalized = normalize_ask_user_request(
            {
                'questions': [
                    self.question('question-2'),
                    self.question(header='Student background'),
                ]
            }
        )

        self.assertEqual(
            [question['id'] for question in normalized['questions']],
            ['question-2', 'question-2-2'],
        )
        self.assertNotIn('Student', normalized['questions'][1]['id'])

    def test_rejects_duplicate_explicit_ids(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate question id: same'):
            normalize_ask_user_request(
                {'questions': [self.question('same'), self.question('same')]}
            )

    def test_accepts_four_options_and_rejects_five(self):
        normalized = normalize_ask_user_request(
            {'questions': [self.question(option_count=4)]}
        )
        self.assertEqual(len(normalized['questions'][0]['options']), 4)

        with self.assertRaisesRegex(ValueError, 'requires 2-4 options'):
            normalize_ask_user_request(
                {'questions': [self.question(option_count=5)]}
            )
