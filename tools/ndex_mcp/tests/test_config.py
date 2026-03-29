"""Tests for ndex_mcp.config module."""

import json

import pytest

from tools.ndex_mcp.config import (
    DEFAULT_SERVER,
    NDExConfig,
    has_credentials,
    load_config,
    load_ndex_config,
)


def _write_config(tmp_path, data):
    """Helper: write a config dict (or raw string) to a temp file and return its path."""
    cfg_file = tmp_path / "config.json"
    if isinstance(data, str):
        cfg_file.write_text(data, encoding="utf-8")
    else:
        cfg_file.write_text(json.dumps(data), encoding="utf-8")
    return cfg_file


# -- load_config tests --------------------------------------------------------


def test_load_valid_config(tmp_path):
    data = {"server": "https://test.ndexbio.org", "username": "alice", "password": "s3cret"}
    path = _write_config(tmp_path, data)

    cfg = load_config(path)

    assert cfg["server"] == "https://test.ndexbio.org"
    assert cfg["username"] == "alice"
    assert cfg["password"] == "s3cret"


def test_load_missing_file(tmp_path):
    path = tmp_path / "nonexistent.json"

    cfg = load_config(path)

    assert cfg["server"] == DEFAULT_SERVER
    assert cfg["username"] is None
    assert cfg["password"] is None


def test_load_invalid_json(tmp_path):
    path = _write_config(tmp_path, "{{not valid json")

    cfg = load_config(path)

    assert cfg["server"] == DEFAULT_SERVER
    assert cfg["username"] is None
    assert cfg["password"] is None


def test_load_partial_config_missing_password(tmp_path):
    data = {"server": "https://custom.ndexbio.org", "username": "bob"}
    path = _write_config(tmp_path, data)

    cfg = load_config(path)

    assert cfg["server"] == "https://custom.ndexbio.org"
    assert cfg["username"] == "bob"
    assert cfg["password"] is None


def test_load_partial_config_missing_server(tmp_path):
    data = {"username": "carol", "password": "pw"}
    path = _write_config(tmp_path, data)

    cfg = load_config(path)

    assert cfg["server"] == DEFAULT_SERVER
    assert cfg["username"] == "carol"
    assert cfg["password"] == "pw"


def test_load_non_dict_json(tmp_path):
    path = _write_config(tmp_path, "[1, 2, 3]")

    cfg = load_config(path)

    assert cfg == {"server": DEFAULT_SERVER, "username": None, "password": None}


# -- load_ndex_config tests ---------------------------------------------------


def test_load_ndex_config_returns_dataclass(tmp_path):
    data = {"server": "https://test.ndexbio.org", "username": "u", "password": "p"}
    path = _write_config(tmp_path, data)

    config = load_ndex_config(path)

    assert isinstance(config, NDExConfig)
    assert config.server == "https://test.ndexbio.org"
    assert config.username == "u"
    assert config.password == "p"


def test_load_ndex_config_defaults(tmp_path):
    path = tmp_path / "nope.json"

    config = load_ndex_config(path)

    assert config.server == DEFAULT_SERVER
    assert config.username is None
    assert config.password is None


# -- has_credentials tests ----------------------------------------------------


@pytest.mark.parametrize(
    "username, password, expected",
    [
        ("alice", "pw", True),
        (None, "pw", False),
        ("alice", None, False),
        (None, None, False),
        ("", "pw", False),
        ("alice", "", False),
        ("", "", False),
    ],
)
def test_has_credentials(username, password, expected):
    config = NDExConfig(server=DEFAULT_SERVER, username=username, password=password)
    assert has_credentials(config) is expected


# -- multi-profile tests ------------------------------------------------------

MULTI_PROFILE_DATA = {
    "server": "https://test.ndexbio.org",
    "profiles": {
        "alice": {"username": "alice", "password": "alice_pw"},
        "bob": {"username": "bob", "password": "bob_pw"},
    },
}


def test_load_profile_by_name(tmp_path):
    path = _write_config(tmp_path, MULTI_PROFILE_DATA)

    cfg = load_config(path, profile="alice")

    assert cfg["server"] == "https://test.ndexbio.org"
    assert cfg["username"] == "alice"
    assert cfg["password"] == "alice_pw"


def test_load_second_profile(tmp_path):
    path = _write_config(tmp_path, MULTI_PROFILE_DATA)

    cfg = load_config(path, profile="bob")

    assert cfg["username"] == "bob"
    assert cfg["password"] == "bob_pw"


def test_profile_inherits_top_level_server(tmp_path):
    """Profiles without their own server use the top-level one."""
    path = _write_config(tmp_path, MULTI_PROFILE_DATA)

    cfg = load_config(path, profile="alice")

    assert cfg["server"] == "https://test.ndexbio.org"


def test_profile_can_override_server(tmp_path):
    data = {
        "server": "https://default.ndexbio.org",
        "profiles": {
            "dev": {
                "server": "https://dev.ndexbio.org",
                "username": "dev_user",
                "password": "dev_pw",
            }
        },
    }
    path = _write_config(tmp_path, data)

    cfg = load_config(path, profile="dev")

    assert cfg["server"] == "https://dev.ndexbio.org"


def test_missing_profile_raises(tmp_path):
    path = _write_config(tmp_path, MULTI_PROFILE_DATA)

    with pytest.raises(ValueError, match="Profile 'charlie' not found"):
        load_config(path, profile="charlie")


def test_profile_requested_but_no_profiles_section(tmp_path):
    """Requesting a profile from a flat config raises ValueError."""
    data = {"server": "https://test.ndexbio.org", "username": "alice", "password": "pw"}
    path = _write_config(tmp_path, data)

    with pytest.raises(ValueError, match="no 'profiles' section"):
        load_config(path, profile="alice")


def test_multi_profile_no_profile_arg_raises(tmp_path):
    """Multiple profiles without --profile should raise."""
    path = _write_config(tmp_path, MULTI_PROFILE_DATA)

    with pytest.raises(ValueError, match="no --profile was specified"):
        load_config(path)


def test_single_profile_used_implicitly(tmp_path):
    """A config with exactly one profile works without --profile."""
    data = {
        "server": "https://test.ndexbio.org",
        "profiles": {
            "only": {"username": "only_user", "password": "only_pw"},
        },
    }
    path = _write_config(tmp_path, data)

    cfg = load_config(path)

    assert cfg["username"] == "only_user"
    assert cfg["password"] == "only_pw"


def test_flat_config_still_works_without_profile(tmp_path):
    """Backward compat: flat format with no profile arg works as before."""
    data = {"server": "https://test.ndexbio.org", "username": "alice", "password": "pw"}
    path = _write_config(tmp_path, data)

    cfg = load_config(path)

    assert cfg["username"] == "alice"
    assert cfg["password"] == "pw"


def test_load_ndex_config_with_profile(tmp_path):
    path = _write_config(tmp_path, MULTI_PROFILE_DATA)

    config = load_ndex_config(path, profile="bob")

    assert isinstance(config, NDExConfig)
    assert config.username == "bob"
    assert config.password == "bob_pw"
