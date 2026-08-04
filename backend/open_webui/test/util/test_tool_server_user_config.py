from types import SimpleNamespace

import pytest

from open_webui.models.tool_servers import (
    get_user_configs_from_settings,
    settings_without_user_configs,
)
from open_webui.utils.headers import (
    get_user_secret_slots,
    interpolate_user_secrets_in_url,
    parse_custom_headers,
)
from open_webui.utils.tools import (
    ToolServerUserConfigRequiredError,
    build_tool_server_headers,
    drop_reserved_user_secret_headers,
    get_missing_user_config_slots,
    get_tool_server_user_config_schema,
    get_user_config_flags,
    mask_user_config_values,
    validate_tool_server_user_config,
    validate_user_config_value,
)
from open_webui.utils.valves import decrypt_valves, encrypt_valves


def make_user(user_id='user-1', configs=None):
    """A user model stand-in carrying the settings the request path reads from."""
    return SimpleNamespace(
        id=user_id,
        name='Test User',
        email='test@example.com',
        role='user',
        settings={'tool_servers': {'user_config': configs or {}}},
    )


USER = make_user()


class TestUserSecretPlaceholders:
    """{{USER_SECRET:<slot>}} interpolation in connection headers."""

    def test_arbitrary_header_names_and_templates(self):
        headers = parse_custom_headers(
            {
                'Authorization': 'Bearer {{USER_SECRET:token}}',
                'X-API-Key': '{{USER_SECRET:api_key}}',
                'X-Auth': 'Basic {{USER_SECRET:basic}}',
            },
            user=USER,
            user_secrets={'token': 'tok', 'api_key': 'key', 'basic': 'dXNlcjpwdw=='},
        )

        assert headers == {
            'Authorization': 'Bearer tok',
            'X-API-Key': 'key',
            'X-Auth': 'Basic dXNlcjpwdw==',
        }

    def test_multiple_slots_in_a_single_value(self):
        headers = parse_custom_headers(
            {'X-Account': '{{USER_SECRET:workspace}}/{{USER_SECRET:login}}'},
            user=USER,
            user_secrets={'workspace': 'acme', 'login': 'jane'},
        )

        assert headers == {'X-Account': 'acme/jane'}

    def test_the_same_slot_can_feed_several_headers(self):
        headers = parse_custom_headers(
            {
                'Authorization': 'Bearer {{USER_SECRET:token}}',
                'X-Legacy-Token': '{{USER_SECRET:token}}',
            },
            user=USER,
            user_secrets={'token': 'tok'},
        )

        assert headers == {'Authorization': 'Bearer tok', 'X-Legacy-Token': 'tok'}

    def test_placeholders_are_resolved_anywhere_in_the_value(self):
        headers = parse_custom_headers(
            {
                'X-Prefixed': 'prefix-{{USER_SECRET:a}}',
                'X-Suffixed': '{{USER_SECRET:a}}-suffix',
                'X-Embedded': 'a={{USER_SECRET:a}};b={{USER_SECRET:b}};c={{USER_SECRET:c}}',
            },
            user=USER,
            user_secrets={'a': '1', 'b': '2', 'c': '3'},
        )

        assert headers == {
            'X-Prefixed': 'prefix-1',
            'X-Suffixed': '1-suffix',
            'X-Embedded': 'a=1;b=2;c=3',
        }

    def test_identity_placeholders_still_interpolate(self):
        headers = parse_custom_headers(
            {'X-Mixed': '{{USER_EMAIL}}:{{USER_SECRET:api_key}}'},
            user=USER,
            user_secrets={'api_key': 'secret'},
        )

        assert headers == {'X-Mixed': 'test@example.com:secret'}

    def test_secret_values_are_not_expanded_again(self):
        headers = parse_custom_headers(
            {'X-API-Key': '{{USER_SECRET:api_key}}'},
            user=USER,
            user_secrets={'api_key': '{{USER_EMAIL}}'},
        )

        assert headers == {'X-API-Key': '{{USER_EMAIL}}'}

    def test_falsy_values_are_kept(self):
        headers = parse_custom_headers(
            {'X-Count': '{{USER_SECRET:count}}', 'X-Flag': '{{USER_SECRET:flag}}'},
            user=USER,
            user_secrets={'count': 0, 'flag': False},
        )

        assert headers == {'X-Count': '0', 'X-Flag': 'False'}

    def test_headers_with_an_unset_slot_are_dropped(self):
        headers = parse_custom_headers(
            {'Authorization': 'Bearer {{USER_SECRET:api_key}}', 'X-Static': 'kept'},
            user=USER,
            user_secrets={},
        )

        assert headers == {'X-Static': 'kept'}

    def test_slots_are_collected_from_a_template(self):
        assert get_user_secret_slots('Bearer {{USER_SECRET:token}}') == {'token'}
        assert get_user_secret_slots('{{USER_SECRET:workspace}}/{{USER_SECRET:login}}') == {
            'workspace',
            'login',
        }
        assert get_user_secret_slots('nothing here') == set()
        assert get_user_secret_slots(None) == set()


