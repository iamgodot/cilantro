from logging.config import dictConfig
from os import environ

from .core import Cilantro, Headers, MutableHeaders, response

__all__ = ["Cilantro", "Headers", "MutableHeaders", "response"]

__version__ = "0.1.0"

logging_config = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in func `%(funcName)s` by logger `%(name)s`: %(message)s",  # NOQA
        }
    },
    "handlers": {
        "default": {
            "class": (
                "logging.StreamHandler"
                if environ.get("CILANTRO_LOG")
                else "logging.NullHandler"
            ),
            "formatter": "default",
        }
    },
    "loggers": {
        "cilantro": {
            "level": "DEBUG",  # TODO: make configurable
            "handlers": ["default"],
            "propagate": False,
        },
    },
}
dictConfig(logging_config)
