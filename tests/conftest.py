import pytest

import assistant.config as conf_mod


@pytest.fixture(autouse=True)
def _reset_config_cache():
    """Clear the lru_cache on config.load() before and after every test.

    Without this, monkeypatch changes to _ENV_PATH or env-vars made in one
    test would be invisible to config.load() in the next test.
    """
    conf_mod.load.cache_clear()
    yield
    conf_mod.load.cache_clear()
