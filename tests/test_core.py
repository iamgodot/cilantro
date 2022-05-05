from collections import namedtuple
from io import BytesIO
from uuid import uuid1
from wsgiref.util import setup_testing_defaults

import pytest

from cilantro import App, Request

ResponseData = namedtuple("ResponseData", "status headers body")


class Client:
    def __init__(self, app) -> None:
        self.app = app

    def request(self, path, method):
        response = {}

        def start_response(status, headers):
            response["status"] = status
            response["headers"] = headers

        environ = {"REQUEST_METHOD": method, "PATH_INFO": path}
        response["body"] = b"".join(self.app(environ, start_response))
        return ResponseData(**response)

    def get(self, path):
        return self.request(path, "GET")


def test_wsgi():
    config = {"views": [{"name": "index", "paths": ["/"], "returns": "Hello world!"}]}
    app = App(config)
    client = Client(app)
    response = client.get("/")
    assert response.status == (200, "OK")
    assert response.body == b"Hello world!"


class TestRequestProperties:
    environ = {}
    setup_testing_defaults(environ)

    def test_basic(self):
        method, path, qs = "GET", "/foobar", "a=b&c=d"
        self.environ.update(
            {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": qs}
        )
        request = Request(self.environ)
        assert request.method == method
        assert request.path == path
        assert request.args == {"a": "b", "c": "d"}

    def test_headers(self):
        content_type = "text/html"
        content_length = 1024
        host = "localhost"
        self.environ.update(
            {
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": content_length,
                "HTTP_HOST": host,
            }
        )
        request = Request(self.environ)
        assert len(request.headers) == 3
        assert request.headers["CONTENT_TYPE"] == content_type
        assert request.headers["CONTENT_LENGTH"] == content_length
        assert request.headers["HOST"] == host

    def test_body(self):
        data = b"foobar"
        stream = BytesIO(data)
        stream.seek(2)
        self.environ.update({"wsgi.input": stream})
        request = Request(self.environ)
        assert request.body == data

    @pytest.mark.parametrize(
        ["data", "form"],
        (
            [b"a=b&c=d", {"a": "b", "c": "d"}],
            [b"a=b&a=c", {"a": ["b", "c"]}],
            [b"foo", {"foo": ""}],
            [b"", {}],
        ),
    )
    def test_form(self, data, form):
        self.environ.update(
            {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": "application/x-www-form-urlencoded",
                "wsgi.input": BytesIO(data),
            }
        )
        request = Request(self.environ)
        assert request.form == form

    @pytest.mark.parametrize(
        ["data", "json"],
        ([b'{"foo":"bar"}', {"foo": "bar"}], [b"", {}], [b"foobar", {}]),
    )
    def test_json(self, data, json):
        self.environ.update(
            {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": "application/json",
                "wsgi.input": BytesIO(data),
            }
        )
        request = Request(self.environ)
        assert request.json == json

    def test_post_and_files(self):
        boundary = f"{uuid1()}"
        self.environ.update(
            {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": f"multipart/form-data; boundary={boundary}",
            }
        )
        body = f"""
--{boundary}
Content-Disposition: form-data; name="field1"

foo
--{boundary}
Content-Disposition: form-data; name="field2"

bar
--{boundary}
Content-Disposition: form-data; name="file1"; filename="test.txt"
Content-Type: text/plain

this is a test line.
--{boundary}
Content-Disposition: form-data; name="file2"; filename="data.file"
Content-Type: application/octet-stream

binary data here.
--{boundary}--
"""
        body_data = body.encode()
        stream = BytesIO(body_data)
        self.environ.update(
            {
                "CONTENT_LENGTH": len(body_data),
                "wsgi.input": stream,
            }
        )
        request = Request(self.environ)
        post = request.post
        assert post["field1"] == "foo"
        assert post["field2"] == "bar"
        assert post["file1"]["name"] == "test.txt"
        assert post["file2"]["name"] == "data.file"
        files = request.files
        assert files["file1"]["file"].read() == b"this is a test line."
        assert files["file2"]["file"].read() == b"binary data here."
