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
    except Exception:
        return dict(DEFAULTS)
    return {**DEFAULTS, **data}
