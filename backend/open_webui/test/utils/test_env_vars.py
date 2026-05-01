from open_webui.utils.env_vars import get_env_with_aliases


def test_get_env_with_aliases_prefers_documented_env_name():
    environ = {
        'FEISHU_CLIENT_REDIRECT_URI': 'https://example.test/oauth/feishu/callback',
        'FEISHU_REDIRECT_URI': 'https://legacy.example.test/oauth/feishu/callback',
    }

    assert (
        get_env_with_aliases(
            'FEISHU_CLIENT_REDIRECT_URI',
            'FEISHU_REDIRECT_URI',
            environ=environ,
        )
        == 'https://example.test/oauth/feishu/callback'
    )


def test_get_env_with_aliases_falls_back_to_legacy_alias():
    environ = {'FEISHU_OAUTH_SCOPE': 'contact:user.email:readonly'}

    assert (
        get_env_with_aliases(
            'FEISHU_CLIENT_SCOPE',
            'FEISHU_OAUTH_SCOPE',
            default='contact:user.base:readonly',
            environ=environ,
        )
        == 'contact:user.email:readonly'
    )


def test_get_env_with_aliases_returns_default_when_missing():
    assert (
        get_env_with_aliases(
            'FEISHU_CLIENT_SCOPE',
            'FEISHU_OAUTH_SCOPE',
            default='contact:user.base:readonly',
            environ={},
        )
        == 'contact:user.base:readonly'
    )