class TestUrlPlaceholders:
    def test_secrets_are_percent_encoded_in_the_url(self):
        url = interpolate_user_secrets_in_url(
            'https://mcp.example.com/{{USER_SECRET:api_key}}/mcp',
            {'api_key': 'a/b c'},
        )

        assert url == 'https://mcp.example.com/a%2Fb%20c/mcp'

    def test_urls_without_placeholders_are_untouched(self):
        assert interpolate_user_secrets_in_url('https://mcp.example.com/mcp', {'a': '1'}) == (
            'https://mcp.example.com/mcp'
        )


class TestReservedHeaders:
    def test_reserved_headers_are_dropped_at_resolve_time(self):
        # Connections can also come from TOOL_SERVER_CONNECTIONS, bypassing validation.
        headers = drop_reserved_user_secret_headers(
            {
                'X-OpenWebUI-User-Email': '{{USER_SECRET:key}}',
                'Host': '{{USER_SECRET:key}}',
                'X-OpenWebUI-User-Email-Suffix': 'kept',
                'X-API-Key': '{{USER_SECRET:key}}',
            }
        )

        assert set(headers) == {'X-OpenWebUI-User-Email-Suffix', 'X-API-Key'}

    def test_headers_without_secrets_are_left_alone(self):
        headers = {'Host': 'example.com', 'Cookie': 'a=b'}

        assert drop_reserved_user_secret_headers(headers) == headers


class TestUserConfigSchema:
    def test_no_schema_when_nothing_is_declared(self):
        assert get_tool_server_user_config_schema({'type': 'mcp', 'auth_type': 'bearer'}) is None

    def test_user_key_auth_type_declares_an_implicit_password_slot(self):
        schema = get_tool_server_user_config_schema({'type': 'mcp', 'auth_type': 'user_key'})

        assert schema['required'] == ['key']
        assert schema['properties']['key']['input']['type'] == 'password'

    def test_declared_slots_are_returned(self):
        schema = get_tool_server_user_config_schema(
            {
                'config': {
                    'user_config': {
                        'properties': {
                            'login': {'type': 'string', 'title': 'Login'},
                            'password': {'type': 'string', 'input': {'type': 'password'}},
                        },
                        'required': ['login', 'password'],
                    }
                }
            }
        )

        assert set(schema['properties']) == {'login', 'password'}
        assert schema['required'] == ['login', 'password']

    def test_a_missing_type_defaults_to_string(self):
        schema = get_tool_server_user_config_schema(
            {'config': {'user_config': {'properties': {'token': {'input': {'type': 'password'}}}}}}
        )

        assert schema['properties']['token']['type'] == 'string'

    def test_any_number_of_slots_can_be_declared(self):
        schema = get_tool_server_user_config_schema(
            {
                'auth_type': 'user_key',
                'config': {
                    'user_config': {
                        'properties': {
                            'region': {'type': 'string'},
                            'project': {'type': 'string'},
                            'webhook_secret': {'input': {'type': 'password'}},
                        },
                        'required': ['region'],
                    }
                },
            }
        )

        assert set(schema['properties']) == {'key', 'region', 'project', 'webhook_secret'}
        assert schema['required'] == ['key', 'region']

    def test_missing_required_slots_are_reported(self):
        connection = {'auth_type': 'user_key'}

        assert get_missing_user_config_slots(connection, {}) == ['key']
        assert get_missing_user_config_slots(connection, {'key': ''}) == ['key']
        assert get_missing_user_config_slots(connection, {'key': 'value'}) == []


