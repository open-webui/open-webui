import sys
import types

import pytest
from open_webui.retrieval.web.utils import SafePlaywrightURLLoader


class FakeSyncPage:
    def __init__(self):
        self.closed = False

    def route(self, *_args, **_kwargs):
        return None

    def goto(self, *_args, **_kwargs):
        raise RuntimeError('navigation failed')

    def close(self):
        self.closed = True


class FakeSyncBrowser:
    def __init__(self):
        self.closed = False
        self.pages = []

    def new_page(self):
        page = FakeSyncPage()
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True


class FakeSyncPlaywright:
    def __init__(self, browser):
        self.chromium = types.SimpleNamespace(
            connect=lambda *_args, **_kwargs: browser,
            launch=lambda *_args, **_kwargs: browser,
        )

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeAsyncPage:
    def __init__(self):
        self.closed = False

    async def route(self, *_args, **_kwargs):
        return None

    async def goto(self, *_args, **_kwargs):
        raise RuntimeError('navigation failed')

    async def close(self):
        self.closed = True


class FakeAsyncBrowser:
    def __init__(self):
        self.closed = False
        self.pages = []

    async def new_page(self):
        page = FakeAsyncPage()
        self.pages.append(page)
        return page

    async def close(self):
        self.closed = True


class FakeAsyncPlaywright:
    def __init__(self, browser):
        async def connect(*_args, **_kwargs):
            return browser

        async def launch(*_args, **_kwargs):
            return browser

        self.chromium = types.SimpleNamespace(
            connect=connect,
            launch=launch,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


def install_sync_playwright(monkeypatch, browser):
    playwright_module = types.ModuleType('playwright')
    sync_api_module = types.ModuleType('playwright.sync_api')
    sync_api_module.sync_playwright = lambda: FakeSyncPlaywright(browser)
    monkeypatch.setitem(sys.modules, 'playwright', playwright_module)
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', sync_api_module)


def install_async_playwright(monkeypatch, browser):
    playwright_module = types.ModuleType('playwright')
    async_api_module = types.ModuleType('playwright.async_api')
    async_api_module.async_playwright = lambda: FakeAsyncPlaywright(browser)
    monkeypatch.setitem(sys.modules, 'playwright', playwright_module)
    monkeypatch.setitem(sys.modules, 'playwright.async_api', async_api_module)


def make_loader():
    loader = SafePlaywrightURLLoader.__new__(SafePlaywrightURLLoader)
    loader.urls = ['https://example.test']
    loader.playwright_ws_url = None
    loader.headless = True
    loader.proxy = None
    loader.continue_on_failure = False
    loader.playwright_timeout = 1000
    loader.evaluator = types.SimpleNamespace(
        evaluate=lambda *_args, **_kwargs: 'content',
        evaluate_async=lambda *_args, **_kwargs: 'content',
    )
    return loader


def test_lazy_load_closes_page_and_browser_when_navigation_raises(monkeypatch):
    browser = FakeSyncBrowser()
    install_sync_playwright(monkeypatch, browser)
    loader = make_loader()
    monkeypatch.setattr(loader, '_safe_process_url_sync', lambda _url: None)

    with pytest.raises(RuntimeError, match='navigation failed'):
        list(loader.lazy_load())

    assert browser.closed
    assert browser.pages[0].closed


@pytest.mark.asyncio
async def test_alazy_load_closes_page_and_browser_when_navigation_raises(monkeypatch):
    browser = FakeAsyncBrowser()
    install_async_playwright(monkeypatch, browser)
    loader = make_loader()

    async def safe_process_url(_url):
        return None

    monkeypatch.setattr(loader, '_safe_process_url', safe_process_url)

    with pytest.raises(RuntimeError, match='navigation failed'):
        async for _doc in loader.alazy_load():
            pass

    assert browser.closed
    assert browser.pages[0].closed
