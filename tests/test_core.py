from collections import namedtuple

from cilantro import App

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
