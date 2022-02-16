from http import client
from urllib import response
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, StreamingResponse
from starlette.testclient import TestClient

from compress_asgi.middleware import CompressionMiddleware


def test_brotli_response():

    TEST_RESPONSE = "1" * 2000
    TEST_PATH ='/'

    app = Starlette()

    app.add_middleware(CompressionMiddleware)
    app.add_route(TEST_PATH, lambda request: PlainTextResponse(TEST_RESPONSE))

    response = TestClient(app).get(TEST_PATH, headers={"accept-encoding": "br"})

    assert response.status_code == 200
    assert response.text == TEST_RESPONSE
    assert response.headers.get("content-encoding") == "br"
    assert int(response.headers.get("content-length", "0")) < len(TEST_RESPONSE)
