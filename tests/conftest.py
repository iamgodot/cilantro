from logging import getLogger

import pytest


@pytest.fixture(autouse=True)
def enable_logs():
    logger = getLogger("cilantro")
    logger.setLevel("DEBUG")
    logger.propagate = True
