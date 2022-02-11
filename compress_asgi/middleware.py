import gzip
import io
from abc import ABC, abstractmethod
from typing import Iterable

import brotli
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class Compressor(ABC):
    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def compress(self, data: bytes, finish: bool = False) -> bytes:
        raise NotImplementedError


class BrotliCompressor(Compressor):
    def __init__(self) -> None:
        self.compressor = brotli.Compressor()

    def compress(self, data: bytes, finish: bool = False) -> bytes:
        return self.compressor(data) + (self.compressor.finish() if finish else b"")


class GzipCompressor(Compressor):
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


DEFAULT_COMPRESSED_MIMES = {
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
}

COMPRESSORS = {
    "br": BrotliCompressor,
    "gzip": GzipCompressor,
}


class CompressionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        include_mediatype: Iterable[str] = DEFAULT_COMPRESSED_MIMES,
    ) -> None:
        """Init CompressionMiddleware.

        Args:
            app (ASGIApp): starlette/FastAPI application.
            minimum_size: Minimal size, in bytes, for appliying compression. Defaults to 500.
            include_mediatype (set): Set of media-type for which to apply compression. Defaults to {}.

        """
        self.app = app
        self.minimum_size = minimum_size
        self.include_mediatype = set(include_mediatype)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            accepted_encodings = Headers(scope=scope).get("Accept-Encoding", "")

            responder = CompressionResponder(
                self.app,
                accepted_encodings,
                self.minimum_size,
                self.include_mediatype,
            )
            await responder(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class CompressionResponder:
    def __init__(
        self,
        app: ASGIApp,
        accepted_encodings: str,
        minimum_size: int,
        include_mediatype: set[str],
    ) -> None:

        self.app = app
        self.minimum_size = minimum_size
        self.include_mediatype = include_mediatype

        self.encoding_name, self.compressor = next(
            filter(lambda nc: nc[0] in accepted_encodings, COMPRESSORS.items()),
            (None, None),
        )

        self.send: Send = unattached_send
        self.initial_message: Message = {}
        self.started = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:

        if self.encoding_name and self.compressor:
            self.send = send
            self.compressor = self.compressor()

            await self.app(scope, receive, self.send_with_compression)
        else:
            await self.app(scope, receive, send)

    async def send_with_compression(self, message: Message) -> None:

        message_type = message["type"]

        message_body = message.get("body", b"")
        message_last_chunk = not message.get("more_body", False)

        if message_type == "http.response.start":
            # Don't send the initial message until we've determined how to
            # modify the outgoing headers correctly.
            self.initial_message = message

        elif message_type == "http.response.body" and not self.started:
            self.started = True
            response_headers = MutableHeaders(raw=self.initial_message["headers"])

            if response_headers.get("Content-Type") in self.include_mediatype:
                # Apply compression if mediatype is included
                if not message_last_chunk or (len(message_body) >= self.minimum_size):

                    response_headers["Content-Encoding"] = self.encoding_name
                    response_headers.add_vary_header("Accept-Encoding")

                    if message_last_chunk:
                        # Standard compressed response.
                        response_headers["Content-Length"] = str(len(message_body))
                    else:
                        # Content-Length is undefined for streaming response
                        del response_headers["Content-Length"]

                    message["body"] = self.compressor.compress(
                        message_body, finish=message_last_chunk
                    )

            await self.send(self.initial_message)
            await self.send(message)

        elif message_type == "http.response.body":
            # Remaining body in streaming compressed response.

            message["body"] = self.compressor.compress(message_body, message_last_chunk)
            await self.send(message)


async def unattached_send(message: Message) -> None:
    raise RuntimeError("send awaitable not set")  # pragma: no cover