class TestUserConfigFlags:
    """The flags GET /api/v1/tools/ reports for a connection: whether the user
    configured it, and whether it can be used as it stands."""

    OPTIONAL = {
        'info': {'id': 'tracker'},
        'config': {'user_config': {'properties': {'login': {}, 'project': {}}, 'required': []}},
    }
    REQUIRED = {
        'info': {'id': 'tracker'},
        'config': {'user_config': {'properties': {'login': {}, 'project': {}}, 'required': ['login']}},
    }

    def test_no_flags_when_the_connection_asks_for_nothing(self):
        assert get_user_config_flags({'info': {'id': 'tracker'}}, None) == {}

    def test_optional_slots_are_not_configured_until_the_user_saves_one(self):
        flags = get_user_config_flags(self.OPTIONAL, None)

        assert flags['requires_user_config'] is True
        assert flags['user_config_set'] is False
        # Nothing is required, so the tool is usable as it stands.
        assert flags['user_config_required_set'] is True

    def test_a_blank_value_does_not_count_as_saved(self):
        assert get_user_config_flags(self.OPTIONAL, {'login': ''})['user_config_set'] is False

    def test_saving_one_optional_slot_configures_the_connection(self):
        flags = get_user_config_flags(self.OPTIONAL, {'login': 'jane'})

        assert flags['user_config_set'] is True
        assert flags['user_config_required_set'] is True

    def test_values_for_undeclared_slots_are_ignored(self):
        assert get_user_config_flags(self.OPTIONAL, {'stale': 'value'})['user_config_set'] is False

    def test_a_required_slot_is_unset_until_it_is_filled_in(self):
        flags = get_user_config_flags(self.REQUIRED, {})

        assert flags['user_config_set'] is False
        assert flags['user_config_required_set'] is False

    def test_a_filled_required_slot_configures_the_connection(self):
        flags = get_user_config_flags(self.REQUIRED, {'login': 'jane'})

        assert flags['user_config_set'] is True
        assert flags['user_config_required_set'] is True

    def test_an_optional_slot_cannot_stand_in_for_a_required_one(self):
        flags = get_user_config_flags(self.REQUIRED, {'project': 'acme'})

        assert flags['user_config_set'] is False
        assert flags['user_config_required_set'] is False

    def test_the_implicit_user_key_slot_is_required(self):
        connection = {'info': {'id': 'tracker'}, 'auth_type': 'user_key'}

        assert get_user_config_flags(connection, None) == {
            'requires_user_config': True,
            'user_config_set': False,
            'user_config_required_set': False,
        }
        assert get_user_config_flags(connection, {'key': 'secret'}) == {
            'requires_user_config': True,
            'user_config_set': True,
            'user_config_required_set': True,
        }


class TestUserConfigValidation:
    def test_reserved_headers_cannot_carry_a_secret(self):
        with pytest.raises(ValueError):
            validate_tool_server_user_config(
                {
                    'auth_type': 'user_key',
                    'info': {'id': 'tracker'},
                    'headers': {'X-OpenWebUI-User-Email': '{{USER_SECRET:key}}'},
                }
            )

    def test_undeclared_slots_are_rejected(self):
        with pytest.raises(ValueError):
            validate_tool_server_user_config(
                {'info': {'id': 'tracker'}, 'headers': {'X-API-Key': '{{USER_SECRET:unknown}}'}}
            )

    def test_required_must_reference_declared_slots(self):
        with pytest.raises(ValueError):
            validate_tool_server_user_config(
                {
                    'info': {'id': 'tracker'},
                    'config': {'user_config': {'properties': {'a': {}}, 'required': ['b']}},
                }
            )

    def test_an_id_is_required_to_key_the_stored_values(self):
        # Without an ID the values could not be told apart from another connection's.
        with pytest.raises(ValueError):
            validate_tool_server_user_config({'type': 'openapi', 'auth_type': 'user_key'})

    def test_url_secrets_are_rejected_for_openapi_connections(self):
        with pytest.raises(ValueError):
            validate_tool_server_user_config(
                {
                    'type': 'openapi',
                    'auth_type': 'user_key',
                    'info': {'id': 'tracker'},
                    'url': 'https://example.com/{{USER_SECRET:key}}',
                }
            )

    def test_url_secrets_must_be_declared(self):
        with pytest.raises(ValueError):
            validate_tool_server_user_config(
                {
                    'type': 'mcp',
                    'info': {'id': 'tracker'},
                    'url': 'https://example.com/{{USER_SECRET:unknown}}',
                    'config': {'user_config': {'properties': {'known': {}}}},
                }
            )

    def test_valid_declaration_passes(self):
        validate_tool_server_user_config(
            {
                'type': 'mcp',
                'info': {'id': 'tracker'},
                'url': 'https://example.com/{{USER_SECRET:api_key}}',
                'config': {'user_config': {'properties': {'api_key': {}}, 'required': ['api_key']}},
                'headers': {'X-API-Key': '{{USER_SECRET:api_key}}'},
            }
        )


