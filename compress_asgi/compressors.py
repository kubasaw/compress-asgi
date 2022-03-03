import gzip
import io
import zlib
from typing import Collection, TypeVar

from .headers_tools import Headers, MutableHeaders

try:
    from asgiref.typing import Scope
except ModuleNotFoundError:
    Scope = TypeVar("Scope")

try:
    import brotli
except ModuleNotFoundError:
    brotli = None


class BaseEncoder:
    encoding_name: str = ""

    def __init__(self, response_mimetype: str) -> None:
        self.content_length = 0

    def compress(self, data: bytes, last_chunk: bool = False) -> bytes:
        self.content_length += len(data)
        return data


if brotli:

    class BrotliEncoder(BaseEncoder):
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

            return super().compress(compressed_data, last_chunk)


class GzipEncoder(BaseEncoder):
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

        return super().compress(compressed_data, last_chunk)


class DeflateEncoder(BaseEncoder):
    encoding_name: str = "deflate"

    def __init__(self, response_mimetype: str) -> None:
        super().__init__(response_mimetype)
        self.compressobj = zlib.compressobj(method=zlib.DEFLATED)

    def compress(self, data: bytes, last_chunk: bool = False) -> bytes:

        compressed_data = self.compressobj.compress(data)
        if last_chunk:
            compressed_data += self.compressobj.flush(zlib.Z_FINISH)

        return super().compress(compressed_data, last_chunk)


class Compressor:
    def __init__(
        self,
        minimum_length: int,
        include_mediatype: Collection[str],
        scope: Scope,
    ) -> None:

        self.request_engine_cls = None
        self.minimum_length = minimum_length
        self.include_mediatype = include_mediatype

        if scope["type"] == "http":
            headers = Headers(scope=scope)

            request_accepted_encodings = headers.getacceptedencodings()
            for compressor in BaseEncoder.__subclasses__():
                if compressor.encoding_name in request_accepted_encodings:
                    self.request_engine_cls = compressor
                    break

    def __bool__(self):
        return bool(self.request_engine_cls)

    def response_init(self, scope: Scope):
        self.response_headers = MutableHeaders(scope=scope)

        content_length = int(
            self.response_headers.get("content-length", self.minimum_length)
        )
        response_mimetype = (
            self.response_headers.get("content-type", "").partition(";")[0].strip()
        )

        if (
            (self.request_engine_cls is None)
            or (response_mimetype not in self.include_mediatype)
            or (content_length < self.minimum_length)
        ):
            self.engine = BaseEncoder(response_mimetype)
        else:
            self.engine = self.request_engine_cls(response_mimetype)

        return scope

    def modify_response_headers(self):
        if self.engine.encoding_name:
            self.response_headers["content-encoding"] = self.engine.encoding_name
            self.response_headers.add_vary_header("accept-encoding")
            if "content-length" in self.response_headers:
                self.response_headers["content-length"] = str(
                    self.engine.content_length
                )
