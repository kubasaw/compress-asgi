import gzip
import io
from typing import TYPE_CHECKING, Collection, Iterable, Tuple, Type

import brotli
from .headers_tools import Headers, MutableHeaders

if TYPE_CHECKING:
    from asgiref.typing import Scope


class BaseCompressor:
    encoding_name: bytes = b""

    def __init__(self, chunked_response: bool, response_mimetype: bytes) -> None:
        self.content_length = 0
        self.chunked_response = chunked_response

    def update_response_headers(self, response_headers: Iterable[Tuple[bytes, bytes]]):
        headers = MutableHeaders(response_headers)
        if self.encoding_name:
            headers[b"content-encoding"] = self.encoding_name
            headers.add_vary_header(b"accept-encoding")
            if self.chunked_response:
                del headers[b"content-length"]
            else:
                headers[b"content-length"] = b"%d" % self.content_length

    def compress(self, data: bytes, last_chunk: bool = False) -> bytes:
        self.content_length += len(data)
        return data


class BrotliCompressor(BaseCompressor):
    encoding_name: bytes = b"br"

    def __init__(self, chunked_response: bool, response_mimetype: bytes) -> None:
        super().__init__(chunked_response, response_mimetype)
        self.compressor = brotli.Compressor()

    def compress(self, data: bytes, last_chunk: bool = False) -> bytes:
        compressed_data = self.compressor.process(data) + (
            self.compressor.finish() if last_chunk else b""
        )
        self.content_length += len(compressed_data)

        return compressed_data


class GzipCompressor(BaseCompressor):
    encoding_name: bytes = b"gzip"

    def __init__(self, chunked_response: bool, response_mimetype: bytes) -> None:
        super().__init__(chunked_response, response_mimetype)
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


class CompressorPreconfiguration:
    @staticmethod
    def __accepted_encodings(headers: Headers):
        ACCEPT_ENCODING_HEADER = b"accept-encoding"

        if ACCEPT_ENCODING_HEADER in headers:
            user_accepted_encodings = {
                encoding.partition(b";")[0].strip()
                for encoding in headers[ACCEPT_ENCODING_HEADER].split(b",")
            }

            return user_accepted_encodings

        return set()

    @staticmethod
    def __choose_compressor(
        headers: Headers,
        compressors: Collection[Type[BaseCompressor]],
    ) -> Type[BaseCompressor]:
        accepted_encodings = CompressorPreconfiguration.__accepted_encodings(headers)

        if accepted_encodings:
            for compressor_cls in compressors:
                if compressor_cls.encoding_name in accepted_encodings:
                    return compressor_cls

        return BaseCompressor

    def __init__(
        self,
        minimum_length: int,
        include_mediatype: Collection[str],
        scope: "Scope",
    ) -> None:
        headers = Headers(scope["headers"])
        compressor_cls = CompressorPreconfiguration.__choose_compressor(
            headers, (BrotliCompressor, GzipCompressor)
        )

        self.minimum_length = minimum_length
        self.include_mediatype = include_mediatype
        self.compressor_cls = compressor_cls

        print(self.compressor_cls)

    @property
    def non_identity(self):
        return self.compressor_cls != BaseCompressor

    def get_compressor(
        self,
        response_headers: Iterable[Tuple[bytes, bytes]],
        response_length: int,
        chunked_response: bool,
    ):
        response_mimetype = (
            Headers(response_headers)
            .get(b"content-type", b"")
            .partition(b";")[0]
            .strip()
        )

        if response_mimetype not in self.include_mediatype or (
            response_length < self.minimum_length and not chunked_response
        ):
            self.compressor_cls = BaseCompressor

        return self.compressor_cls(chunked_response, response_mimetype)
