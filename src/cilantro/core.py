from collections import defaultdict
from collections.abc import Mapping
from json import dumps
from typing import Any, Iterator
from urllib.parse import quote


class Cilantro:
    def __init__(self, name: str):
        self.name = name

    def __call__(self):
        return "Hello world!"


class Headers(Mapping):
    def __init__(self, headers: list[tuple[bytes, bytes]] | dict[str, str]):
        if isinstance(headers, dict):
            self._headers = [(k.encode(), v.encode()) for k, v in headers.items()]
        else:
            self._headers = headers

        self._dict = defaultdict(list)
        if isinstance(headers, dict):
            for k, v in headers.items():
                self._dict[k.lower()].append(v)
        else:
            for b_key, b_value in headers:
                key, value = b_key.decode().lower(), b_value.decode().lower()
                self._dict[key].append(value)
            # Duplicates could exist
            for key, values in self._dict.items():
                self._dict[key] = list(dict.fromkeys(values))

    def __getitem__(self, key: str) -> list[str]:
        if key not in self:
            raise KeyError
        return self._dict[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def __contains__(self, key: Any) -> bool:
        return key.lower() in self._dict

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Headers):
            return False
        return self._dict == other._dict

    def __str__(self) -> str:
        return str(self.raw)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.raw})"

    @property
    def raw(self) -> list[tuple[bytes, bytes]]:
        return self._headers

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self:
            return default
        return self[key][0]

    def list(self, key: str) -> list[str]:
        if key not in self:
            return []
        return self[key]


class MutableHeaders(Headers):
    def __setitem__(self, key: str, value: str) -> None:
        # TODO: validation
        self._dict[key.lower()] = [value]

    def __delitem__(self, key: str) -> None:
        del self._dict[key.lower()]

    def append(self, key: str, value: str) -> None:
        if key not in self:
            self[key] = value
        elif value not in self[key]:
            self._dict[key.lower()].append(value)

    def set(self, key: str, value: str) -> None:
        self[key] = value

    def pop(self, key: str) -> list[str]:
        values = self.list(key)
        del self[key]
        return values


async def response(
    content: bytes | str | dict,
    *,
    content_type: str = "text/plain",
    status: int = 200,
    headers: dict[str, str] | None = None,
    charset: str = "utf-8",
) -> dict[str, int | list[tuple[bytes, bytes]] | bytes]:
    if headers is None:
        headers = {}

    if 300 <= status < 400:
        if not isinstance(content, str):
            raise ValueError("Redirect url must be a string")
        headers["location"] = quote(content, safe=":/%#?=")
        content = ""

    match content:
        case bytes():
            body = content
        case str():
            body = content.encode(charset)
        case dict():
            body = dumps(content, ensure_ascii=False, indent=None).encode(charset)
        case _:
            body = b""

    if isinstance(content, dict):
        headers["content-type"] = "application/json"
    elif content:
        headers["content-type"] = f"{content_type}; charset={charset}"

    if status >= 200 and status not in (204, 304):
        headers.setdefault("content-length", str(len(body)))

    return {
        "status": status,
        "headers": MutableHeaders(headers).raw,
        "body": body,
    }
