"""Configuration loader for NDEx MCP server.

Reads credentials from ~/.ndex/config.json (read-only).
The user manages that file manually.

Supports two config formats:

**Flat (legacy)**::

    {"server": "https://www.ndexbio.org", "username": "alice", "password": "pw"}

**Multi-profile**::

    {
      "server": "https://www.ndexbio.org",
      "profiles": {
        "alice": {"username": "alice", "password": "pw"},
        "bob":   {"username": "bob",   "password": "pw2"}
      }
    }

When using multi-profile, pass ``--profile <name>`` to the MCP server.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_SERVER = "https://www.ndexbio.org"
DEFAULT_CONFIG_PATH = Path.home() / ".ndex" / "config.json"

_DEFAULTS = {
    "server": DEFAULT_SERVER,
    "username": None,
    "password": None,
}


def _is_profile_format(data: dict) -> bool:
    """Return True if *data* uses the multi-profile format."""
    return "profiles" in data and isinstance(data["profiles"], dict)


def load_config(
    path: Optional[Path] = None,
    profile: Optional[str] = None,
) -> dict:
    """Load NDEx config from a JSON file.

    Args:
        path: Config file path. Defaults to ``~/.ndex/config.json``.
        profile: Named profile to load from a multi-profile config.
            When *None* and the file uses the flat format, the flat
            credentials are returned.  When *None* and the file uses
            multi-profile format, raises ``ValueError``.

    Returns a dict with keys: server, username, password.
    Falls back to defaults if the file is missing or invalid.
    """
    path = path or DEFAULT_CONFIG_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(_DEFAULTS)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)

    server = data.get("server", DEFAULT_SERVER)

    if profile is not None:
        # Explicit profile requested
        if not _is_profile_format(data):
            raise ValueError(
                f"Profile '{profile}' requested but config file has no "
                "'profiles' section. Add a 'profiles' dict to your config."
            )
        profiles = data["profiles"]
        if profile not in profiles:
            available = ", ".join(sorted(profiles.keys()))
            raise ValueError(
                f"Profile '{profile}' not found. "
                f"Available profiles: {available}"
            )
        p = profiles[profile]
        return {
            "server": p.get("server", server),
            "username": p.get("username"),
            "password": p.get("password"),
        }

    # No profile requested
    if _is_profile_format(data):
        profiles = data["profiles"]
        if len(profiles) == 1:
            # Single profile — use it implicitly
            p = next(iter(profiles.values()))
            return {
                "server": p.get("server", server),
                "username": p.get("username"),
                "password": p.get("password"),
            }
        available = ", ".join(sorted(profiles.keys()))
        raise ValueError(
            "Config contains multiple profiles but no --profile was "
            f"specified. Available profiles: {available}"
        )

    # Flat legacy format
    return {
        "server": server,
        "username": data.get("username"),
        "password": data.get("password"),
    }


@dataclass
class NDExConfig:
    server: str
    username: Optional[str]
    password: Optional[str]


def load_ndex_config(
    path: Optional[Path] = None,
    profile: Optional[str] = None,
) -> NDExConfig:
    """Load NDEx config and return an NDExConfig instance."""
    cfg = load_config(path, profile=profile)
    return NDExConfig(
        server=cfg["server"],
        username=cfg["username"],
        password=cfg["password"],
    )


def has_credentials(config: NDExConfig) -> bool:
    """Return True if both username and password are non-None and non-empty."""
    return bool(config.username) and bool(config.password)
