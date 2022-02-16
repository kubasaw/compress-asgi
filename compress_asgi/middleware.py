import gzip
import io
from typing import Collection

import brotli
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class Compressor:
    encodingName: str = None

    def compress(self, data: bytes, finish: bool = False) -> bytes:
        return data


class BrotliCompressor(Compressor):
    encodingName: str = "br"

    def __init__(self) -> None:
        self.compressor = brotli.Compressor()

    def compress(self, data: bytes, finish: bool = False) -> bytes:
        return self.compressor.process(data) + (
            self.compressor.finish() if finish else b""
        )


class GzipCompressor(Compressor):
    encodingName: str = "gzip"

    def __init__(self) -> None:
        self.buffer = io.BytesIO()
        self.file = gzip.GzipFile(mode="wb", fileobj=self.buffer)

    def compress(self, data: bytes, finish: bool = False) -> bytes:
        self.file.write(data)
        if finish:
            self.file.close()

        compressedData = self.buffer.getvalue()
        self.buffer.truncate(0)

        return compressedData


class CompressorFactory:
    def __init__(
        self,
        minimum_size: int,
        compressible_mimes: Collection[str],
    ) -> None:
        self.minimum_size = minimum_size
        self.compressible_mimes = compressible_mimes

    def installCompressor(
        self, request_headers: Headers, response_headers: MutableHeaders
    ) -> Compressor:
        compressor = BrotliCompressor()

        response_headers["content-encoding"] = compressor.encodingName
        return compressor


class CompressionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        include_mediatype: Collection[str] = frozenset(
            (
                "text/html",
                "text/css",
                "text/plain",
                "text/xml",
                "text/x-component",
                "text/javascript",
                "application/x-javascript",
                "application/javascript",
                "application/json",
                "application/manifest+json",
                "application/vnd.api+json",
                "application/xml",
                "application/xhtml+xml",
                "application/rss+xml",
                "application/atom+xml",
                "application/vnd.ms-fontobject",
                "application/x-font-ttf",
                "application/x-font-opentype",
                "application/x-font-truetype",
                "image/svg+xml",
                "image/x-icon",
                "image/vnd.microsoft.icon",
                "font/ttf",
                "font/eot",
                "font/otf",
                "font/opentype",
            )
        ),
    ) -> None:
        self.app = app
        self.compressorFactory = CompressorFactory(minimum_size, include_mediatype)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request_headers = Headers(scope=scope)
            responder = CompressionResponder(
                self.app, request_headers, self.compressorFactory
            )
            await responder(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class CompressionResponder:
    def __init__(
        self,
        app: ASGIApp,
        request_headers: Headers,
        compressor_factory: CompressorFactory,
    ) -> None:

        self.app = app
        self.request_headers = request_headers
        self.compressor_factory = compressor_factory
        self.compressor: Compressor = None

        self.initial_message: Message = {}
        self.send: Send = unattached_send

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.send = send
        await self.app(scope, receive, self.send_with_compression)

    async def send_with_compression(self, message: Message) -> None:

        if message["type"] == "http.response.start":
            # Don't send the initial message until we've determined how to
            # modify the outgoing headers correctly.
            self.initial_message = message

        elif message["type"] == "http.response.body" and not self.compressor:
            response_headers = MutableHeaders(raw=self.initial_message["headers"])
            self.compressor = self.compressor_factory.installCompressor(
                self.request_headers, response_headers
            )

            more_body = message.get("more_body", False)
            message["body"] = self.compressor.compress(message["body"], not more_body)

            await self.send(self.initial_message)
            await self.send(message)

        elif message["type"] == "http.response.body":
            # Remaining body in streaming compressed response.
            more_body = message.get("more_body", False)
            message["body"] = self.compressor.compress(message["body"], not more_body)
            await self.send(message)


async def unattached_send(message: Message) -> None:
    raise RuntimeError("send awaitable not set")  # pragma: no cover
