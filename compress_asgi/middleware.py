from typing import TYPE_CHECKING, Collection

from .compressors import BaseCompressor, CompressorPreconfiguration
from .constants import DEFAULT_MIMES_INCLUDED, DEFAULT_MINIMUM_SIZE

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

        compressor_preconfiguration = CompressorPreconfiguration(
            self.minimum_size, self.include_mediatype, scope
        )
        if compressor_preconfiguration.non_identity:
            responder = CompressionResponder(self.app, compressor_preconfiguration)
            await responder(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class CompressionResponder:
    def __init__(
        self,
        app: "ASGI3Application",
        compressor_preconfiguration: CompressorPreconfiguration,
    ) -> None:

        self.app = app
        self.compressor_preconfig = compressor_preconfiguration

        self.compressor: BaseCompressor = None
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
        else:
            if send_event["type"] == "http.response.body":
                response_started = bool(self.compressor)
                more_body = send_event.get("more_body", False)

                if not response_started:
                    self.compressor = self.compressor_preconfig.get_compressor(
                        self.initial_send_event["headers"],
                        len(send_event["body"]),
                        more_body,
                    )

                send_event["body"] = self.compressor.compress(
                    send_event["body"], not more_body
                )

                if not response_started:
                    self.compressor.update_response_headers(
                        self.initial_send_event["headers"]
                    )
                    await self.send(self.initial_send_event)

            await self.send(send_event)


async def unattached_send(send_event: "ASGIHTTPSendEvent"):
    raise RuntimeError("send awaitable not set")  # pragma: no cover
