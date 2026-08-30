"""Port probing for the Ollama API base URL.

Exercised against real listening sockets on ephemeral loopback ports rather
than mocks, so the reachability check itself is covered rather than stubbed.
Ephemeral ports are used (via the injectable `ports` argument) so the test does
not depend on the real ports being free on the machine running it.
"""

import socket
import threading
from contextlib import closing, contextmanager

from open_webui.config import OLLAMA_API_PORTS, _resolve_ollama_base_url


@contextmanager
def listening():
    """Hold a listening socket on an ephemeral loopback port; yield the port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(8)
    port = sock.getsockname()[1]

    stop = threading.Event()

    def accept_loop():
        sock.settimeout(0.2)
        while not stop.is_set():
            try:
                with closing(sock.accept()[0]):
                    pass
            except (OSError, TimeoutError):
                continue

    thread = threading.Thread(target=accept_loop, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        stop.set()
        thread.join(timeout=2)
        sock.close()


def free_port() -> int:
    """A port that is (almost certainly) not listening."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def test_default_port_is_tried_first():
    """An existing setup must never be redirected away from the default port."""
    with listening() as default_port, listening() as fallback_port:
        resolved = _resolve_ollama_base_url(_url(default_port), ports=(default_port, fallback_port))
    assert resolved == _url(default_port)


def test_falls_back_when_the_default_port_is_down():
    down = free_port()
    with listening() as fallback_port:
        resolved = _resolve_ollama_base_url(_url(down), ports=(down, fallback_port))
    assert resolved == _url(fallback_port)


def test_first_reachable_fallback_wins():
    """With several fallbacks, probing order decides."""
    down, also_down = free_port(), free_port()
    with listening() as first, listening() as second:
        resolved = _resolve_ollama_base_url(_url(down), ports=(down, also_down, first, second))
    assert resolved == _url(first)


def test_url_is_unchanged_when_nothing_is_listening():
    """No endpoint up: keep the configured URL so the error names it."""
    down, also_down = free_port(), free_port()
    original = _url(down)
    assert _resolve_ollama_base_url(original, ports=(down, also_down)) == original


def test_only_the_port_is_rewritten():
    """Scheme, host and any path must survive the rewrite."""
    down = free_port()
    with listening() as fallback_port:
        resolved = _resolve_ollama_base_url(f"http://127.0.0.1:{down}/ollama", ports=(down, fallback_port))
    assert resolved == f"http://127.0.0.1:{fallback_port}/ollama"


def test_configured_ports_are_distinct_and_default_is_first():
    assert len(set(OLLAMA_API_PORTS)) == len(OLLAMA_API_PORTS)
    assert OLLAMA_API_PORTS[0] == 11434
    assert 17434 in OLLAMA_API_PORTS
