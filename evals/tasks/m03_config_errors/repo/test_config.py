import pytest

from config import DEFAULTS, ConfigError, load_config


def test_missing_file_gives_defaults(tmp_path):
    assert load_config(str(tmp_path / "nope.json")) == DEFAULTS


def test_overrides(tmp_path):
    path = tmp_path / "c.json"
    path.write_text('{"theme": "dark"}')
    assert load_config(str(path))["theme"] == "dark"
    assert load_config(str(path))["retries"] == 3


def test_invalid_json_raises(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{theme: dark")
    with pytest.raises(ConfigError):
        load_config(str(path))
