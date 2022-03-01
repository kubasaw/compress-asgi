import gzip
import io
from typing import Collection

import brotli

from .headers_tools import Headers, MutableHeaders


class BaseEngine:
    encoding_name: str = ""

    def __init__(self, response_mimetype: str) -> None:
        self.content_length = 0

    def compress(self, data: bytes, last_chunk: bool = False) -> bytes:
        self.content_length += len(data)
        return data


class BrotliEngine(BaseEngine):
    encoding_name: str = "br"

    def __init__(self, response_mimetype: str) -> None:
        super().__init__(response_mimetype)

        if any(
            predicate in response_mimetype
            for predicate in ("text", "javascript", "json", "xml")
        ):
            mode = brotli.MODE_TEXT
        elif "font" in response_mimetype:
            mode = brotli.MODE_FONT
        else:
            mode = brotli.MODE_GENERIC

        self.compressor = brotli.Compressor(mode=mode)

    def compress(self, data: bytes, last_chunk: bool = False) -> bytes:
        compressed_data = self.compressor.process(data) + (
            self.compressor.finish() if last_chunk else b""
        )
        self.content_length += len(compressed_data)

        return compressed_data


class GzipEngine(BaseEngine):
    encoding_name: str = "gzip"

    def __init__(self, response_mimetype: str) -> None:
        super().__init__(response_mimetype)
        self.buffer = io.BytesIO()
        self.file = gzip.GzipFile(mode="wb", fileobj=self.buffer)

    def compress(self, data: bytes, last_chunk: bool = False) -> bytes:
        self.file.write(data)
        if last_chunk:
            self.file.close()

        compressed_data = self.buffer.getvalue()
        self.buffer.seek(0)
        self.buffer.truncate()
        self.content_length += len(compressed_data)

        return compressed_data


class Compressor:
    def __init__(
        self,
        minimum_length: int,
        include_mediatype: Collection[str],
        request_headers: Headers,
    ) -> None:

        self.request_engine_cls = None

        request_accepted_encodings = request_headers.getacceptedencodings()
        for compressor in (BrotliEngine, GzipEngine):
            if compressor.encoding_name in request_accepted_encodings:
                self.request_engine_cls = compressor
                break

        self.minimum_length = minimum_length
        self.include_mediatype = include_mediatype

    @property
    def accepted(self):
        return bool(self.request_engine_cls)

    def response_init(self, response_headers: MutableHeaders):
        self.response_headers = response_headers

        content_length = int(
            response_headers.get("content-length", self.minimum_length)
        )
        response_mimetype = (
            response_headers.get("content-type", "").partition(";")[0].strip()
        )

        if (
            (self.request_engine_cls is None)
            or (response_mimetype not in self.include_mediatype)
            or (content_length < self.minimum_length)
        ):
            self.engine = BaseEngine(response_mimetype)
        else:
            self.engine = self.request_engine_cls(response_mimetype)

    def modify_response_headers(self):
        if self.engine.encoding_name:
            self.response_headers["content-encoding"] = self.engine.encoding_name
            self.response_headers.add_vary_header("accept-encoding")
            if "content-length" in self.response_headers:
                self.response_headers["content-length"] = str(
                    self.engine.content_length
                )
