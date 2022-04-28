from importlib import import_module
from typing import Iterable, Tuple


class View:
    def __init__(self, name, paths, methods, handler, **_) -> None:
        self.name = name
        self.paths = paths
        self.methods = methods
        self.handler = handler


class Dispatcher:
    def __init__(self) -> None:
        self.views_static = {}
        self.views_dynamic = {}

    def is_static(self, path) -> bool:
        return bool(path)

    def add_view(self, view: View) -> None:
        for path in view.paths:
            if self.is_static(path):
                self.views_static[path] = view
            else:
                self.views_dynamic[path] = view

    def match(self, path, method):
        if view := self.views_static.get(path):
            if method in view.methods:
                return view
            else:
                return None
        # TODO: match dynamic views


class Request:
    def __init__(self, environ) -> None:
        self.environ = environ

    @property
    def method(self) -> str:
        return self.environ["REQUEST_METHOD"]

    @property
    def path(self) -> str:
        return self.environ["PATH_INFO"]


class Response:
    # TODO: cache properties
    def __init__(self, data, headers) -> None:
        if isinstance(data, (str, bytes)):
            self.data = [data]
        else:
            self.data = data
        self.headers = headers

    def __iter__(self):
        for part in self.data:
            if isinstance(part, str):
                yield part.encode()
            else:
                yield part

    @property
    def status(self) -> Tuple[int, str]:
        return 200, "OK"

    @property
    def status_code(self):
        return self.status[0]


class ConfigError(Exception):
    pass


class App:
    def __init__(self, config) -> None:
        if config is None:
            config = {}
        self.config = {k.lower(): v for k, v in config.items()}
        self.dispatcher = Dispatcher()
        self.parse_config()

    def parse_config(self):
        for view in self.config.get("views", []):
            # TODO: validation
            if not view.get("name"):
                raise ConfigError("No name for view:", view)
            if not view.get("methods"):
                view["methods"] = ["GET"]
            if returns := view.get("returns"):
                handler = lambda *a, **kw: returns
            elif calls := view.get("calls"):
                splited = calls.rsplit(".", 1)
                app_name = self.config["app_name"]
                try:
                    if len(splited) == 1:
                        mod = import_module(app_name)
                        handler = getattr(mod, splited[0])
                    else:
                        mod = import_module(f"{app_name}.{splited[0]}")
                        handler = getattr(mod, splited[1])
                except AttributeError:
                    raise ConfigError("Invalid handling for view:", view["name"])
            else:
                raise ConfigError("No handling for view:", view["name"])
            view["handler"] = handler
            self.dispatcher.add_view(View(**view))

    def __call__(self, environ, start_response) -> Iterable:
        return self.handle(environ, start_response)

    def make_headers(self, response):
        return []

    def handle(self, environ, start_response) -> Iterable:
        request = Request(environ)
        view = self.dispatcher.match(request.path, request.method)
        result = view.handler(request)
        headers = self.make_headers(result)
        response = Response(result, headers)
        start_response(response.status, response.headers)
        return response
