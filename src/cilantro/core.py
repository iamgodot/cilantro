import json
from cgi import FieldStorage
from collections import defaultdict
from collections.abc import MutableMapping
from importlib import import_module
from io import BytesIO
from typing import Dict, Iterable, Optional, Tuple
from urllib.parse import unquote


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


class RequestHeaderDict(MutableMapping):
    def __init__(self, headers: Dict) -> None:
        self._headers = headers

    @property
    def data(self) -> Dict:
        return self._headers

    def __getitem__(self, key):
        key = key.replace("-", "_").upper()
        return self.data[key]

    def __setitem__(self, key, value):
        raise TypeError(f"{self.__name__} is read-only.")

    def __delitem__(self, key):
        raise TypeError(f"{self.__name__} is read-only.")

    def __iter__(self):
        for key in self.data:
            yield key

    def __len__(self) -> int:
        return len(self.data)

    def __contains__(self, key) -> bool:
        return key in self.data


class cached_property:
    def __init__(self, getter) -> None:
        self.getter = getter
        self.attr = getter.__name__

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = obj.__dict__[self.attr] = self.getter(obj)
        return value

    def __set__(self, obj, value):
        raise AttributeError(f"{self.attr} is read-only.")


def parse_qs(qs):
    """Parse strings with key-value params.

    Returns:
        A result dict containing key-value pairs.
        Note the value won't be list when it's singled.
    """

    def unquote_plus(x):
        return unquote(x.replace("+", " "))

    result = defaultdict(list)
    for item in qs.split("&"):
        if not item:
            continue
        splited = item.split("=", maxsplit=1)
        key = splited[0]
        value = "" if len(splited) == 1 else splited[1]
        result[unquote_plus(key)].append(unquote_plus(value))
    return {k: v[0] if len(v) == 1 else v for k, v in result.items()}


class Request:
    """Wraps a HTTP request, keeping minimal and read-only.

    Attributes:
        method: HTTP method upper string.
        path: HTTP url path.
        args: Parsed dict of query string.

        content_type: `CONTENT_TYPE` from headers.
        content_length: `CONTENT_LENGTH` from headers.
        headers: Dict of headers.

        body: Raw bytes read from request body.
        post: Dict of all data of a POST request, including form and files.
        form: Dict of form data when content type is x-www-form-urlencoded.
        files: Dict of file data when content type is multipart/form-data.
        json: Dict of POST data when content type is application/json.
    """

    __slots__ = ("_environ", "__dict__")

    def __init__(self, environ) -> None:
        self._environ = environ

    @cached_property
    def method(self) -> str:
        return self._environ["REQUEST_METHOD"].upper()

    @cached_property
    def path(self) -> str:
        return self._environ["PATH_INFO"]

    @cached_property
    def args(self) -> Dict:
        query_string = self._environ.get("QUERY_STRING")
        return parse_qs(query_string)

    @cached_property
    def content_type(self):
        return self.headers["content-type"]

    @cached_property
    def content_length(self):
        return self.headers["content-length"]

    @cached_property
    def headers(self) -> Dict:
        headers = {
            "CONTENT_TYPE": self._environ.get("CONTENT_TYPE", "").lower(),
            "CONTENT_LENGTH": self._environ.get("CONTENT_LENGTH", 0),
        }
        for k, v in self._environ.items():
            if k.startswith("HTTP_"):
                headers[k[5:].upper()] = v
        return RequestHeaderDict(headers)

    @cached_property
    def form(self) -> Optional[Dict]:
        if self.content_type != "application/x-www-form-urlencoded":
            return None
        return {k: v for k, v in self.post.items() if not isinstance(v, dict)}

    @cached_property
    def body(self) -> bytes:
        """Raw bytes of request body."""
        input_ = self._environ["wsgi.input"]
        # The input stream may have been pre-read
        input_.seek(0)
        return input_.read()

    @cached_property
    def post(self) -> Optional[Dict]:
        if self.method != "POST":
            return None
        if self.content_type.startswith("multipart/"):
            post = {}
            field_storage = FieldStorage(
                fp=BytesIO(self.body), environ=self._environ, keep_blank_values=True
            )
            # NOTE: prevent GC of FieldStorage so that item.file won't be closed
            self._field_storage = field_storage
            for item in field_storage.list or []:
                if not item.filename:
                    post[item.name] = item.value
                else:
                    post[item.name] = {
                        "name": item.filename,
                        "file": item.file,
                        "type": item.type,
                    }
            return post
        return parse_qs(self.body.decode())

    @cached_property
    def files(self) -> Optional[Dict]:
        """File related data for uploading.

        Returns:
            A dict {'file1': {'file': f, 'name': n, 'type': t}}, where f is a file
            object, n is specified file name or None and t is the given content type.
        """
        if not self.content_type.startswith("multipart/"):
            return None
        return {k: v for k, v in self.post.items() if isinstance(v, dict)}

    @cached_property
    def json(self) -> Optional[Dict]:
        if self.content_type != "application/json":
            return None
        data = self.body.decode()
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {}


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
