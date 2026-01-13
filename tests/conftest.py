import os

import pytest

from src.core import llm as llm_module


@pytest.fixture(autouse=True, scope="session")
def enable_test_mode():
    """Force offline LLM stubs for tests."""
    previous = os.getenv("CARF_TEST_MODE")
    os.environ["CARF_TEST_MODE"] = "1"
    llm_module.get_chat_model.cache_clear()

    yield

    if previous is None:
        os.environ.pop("CARF_TEST_MODE", None)
    else:
        os.environ["CARF_TEST_MODE"] = previous
    llm_module.get_chat_model.cache_clear()
