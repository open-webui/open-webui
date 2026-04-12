from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestNotes(AbstractPostgresTest):
    BASE_PATH = '/api/v1/notes'

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.notes import Notes
        from open_webui.models.users import Users

        cls.notes = Notes
        cls.users = Users

    def setup_method(self):
        super().setup_method()
        self.users.insert_new_user(
            id='user-1',
            name='Alice',
            email='alice@openwebui.com',
            profile_image_url='/alice.png',
            role='user',
        )
        self.users.insert_new_user(
            id='user-2',
            name='Bob',
            email='bob@openwebui.com',
            profile_image_url='/bob.png',
            role='user',
        )

    # ──────────────────────────────────────────────
    # Create
    # ──────────────────────────────────────────────

    def test_create_note(self):
        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'My First Note', 'data': {'content': {'md': 'Hello world'}}},
            )
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'My First Note'
        assert data['user_id'] == 'user-1'
        assert data['id'] is not None

    def test_create_note_without_notes_permission_returns_401(self):
        # Disable the notes feature for regular users via app config
        from open_webui.main import app

        original = app.state.config.USER_PERMISSIONS.get('features', {}).get('notes', True)
        app.state.config.USER_PERMISSIONS.setdefault('features', {})['notes'] = False
        try:
            with mock_webui_user(id='user-1'):
                response = self.fast_api_client.post(
                    self.create_url('/create'),
                    json={'title': 'Forbidden Note'},
                )
            assert response.status_code == 401
        finally:
            app.state.config.USER_PERMISSIONS['features']['notes'] = original

    # ──────────────────────────────────────────────
    # Get by ID
    # ──────────────────────────────────────────────

    def test_get_note_by_id(self):
        with mock_webui_user(id='user-1'):
            create_resp = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Fetch Me', 'data': {'content': {'md': 'content'}}},
            )
        note_id = create_resp.json()['id']

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url(f'/{note_id}'))
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == note_id
        assert data['title'] == 'Fetch Me'
        assert data['write_access'] is True

    def test_get_note_by_id_not_found(self):
        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url('/nonexistent-id'))
        assert response.status_code == 404

    def test_get_note_by_id_other_user_forbidden(self):
        """A note owner's note is not visible to an unrelated user."""
        with mock_webui_user(id='user-1'):
            create_resp = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Private Note'},
            )
        note_id = create_resp.json()['id']

        with mock_webui_user(id='user-2'):
            response = self.fast_api_client.get(self.create_url(f'/{note_id}'))
        assert response.status_code == 403

    # ──────────────────────────────────────────────
    # List / GET /
    # ──────────────────────────────────────────────

    def test_get_notes_empty(self):
        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url('/'))
        assert response.status_code == 200
        assert response.json() == []

    def test_get_notes_returns_own_notes(self):
        with mock_webui_user(id='user-1'):
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Note A'},
            )
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Note B'},
            )

        with mock_webui_user(id='user-2'):
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': "Bob's note"},
            )

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url('/'))
        assert response.status_code == 200
        titles = [n['title'] for n in response.json()]
        assert 'Note A' in titles
        assert 'Note B' in titles
        assert "Bob's note" not in titles

    # ──────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────

    def test_search_notes_single_word(self):
        with mock_webui_user(id='user-1'):
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Shopping list', 'data': {'content': {'md': 'Buy apples'}}},
            )
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Work tasks', 'data': {'content': {'md': 'Finish report'}}},
            )

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url('/search'), params={'query': 'shopping'})
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == 'Shopping list'

    def test_search_notes_multi_word_query(self):
        """Multi-word queries are normalised (spaces stripped) before matching.

        'to do' should match a note titled 'to-do list' because the search
        normalises both sides by removing hyphens and spaces.
        """
        with mock_webui_user(id='user-1'):
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'to-do list', 'data': {'content': {'md': 'task one'}}},
            )
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'meeting notes', 'data': {'content': {'md': 'agenda'}}},
            )

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url('/search'), params={'query': 'to do'})
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == 'to-do list'

    def test_search_notes_by_content(self):
        with mock_webui_user(id='user-1'):
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Recipes', 'data': {'content': {'md': 'pasta carbonara ingredients'}}},
            )

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url('/search'), params={'query': 'carbonara'})
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == 'Recipes'

    def test_search_notes_no_results(self):
        with mock_webui_user(id='user-1'):
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Random note'},
            )

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url('/search'), params={'query': 'zzznomatch'})
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert data['items'] == []

    def test_search_notes_scoped_to_user(self):
        """Search must not return another user's private notes."""
        with mock_webui_user(id='user-1'):
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Alice secret'},
            )
        with mock_webui_user(id='user-2'):
            self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Bob secret'},
            )

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url('/search'), params={'query': 'secret'})
        assert response.status_code == 200
        data = response.json()
        titles = [item['title'] for item in data['items']]
        assert 'Alice secret' in titles
        assert 'Bob secret' not in titles

    # ──────────────────────────────────────────────
    # Update
    # ──────────────────────────────────────────────

    def test_update_note(self):
        with mock_webui_user(id='user-1'):
            create_resp = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Original Title', 'data': {'content': {'md': 'old content'}}},
            )
        note_id = create_resp.json()['id']

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.post(
                self.create_url(f'/{note_id}/update'),
                json={'title': 'Updated Title', 'data': {'content': {'md': 'new content'}}},
            )
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Updated Title'

    def test_update_note_by_other_user_forbidden(self):
        with mock_webui_user(id='user-1'):
            create_resp = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Alice note'},
            )
        note_id = create_resp.json()['id']

        with mock_webui_user(id='user-2'):
            response = self.fast_api_client.post(
                self.create_url(f'/{note_id}/update'),
                json={'title': 'Hijacked'},
            )
        assert response.status_code == 403

    def test_update_note_not_found(self):
        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.post(
                self.create_url('/nonexistent-id/update'),
                json={'title': 'Whatever'},
            )
        assert response.status_code == 404

    # ──────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────

    def test_delete_note(self):
        with mock_webui_user(id='user-1'):
            create_resp = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'To Be Deleted'},
            )
        note_id = create_resp.json()['id']

        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.delete(self.create_url(f'/{note_id}/delete'))
        assert response.status_code == 200
        assert response.json() is True

        # Confirm it's gone
        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.get(self.create_url(f'/{note_id}'))
        assert response.status_code == 404

    def test_delete_note_by_other_user_forbidden(self):
        with mock_webui_user(id='user-1'):
            create_resp = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'Protected'},
            )
        note_id = create_resp.json()['id']

        with mock_webui_user(id='user-2'):
            response = self.fast_api_client.delete(self.create_url(f'/{note_id}/delete'))
        assert response.status_code == 403

    def test_delete_note_not_found(self):
        with mock_webui_user(id='user-1'):
            response = self.fast_api_client.delete(self.create_url('/nonexistent-id/delete'))
        assert response.status_code == 404

    # ──────────────────────────────────────────────
    # Admin access
    # ──────────────────────────────────────────────

    def test_admin_can_get_any_note(self):
        with mock_webui_user(id='user-1'):
            create_resp = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'User note'},
            )
        note_id = create_resp.json()['id']

        with mock_webui_user(id='admin-1', role='admin'):
            response = self.fast_api_client.get(self.create_url(f'/{note_id}'))
        assert response.status_code == 200
        assert response.json()['id'] == note_id

    def test_admin_can_delete_any_note(self):
        with mock_webui_user(id='user-1'):
            create_resp = self.fast_api_client.post(
                self.create_url('/create'),
                json={'title': 'User note'},
            )
        note_id = create_resp.json()['id']

        with mock_webui_user(id='admin-1', role='admin'):
            response = self.fast_api_client.delete(self.create_url(f'/{note_id}/delete'))
        assert response.status_code == 200
        assert response.json() is True