class TestValueValidation:
    def test_control_characters_are_rejected(self):
        # A newline would split the header or blow up inside the HTTP client.
        for value in ('a\r\nX-Injected: 1', 'a\nb', 'a\x00b'):
            with pytest.raises(ValueError):
                validate_user_config_value('key', value)

    def test_overlong_values_are_rejected(self):
        with pytest.raises(ValueError):
            validate_user_config_value('key', 'a' * 4097)

    def test_scalars_are_coerced_to_strings(self):
        assert validate_user_config_value('key', 42) == '42'

    def test_structured_values_are_rejected(self):
        with pytest.raises(ValueError):
            validate_user_config_value('key', {'a': 1})


class TestMasking:
    def test_password_slots_are_write_only(self):
        schema = {
            'properties': {
                'api_key': {'input': {'type': 'password'}},
                'workspace': {'type': 'string'},
            }
        }

        masked = mask_user_config_values(schema, {'api_key': 'super-secret', 'workspace': 'acme'})

        assert masked['api_key'] == {'set': True, 'sensitive': True}
        assert masked['workspace'] == {'set': True, 'sensitive': False, 'value': 'acme'}
        assert 'super-secret' not in str(masked)


class TestSettingsResponses:
    """The credentials live in user.settings, which several endpoints hand back."""

    SETTINGS = {
        'ui': {'theme': 'dark'},
        'tool_servers': {'user_config': {'tracker': {'key': 'super-secret'}}},
    }

    def test_credentials_are_stripped_from_the_settings(self):
        stripped = settings_without_user_configs(self.SETTINGS)

        assert stripped == {'ui': {'theme': 'dark'}}
        assert 'super-secret' not in str(stripped)

    def test_unrelated_tool_server_settings_survive(self):
        settings = {'tool_servers': {'other': 1, 'user_config': {'tracker': {'key': 'k'}}}}

        assert settings_without_user_configs(settings) == {'tool_servers': {'other': 1}}

    def test_settings_without_credentials_are_returned_unchanged(self):
        assert settings_without_user_configs({'ui': {}}) == {'ui': {}}
        assert settings_without_user_configs(None) is None

    def test_the_request_path_reads_the_stored_values(self):
        assert get_user_configs_from_settings(self.SETTINGS) == {'tracker': {'key': 'super-secret'}}
        assert get_user_configs_from_settings({'ui': {}}) == {}
        assert get_user_configs_from_settings(None) == {}


class TestStorage:
    """Storage follows the valves helper, encryption included — which is opt-in."""

    def test_values_are_encrypted_when_valve_encryption_is_enabled(self, monkeypatch):
        monkeypatch.setattr('open_webui.utils.valves.ENABLE_VALVE_ENCRYPTION', True)

        encrypted = encrypt_valves({'api_key': 'super-secret'})

        assert isinstance(encrypted, str)
        assert 'super-secret' not in encrypted
        assert decrypt_valves(encrypted) == {'api_key': 'super-secret'}

    def test_values_are_stored_as_submitted_by_default(self, monkeypatch):
        # ENABLE_VALVE_ENCRYPTION is off by default, and then these values are kept
        # the same way valves are: readable in the database.
        monkeypatch.setattr('open_webui.utils.valves.ENABLE_VALVE_ENCRYPTION', False)

        stored = encrypt_valves({'api_key': 'super-secret'})

        assert stored == {'api_key': 'super-secret'}
        assert decrypt_valves(stored) == {'api_key': 'super-secret'}


