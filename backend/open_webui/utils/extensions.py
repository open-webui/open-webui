"""
Extension functions: an admin-only, non-user-facing plugin type.

Unlike tools/actions/filters/pipes, an Extension has no per-user or per-model
surface. It is enabled/disabled from the admin Functions page and exists to run
backend lifecycle work (on_startup / on_shutdown) and to inject global frontend
assets (custom JS/CSS) via the static seams the app already serves
(/static/loader.js and /static/custom.css).

Lifecycle hooks (all optional, sync or async):
    async def on_startup(self, __app__=None)   # at server boot, and on enable
    async def on_shutdown(self)                 # at server shutdown, and on disable
    def assets(self) -> dict                    # {"js": "...", "css": "..."} injected globally

Asset injection model: there is exactly one loader.js and one custom.css, so
core aggregates every enabled extension. CSS is concatenated (the CSS parser
tolerates a bad rule). JS is written to one file per extension under
/static/extensions/<id>.js and pulled in by a generated loader.js that injects a
separate <script> per extension, so a syntax error in one cannot break the rest
(a parse error in a concatenated blob would, and try/catch can't catch it).
"""

import asyncio
import inspect
import json
import logging
import re
from pathlib import Path

from open_webui.env import SAFE_MODE, STATIC_DIR
from open_webui.models.functions import Functions

log = logging.getLogger(__name__)

EXTENSIONS_SUBDIR = 'extensions'
STARTUP_TIMEOUT = 30  # seconds; a hung hook must not stall boot/shutdown

# Active extension modules keyed by function id. Mirrors app.state.EXTENSIONS but
# lives at module level so post_webhook can dispatch without an app handle.
_ACTIVE: dict = {}


def _assets_dir() -> Path:
    d = Path(STATIC_DIR) / EXTENSIONS_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_id(function_id: str) -> str:
    # Filenames are served at a public URL, so keep them to a known-safe set.
    return re.sub(r'[^a-zA-Z0-9_-]', '_', str(function_id))


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def _call_hook(module, name, app=None):
    hook = getattr(module, name, None)
    if hook is None:
        return
    kwargs = {}
    try:
        if '__app__' in inspect.signature(hook).parameters:
            kwargs['__app__'] = app
    except (TypeError, ValueError):
        pass
    await asyncio.wait_for(_maybe_await(hook(**kwargs)), timeout=STARTUP_TIMEOUT)


async def _collect_assets(module) -> dict:
    fn = getattr(module, 'assets', None)
    if fn is None:
        return {}
    try:
        result = await _maybe_await(fn())
        return result if isinstance(result, dict) else {}
    except Exception:
        log.exception('extension assets() failed')
        return {}


async def _activate(app, function) -> bool:
    """Load one extension, set its valves, run on_startup, cache its assets."""
    from open_webui.utils.plugin import load_function_module_by_id

    try:
        module, _type, frontmatter = await load_function_module_by_id(function.id)

        if hasattr(module, 'valves') and hasattr(module, 'Valves'):
            valves = await Functions.get_function_valves_by_id(function.id)
            module.valves = module.Valves(**(valves or {}))

        await _call_hook(module, 'on_startup', app=app)

        app.state.EXTENSIONS[function.id] = {
            'module': module,
            'name': function.name,
            'priority': int((frontmatter or {}).get('priority', 0) or 0),
            'assets': await _collect_assets(module),
        }
        _ACTIVE[function.id] = module
        log.info(f'Extension started: {function.id}')
        return True
    except Exception:
        log.exception(f'Extension failed to start: {function.id}')
        return False


async def _deactivate(app, function_id) -> None:
    _ACTIVE.pop(function_id, None)
    entry = app.state.EXTENSIONS.pop(function_id, None)
    if not entry:
        return
    try:
        await _call_hook(entry['module'], 'on_shutdown')
    except Exception:
        log.exception(f'Extension on_shutdown failed: {function_id}')


def regenerate_assets(app) -> None:
    """Rewrite custom.css + loader.js + per-extension JS from currently active
    extensions. Deterministic order: priority, then id."""
    extensions = getattr(app.state, 'EXTENSIONS', {})
    items = sorted(extensions.items(), key=lambda kv: (kv[1]['priority'], kv[0]))

    assets_dir = _assets_dir()
    for stale in assets_dir.glob('*.js'):
        try:
            stale.unlink()
        except OSError:
            pass

    css_parts = []
    js_urls = []
    for function_id, entry in items:
        assets = entry.get('assets') or {}
        css = assets.get('css')
        js = assets.get('js')
        if css:
            css_parts.append(f'/* === extension: {function_id} === */\n{css}')
        if js:
            safe = _safe_id(function_id)
            # IIFE + try/catch isolates scope and runtime errors per extension.
            wrapped = (
                f'// extension: {function_id}\n'
                f"(function () {{\ntry {{\n{js}\n}} catch (e) {{ console.error('[ext {function_id}]', e); }}\n}})();\n"
            )
            (assets_dir / f'{safe}.js').write_text(wrapped, encoding='utf-8')
            js_urls.append(f'/static/{EXTENSIONS_SUBDIR}/{safe}.js')

    Path(STATIC_DIR, 'custom.css').write_text('\n\n'.join(css_parts), encoding='utf-8')

    loader = '// Generated by Open WebUI extension loader. Do not edit.\n'
    if js_urls:
        loader += (
            f'{json.dumps(js_urls)}.forEach(function (src) {{'
            "var s = document.createElement('script');"
            's.src = src; s.defer = true;'
            'document.head.appendChild(s);'
            '});\n'
        )
    Path(STATIC_DIR, 'loader.js').write_text(loader, encoding='utf-8')


async def startup_extensions(app) -> None:
    """Called once from the lifespan, after dependency install."""
    app.state.EXTENSIONS = {}
    _ACTIVE.clear()
    if SAFE_MODE:
        log.info('SAFE_MODE: skipping extension startup')
        regenerate_assets(app)
        return
    try:
        functions = await Functions.get_functions_by_type('extension', active_only=True)
    except Exception:
        log.exception('Failed to list extensions at startup')
        return

    for function in functions:
        await _activate(app, function)
    regenerate_assets(app)
    log.info(f'Started {len(app.state.EXTENSIONS)} extension(s)')


async def shutdown_extensions(app) -> None:
    """Called from the lifespan after yield."""
    for function_id in list(getattr(app.state, 'EXTENSIONS', {}).keys()):
        await _deactivate(app, function_id)


async def set_extension_active(app, function, is_active: bool) -> None:
    """Enable/disable an extension at runtime (from the toggle route) so it
    takes effect without a restart."""
    if not hasattr(app.state, 'EXTENSIONS'):
        app.state.EXTENSIONS = {}
    if is_active:
        if not SAFE_MODE:
            await _activate(app, function)
    else:
        await _deactivate(app, function.id)
    regenerate_assets(app)


async def dispatch_webhook(name, message, event_data) -> None:
    """Fan a webhook event out to every active extension exposing on_webhook.
    Called from post_webhook regardless of whether an outbound URL is set.
    Best-effort: a failing handler must not break webhook delivery."""
    for function_id, module in list(_ACTIVE.items()):
        hook = getattr(module, 'on_webhook', None)
        if hook is None:
            continue
        try:
            await _maybe_await(hook(name, message, event_data))
        except Exception:
            log.exception(f'Extension on_webhook failed: {function_id}')
