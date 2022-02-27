from typing import TYPE_CHECKING, Collection

from .compressors import Compressor
from .constants import DEFAULT_MIMES_INCLUDED, DEFAULT_MINIMUM_SIZE
from .headers_tools import Headers, MutableHeaders

if TYPE_CHECKING:
    from asgiref.typing import (
        ASGI3Application,
        ASGIReceiveCallable,
        ASGISendCallable,
        HTTPDisconnectEvent,
        HTTPResponseBodyEvent,
        HTTPResponseStartEvent,
        HTTPServerPushEvent,
        Scope,
    )

    ASGIHTTPSendEvent = (
        HTTPResponseStartEvent
        | HTTPResponseBodyEvent
        | HTTPServerPushEvent
        | HTTPDisconnectEvent
    )


class CompressionMiddleware:
    def __init__(
        self,
        app: "ASGI3Application",
        minimum_size: int = DEFAULT_MINIMUM_SIZE,
        include_mediatype: Collection[str] = DEFAULT_MIMES_INCLUDED,
    ) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.include_mediatype = frozenset(include_mediatype)

    async def __call__(
        self, scope: "Scope", receive: "ASGIReceiveCallable", send: "ASGISendCallable"
    ) -> None:

        compressor = Compressor(
            self.minimum_size, self.include_mediatype, Headers(scope=scope)
        )
        if compressor.accepted:
            responder = CompressionResponder(self.app, compressor)
            await responder(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class CompressionResponder:
    def __init__(
        self,
        app: "ASGI3Application",
        compressor: Compressor,
    ) -> None:

        self.app = app
        self.compressor = compressor

        self.initial_send_event: HTTPResponseStartEvent = None
        self.send: ASGISendCallable = unattached_send

    async def __call__(
        self, scope: "Scope", receive: "ASGIReceiveCallable", send: "ASGISendCallable"
    ) -> None:
        self.send = send
        await self.app(scope, receive, self.send_with_compression)

    async def send_with_compression(self, send_event: "ASGIHTTPSendEvent") -> None:

        if send_event["type"] == "http.response.start":
            self.initial_send_event = send_event
            self.compressor.response_init(MutableHeaders(scope=send_event))
        else:
            if send_event["type"] == "http.response.body":

                send_event["body"] = self.compressor.engine.compress(
                    send_event["body"], not send_event.get("more_body", False)
                )

                if self.initial_send_event:
                    self.compressor.modify_response_headers()
                    await self.send(self.initial_send_event)
                    self.initial_send_event = None

            await self.send(send_event)


async def unattached_send(send_event: "ASGIHTTPSendEvent"):
    raise RuntimeError("send awaitable not set")  # pragma: no cover