class TestBuildToolServerHeaders:
    @pytest.mark.asyncio
    async def test_user_key_auth_type_sends_the_users_own_bearer_token(self):
        connection = {'type': 'mcp', 'auth_type': 'user_key', 'info': {'id': 'tracker'}}
        user = make_user(configs={'tracker': {'key': 'personal-key'}})

        headers, _ = await build_tool_server_headers(connection, None, user, server_id='tracker')

        assert headers['Authorization'] == 'Bearer personal-key'

    @pytest.mark.asyncio
    async def test_declared_slots_are_interpolated_into_custom_headers(self):
        connection = {
            'type': 'mcp',
            'auth_type': 'none',
            'info': {'id': 'tracker'},
            'headers': {'X-Auth-Token': 'Token {{USER_SECRET:token}}', 'X-Login': '{{USER_SECRET:login}}'},
            'config': {
                'user_config': {
                    'properties': {'login': {}, 'token': {'input': {'type': 'password'}}},
                    'required': ['login', 'token'],
                }
            },
        }
        user = make_user(configs={'tracker': {'login': 'jane', 'token': 'tok'}})

        headers, _ = await build_tool_server_headers(connection, None, user, server_id='tracker')

        assert headers['X-Auth-Token'] == 'Token tok'
        assert headers['X-Login'] == 'jane'

    @pytest.mark.asyncio
    async def test_missing_credentials_raise_instead_of_sending_an_empty_header(self):
        connection = {'type': 'mcp', 'auth_type': 'user_key', 'info': {'id': 'tracker'}}

        with pytest.raises(ToolServerUserConfigRequiredError):
            await build_tool_server_headers(connection, None, make_user(), server_id='tracker')

    @pytest.mark.asyncio
    async def test_one_users_values_never_leak_into_another_users_request(self):
        connection = {'type': 'mcp', 'auth_type': 'user_key', 'info': {'id': 'tracker'}}
        first = make_user('user-1', {'tracker': {'key': 'user-1-key'}})
        second = make_user('user-2', {'tracker': {'key': 'user-2-key'}})

        first_headers, _ = await build_tool_server_headers(connection, None, first, server_id='tracker')
        second_headers, _ = await build_tool_server_headers(connection, None, second, server_id='tracker')

        assert first_headers['Authorization'] == 'Bearer user-1-key'
        assert second_headers['Authorization'] == 'Bearer user-2-key'

    @pytest.mark.asyncio
    async def test_values_stored_for_another_connection_are_not_used(self):
        connection = {'type': 'mcp', 'auth_type': 'user_key', 'info': {'id': 'tracker'}}
        user = make_user(configs={'other-server': {'key': 'someone-elses'}})

        with pytest.raises(ToolServerUserConfigRequiredError):
            await build_tool_server_headers(connection, None, user, server_id='tracker')

    @pytest.mark.asyncio
    async def test_reserved_headers_are_refused_even_when_stored_credentials_exist(self):
        connection = {
            'type': 'mcp',
            'auth_type': 'user_key',
            'info': {'id': 'tracker'},
            'headers': {'X-OpenWebUI-User-Email': '{{USER_SECRET:key}}'},
        }
        user = make_user(configs={'tracker': {'key': 'personal-key'}})

        headers, _ = await build_tool_server_headers(connection, None, user, server_id='tracker')

        assert 'X-OpenWebUI-User-Email' not in headers

    @pytest.mark.asyncio
    async def test_connections_without_user_config_are_untouched(self):
        connection = {'type': 'mcp', 'auth_type': 'bearer', 'key': 'global', 'info': {'id': 'plain'}}

        headers, _ = await build_tool_server_headers(connection, None, USER, server_id='plain')

        assert headers['Authorization'] == 'Bearer global'
