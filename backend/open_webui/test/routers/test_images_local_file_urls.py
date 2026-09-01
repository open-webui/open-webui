"""Regression tests for same-instance file URLs in the image-edit loader (#29220).

An absolute URL pointing back at this deployment must be resolved through the local
file route (with the caller's identity) rather than fetched anonymously over HTTP.
"""

import pytest

from open_webui.routers.images import _resolve_local_file_path

FILE_ID = 'b4dcc0cc-a7f9-47db-9b99-6cb8ec42d0d3'
CONTENT_PATH = f'/api/v1/files/{FILE_ID}/content'
SELF = ['http://localhost:8080']


@pytest.mark.parametrize(
    'url,origins,expected',
    [
        # --- resolves to the local route ---
        (f'http://localhost:8080{CONTENT_PATH}', SELF, CONTENT_PATH),
        (f'http://localhost:8080{CONTENT_PATH}/picture.png', SELF, f'{CONTENT_PATH}/picture.png'),
        (f'http://localhost:8080{CONTENT_PATH}?download=1', SELF, CONTENT_PATH),
        # default port is normalised, so an explicit :80 still matches
        (f'http://localhost{CONTENT_PATH}', ['http://localhost:80'], CONTENT_PATH),
        # behind a proxy the configured public URL matches even though base_url does not
        (
            f'https://chat.example.com{CONTENT_PATH}',
            ['https://chat.example.com', 'http://127.0.0.1:8080/'],
            CONTENT_PATH,
        ),
        # subpath deployment: the prefix is stripped from the returned route
        (
            f'https://host.example/openwebui{CONTENT_PATH}',
            ['https://host.example/openwebui'],
            CONTENT_PATH,
        ),
        # --- stays on the external path ---
        (f'http://evil.example{CONTENT_PATH}', SELF, None),
        # userinfo injection must not read as same-origin
        (f'http://localhost:8080@evil.example{CONTENT_PATH}', SELF, None),
        # suffix confusion
        (f'http://localhost:8080evil.example{CONTENT_PATH}', SELF, None),
        # same origin, different port
        (f'http://localhost:9999{CONTENT_PATH}', SELF, None),
        # same origin but not the file-content route
        ('http://localhost:8080/api/v1/chats/', SELF, None),
        # unanchored lookalike path
        (f'http://localhost:8080/evil{CONTENT_PATH}', SELF, None),
        # a subpath deployment must not match the unprefixed route
        (f'https://host.example{CONTENT_PATH}', ['https://host.example/openwebui'], None),
        # non-http scheme
        (f'file://{CONTENT_PATH}', SELF, None),
        # no usable origin configured
        (f'http://localhost:8080{CONTENT_PATH}', [], None),
        (f'http://localhost:8080{CONTENT_PATH}', [''], None),
    ],
)
def test_resolve_local_file_path(url, origins, expected):
    assert _resolve_local_file_path(url, origins) == expected
