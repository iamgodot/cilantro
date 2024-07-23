import pytest

from cilantro import Cilantro, Headers, MutableHeaders, Request
from cilantro.core import response


def test_cilantro():
    cilantro = Cilantro("Cilantro")
    assert cilantro() == "Hello world!"


def test_headers_internal():
    raw = [
        (b"Host", b"localhost"),
        (b"Accept", b"text/html"),
        (b"Accept", b"text/plain"),
    ]
    headers = Headers(raw)
    headers_mutable = MutableHeaders(raw)
    assert headers_mutable["host"] == headers_mutable["Host"] == ["localhost"]
    assert (
        headers_mutable["accept"]
        == headers_mutable["Accept"]
        == ["text/html", "text/plain"]
    )

    assert list(headers_mutable) == ["host", "accept"]
    assert len(headers_mutable) == 2
    assert "host" in headers_mutable and "accept" in headers_mutable

    assert headers == headers_mutable
    assert headers != {"host": ["localhost"], "accept": ["text/html", "text/plain"]}

    assert (
        str(headers)
        == str(headers_mutable)
        == "[(b'Host', b'localhost'), (b'Accept', b'text/html'), (b'Accept', b'text/plain')]"  # noqa
    )
    assert (
        repr(headers)
        == "Headers([(b'Host', b'localhost'), (b'Accept', b'text/html'), (b'Accept', b'text/plain')])"  # noqa
    )
    assert (
        repr(headers_mutable)
        == "MutableHeaders([(b'Host', b'localhost'), (b'Accept', b'text/html'), (b'Accept', b'text/plain')])"  # noqa
    )

    headers_mutable["host"] = "127.0.0.1"
    del headers_mutable["accept"]
    assert headers_mutable["host"] == ["127.0.0.1"]
    with pytest.raises(KeyError):
        headers_mutable["accept"]


def test_init_headers_with_dict():
    headers = Headers({"Host": "localhost", "Accept": "text/html"})
    assert headers.raw == [
        (b"Host", b"localhost"),
        (b"Accept", b"text/html"),
    ]
    assert headers.get("host") == "localhost"
    assert headers.get("accept") == "text/html"


def test_headers_read():
    raw = [
        (b"Host", b"localhost"),
        (b"Accept", b"text/html"),
        (b"Accept", b"text/plain"),
    ]
    headers = Headers(raw)
    assert headers.raw == raw

    assert headers.get("host") == headers.get("Host") == "localhost"
    assert headers.get("accept") == headers.get("Accept") == "text/html"
    assert headers.get("user-agent") is None
    assert headers.get("user-agent", "text/html") == "text/html"

    assert headers.list("host") == headers.list("Host") == ["localhost"]
    assert (
        headers.list("accept") == headers.list("Accept") == ["text/html", "text/plain"]
    )
    assert headers.list("user-agent") == []


def test_headers_with_duplicate_input():
    raw = [
        (b"Host", b"localhost"),
        (b"Accept", b"text/html"),
        (b"Host", b"localhost"),
    ]
    headers = Headers(raw)
    assert len(headers) == 2
    assert headers.get("host") == "localhost"
    assert headers.list("host") == ["localhost"]


