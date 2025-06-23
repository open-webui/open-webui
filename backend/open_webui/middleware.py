from enum import Enum
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

class MatchType(Enum):
    exact = 1
    prefix = 2

class PreventCachingMiddleware:
    """
    Add cache headers to the configured request paths.

    Configure the list of paths to prevent caching for by registering
    the middleware with an array of "paths"

    Example usage:

        app = FastAPI( ... )
        app.add_middleware(PreventCachingMiddleware, paths = [
            ("/", MatchType.exact),
            ("/uptodate/", MatchType.prefix),
        ])

    Docs:

     * https://www.starlette.io/middleware/#inspecting-or-modifying-the-response
     * https://github.com/encode/starlette/tree/0.37.2/starlette/middleware
     * https://fastapi.tiangolo.com/advanced/middleware/#adding-asgi-middlewares
    """

    def __init__(
        self,
        app: ASGIApp,
        paths: list[str] = []
    ) -> None:
        self.app = app
        self.paths = paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start" and self.match_path(scope["path"]):
                headers = MutableHeaders(scope=message)
                headers.append("Cache-Control", "must-revalidate")
                headers.append("Expire", "0")

            await send(message)

        await self.app(scope, receive, send_wrapper)

    def match_path(self, request_path: str) -> bool:
        """
        Return True if the path matches the config
        """

        for path_pattern, match_type in self.paths:
            if match_type == MatchType.exact and path_pattern == request_path:
                return True
            elif match_type == MatchType.prefix and request_path.startswith(path_pattern):
                return True

        return False
