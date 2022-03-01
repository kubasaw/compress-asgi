import time
import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, StreamingResponse
from starlette.testclient import TestClient


@pytest.mark.parametrize("encoding", ("gzip", "br"))
def test_encoded_response(encoding: str):

    from compress_asgi.middleware import CompressionMiddleware

    TEST_RESPONSE = "1" * 1000
    TEST_PATH = "/"

    app = Starlette()

    app.add_middleware(CompressionMiddleware)
    app.add_route(TEST_PATH, lambda request: PlainTextResponse(TEST_RESPONSE))

    response = TestClient(app).get(TEST_PATH, headers={"accept-encoding": encoding})

    assert response.status_code == 200
    assert response.text == TEST_RESPONSE
    assert response.headers["content-encoding"] == encoding
    assert response.headers["vary"] == "accept-encoding"
    assert int(response.headers["content-length"]) < len(TEST_RESPONSE)


@pytest.mark.parametrize("encoding", (None, "unknown"))
def test_unencoded_response(encoding: str | None):

    from compress_asgi.middleware import CompressionMiddleware

    TEST_RESPONSE = "1" * 2000
    TEST_PATH = "/"

    app = Starlette()

    app.add_middleware(CompressionMiddleware)
    app.add_route(TEST_PATH, lambda request: PlainTextResponse(TEST_RESPONSE))

    response = TestClient(app).get(TEST_PATH, headers={"accept-encoding": encoding})

    assert response.status_code == 200
    assert response.text == TEST_RESPONSE
    assert "content-encoding" not in response.headers
    assert int(response.headers["content-length"]) == len(TEST_RESPONSE)


@pytest.mark.parametrize("encoding", ("gzip", "br"))
def test_streaming_response(encoding: str):

    from compress_asgi.middleware import CompressionMiddleware

    TEST_PATH = "/"
    TEST_RESPONSE_BYTE = "1"
    TEST_RESPONSE_LENGTH = 100

    app = Starlette()

    def responseGenerator():
        bytes_to_be_sent = TEST_RESPONSE_LENGTH
        while bytes_to_be_sent:
            yield TEST_RESPONSE_BYTE
            bytes_to_be_sent -= 1

    app.add_middleware(CompressionMiddleware)
    app.add_route(
        TEST_PATH,
        lambda request: StreamingResponse(responseGenerator(), media_type="text/html"),
    )

    response = TestClient(app).get(TEST_PATH, headers={"accept-encoding": encoding})

    assert response.status_code == 200
    assert response.text == TEST_RESPONSE_BYTE * TEST_RESPONSE_LENGTH
    assert response.headers["content-encoding"] == encoding
    assert response.headers["vary"] == "accept-encoding"
    assert "content-length" not in response.headers


def test_short_response():

    from compress_asgi.middleware import CompressionMiddleware

    TEST_RESPONSE = "1" * 100
    TEST_PATH = "/"

    app = Starlette()

    app.add_middleware(CompressionMiddleware)
    app.add_route(TEST_PATH, lambda request: PlainTextResponse(TEST_RESPONSE))

    response = TestClient(app).get(TEST_PATH)

    assert response.status_code == 200
    assert response.text == TEST_RESPONSE
    assert "content-encoding" not in response.headers
    assert int(response.headers["content-length"]) == len(TEST_RESPONSE)


def test_excluded_mime():

    from compress_asgi.middleware import CompressionMiddleware

    TEST_RESPONSE = "1" * 2000
    TEST_PATH = "/"

    app = Starlette()

    app.add_middleware(CompressionMiddleware, include_mediatype={"only_this_mime"})
    app.add_route(TEST_PATH, lambda request: PlainTextResponse(TEST_RESPONSE))

    response = TestClient(app).get(TEST_PATH)

    assert response.status_code == 200
    assert response.text == TEST_RESPONSE
    assert "content-encoding" not in response.headers
    assert int(response.headers["content-length"]) == len(TEST_RESPONSE)


def test_multiple_vary_headers():

    from compress_asgi.middleware import CompressionMiddleware

    TEST_RESPONSE = "1" * 2000
    TEST_PATH = "/"

    app = Starlette()

    app.add_middleware(CompressionMiddleware)
    app.add_route(
        TEST_PATH,
        lambda request: PlainTextResponse(
            TEST_RESPONSE, headers={"vary": "user-agent"}
        ),
    )

    response = TestClient(app).get(TEST_PATH)

    assert response.status_code == 200
    assert response.text == TEST_RESPONSE
    assert all(
        vary_header in (v.strip() for v in response.headers["vary"].split(","))
        for vary_header in ("user-agent", "accept-encoding")
    )


def test_multiple_same_response_headers():

    from compress_asgi.middleware import CompressionMiddleware

    class MultiDictLike:
        def __init__(self, header: str, *values) -> None:
            self.header = header
            self.values = values

        def items(self):
            for v in self.values:
                yield self.header, str(v)

    TEST_RESPONSE = "1" * 2000
    TEST_PATH = "/"

    app = Starlette()

    app.add_middleware(CompressionMiddleware)
    app.add_route(
        TEST_PATH,
        lambda request: PlainTextResponse(
            TEST_RESPONSE, headers=MultiDictLike("content-encoding", 'gzip', 'br', None, 'gzip')
        ),
    )

    response = TestClient(app).get(TEST_PATH)

    assert response.status_code == 200
    assert response.text == TEST_RESPONSE
