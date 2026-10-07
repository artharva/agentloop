"""Load settings from a JSON file, falling back to defaults."""

import json

DEFAULTS = {"theme": "light", "retries": 3, "verbose": False}


class ConfigError(Exception):
    """The config file exists but cannot be used."""


def load_config(path: str) -> dict:
    """Defaults, overridden by the settings in the JSON file at `path`.

    A missing file means "use the defaults". A file that is not valid JSON, or
    whose top level is not an object, raises ConfigError mentioning the path.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return dict(DEFAULTS)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: invalid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a JSON object")
    return {**DEFAULTS, **data}
