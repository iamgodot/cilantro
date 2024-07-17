import pytest

from cilantro import Cilantro, Headers, MutableHeaders
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
