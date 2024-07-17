import pytest

from cilantro import Cilantro, Headers, MutableHeaders


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
