import pytest

from config import ConfigError, load_config


def test_error_names_the_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json")
    with pytest.raises(ConfigError, match="settings.json"):
        load_config(str(path))


def test_top_level_must_be_object(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]")
    with pytest.raises(ConfigError):
        load_config(str(path))


def test_defaults_not_shared(tmp_path):
    first = load_config(str(tmp_path / "missing.json"))
    first["theme"] = "changed"
    assert load_config(str(tmp_path / "missing.json"))["theme"] == "light"
