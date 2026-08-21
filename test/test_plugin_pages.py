import json
from pathlib import Path
from types import SimpleNamespace

from open_webui.routers.functions import _plugin_app_response, _plugin_relative_path


FIXTURE_ROOT = Path(__file__).parent / 'fixtures' / 'plugin-pages' / 'example-plugin'


def fixture_assets():
    return {
        str(path.relative_to(FIXTURE_ROOT)).replace('\\', '/'): path.read_text(encoding='utf-8')
        for path in FIXTURE_ROOT.rglob('*')
        if path.is_file()
    }


def test_manifest_exposes_multiple_pages_and_default_page():
    app = _plugin_app_response(
        SimpleNamespace(id='example_plugin', updated_at=42),
        fixture_assets(),
    )

    assert app is not None
    assert app.default_page == 'home'
    assert [page.id for page in app.pages] == ['home', 'second']
    assert [page.id for page in app.pages if page.sidebar] == ['home']
    assert app.pages[0].icon == 'notes'
    assert app.pages[1].icon == 'unknown_icon'


def test_missing_icon_is_accepted_and_uses_the_host_default():
    assets = fixture_assets()
    manifest = json.loads(assets['plugin.json'])
    del manifest['pages'][0]['navigation']['icon']
    assets['plugin.json'] = json.dumps(manifest)

    app = _plugin_app_response(SimpleNamespace(id='example_plugin', updated_at=42), assets)
    assert app is not None
    assert app.pages[0].icon is None


def test_invalid_manifest_and_unsafe_entrypoints_are_rejected():
    assets = fixture_assets()
    manifest = json.loads(assets['plugin.json'])
    manifest['id'] = 'different_plugin'
    assets['plugin.json'] = json.dumps(manifest)

    assert _plugin_app_response(SimpleNamespace(id='example_plugin', updated_at=42), assets) is None
    assert _plugin_relative_path('../index.html', ('.html',)) is None
    assert _plugin_relative_path('https://example.com/index.html', ('.html',)) is None
    assert _plugin_relative_path('index.html?x=1', ('.html',)) is None