def test_headers_write():
    headers = MutableHeaders([])
    headers.append("accept", "text/html")
    headers.append("accept", "text/html")
    headers.append("accept", "text/plain")
    assert headers.list("accept") == ["text/html", "text/plain"]

    headers.set("accept", "application/json")
    headers.set("host", "localhost")
    assert headers.list("accept") == ["application/json"]
    assert headers.list("host") == ["localhost"]

    assert headers.pop("accept") == ["application/json"]
    assert headers.get("accept") is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    ["content", "options", "status", "headers", "body"],
    [
        (
            None,
            {},
            200,
            [
                (b"content-length", b"0"),
            ],
            b"",
        ),
        (
            b"Hello world!",
            {},
            200,
            [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", b"12"),
            ],
            b"Hello world!",
        ),
        (
            "Hello world!",
            {},
            200,
            [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", b"12"),
            ],
            b"Hello world!",
        ),
        (
            "<h1>Hello world!</h1>",
            {"content_type": "text/html"},
            200,
            [
                (b"content-type", b"text/html; charset=utf-8"),
                (b"content-length", b"21"),
            ],
            b"<h1>Hello world!</h1>",
        ),
        (
            {"message": "Hello world!"},
            {},
            200,
            [
                (b"content-type", b"application/json"),
                (b"content-length", b"27"),
            ],
            b'{"message": "Hello world!"}',
        ),
        (
            "https://github.com/iamgodot/cilantro",
            {"status": 308},
            308,
            [
                (b"location", b"https://github.com/iamgodot/cilantro"),
                (b"content-length", b"0"),
            ],
            b"",
        ),
        (
            None,
            {"status": 204},
            204,
            [],
            b"",
        ),
    ],
)
async def test_response_content(content, options, status, headers, body):
    res = await response(content, **options)
    assert res == {
        "status": status,
        "headers": headers,
        "body": body,
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ["headers_in", "headers_out"],
    [
        (
            None,
            [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", b"12"),
            ],
        ),
        (
            {},
            [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", b"12"),
            ],
        ),
        (
            {"foo": "bar"},
            [
                (b"foo", b"bar"),
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", b"12"),
            ],
        ),
    ],
)
async def test_response_headers(headers_in, headers_out):
    res = await response("Hello world!", headers=headers_in)
    assert res["headers"] == headers_out


@pytest.mark.anyio
@pytest.mark.parametrize("content", [b"Hello world!", {"message": "Hello world!"}])
async def test_response_redirect_url(content):
    with pytest.raises(ValueError):
        await response(content, status=308)


@pytest.mark.anyio
async def test_request_basic():
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/index",
        "query_string": b"foo=bar&foo=bat&a=b",
        "headers": [
            (b"host", b"localhost"),
        ],
    }

    request_body_completed = False

    async def receive():
        nonlocal request_body_completed
        if request_body_completed:
            return {"type": "http.disconnect"}
        request_body_completed = True
        return {
            "type": "http.request",
            "body": b"Hello world!",
            "more_body": False,
        }

    async def send(_):
        pass

    request = Request(scope, receive, send)
    assert request.method == "GET"
    assert request.url == "http://localhost/index?foo=bar&foo=bat&a=b"
    assert request.scheme == "http"
    assert request.path == "/index"
    assert request.http_version == "1.1"
    assert request.headers.get("host") == "localhost"
    assert request.query_params == {"foo": ["bar", "bat"], "a": ["b"]}

    request_copy = Request(scope, receive, send)
    assert request != request_copy

    assert str(request) == 'Request("http://localhost/index?foo=bar&foo=bat&a=b")'

    body = await request.get_body()
    assert body == b"Hello world!"
    # Cache is used this time
    body = await request.get_body()
    assert body == b"Hello world!"


@pytest.mark.parametrize(
    ["scheme", "server", "url"],
    [
        ["http", ("localhost", 80), "http://localhost/"],
        ["https", ("localhost", 443), "https://localhost/"],
        ["http", ("localhost", 8000), "http://localhost:8000/"],
        ["http", (), "/"],
    ],
)
def test_request_host(scheme, server, url):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": scheme,
        "path": "/",
        "query_string": b"",
        "headers": [],
        "server": server,
    }

    async def receive():
        return {}

    async def send(_):
        pass

    request = Request(scope, receive, send)
    assert request.url == url


@pytest.mark.anyio
async def test_request_disconnected_during_body():
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"host", b"localhost"),
        ],
    }

    request_body_completed = False

    async def receive():
        nonlocal request_body_completed
        if request_body_completed:
            return {"type": "http.disconnect"}
        request_body_completed = True
        return {
            "type": "http.request",
            "body": b"Hello world!",
            "more_body": True,
        }

    async def send(_):
        pass

    request = Request(scope, receive, send)
    with pytest.raises(RuntimeError):
        await request.get_body()


@pytest.mark.anyio
async def test_request_get_json():
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"host", b"localhost"),
        ],
    }

    async def receive():
        return {
            "type": "http.request",
            "body": b'{"message": "Hello world!"}',
            "more_body": False,
        }

    async def send(_):
        pass

    request = Request(scope, receive, send)
    json_body = await request.get_json()
    assert json_body == {"message": "Hello world!"}
    # Cache is used this time
    json_body = await request.get_json()
    assert json_body == {"message": "Hello world!"}
