"""Unit tests for NDExClientWrapper with a mocked Ndex2 client."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from tools.ndex_mcp.config import NDExConfig
from tools.ndex_mcp.ndex_client_wrapper import NDExClientWrapper

AUTH_CONFIG = NDExConfig(
    server="https://test.ndexbio.org",
    username="testuser",
    password="testpass",
)
ANON_CONFIG = NDExConfig(
    server="https://test.ndexbio.org",
    username=None,
    password=None,
)

PATCH_TARGET = "tools.ndex_mcp.ndex_client_wrapper.ndex2.client.Ndex2"


# ------------------------------------------------------------------
# Construction
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_construct_with_credentials(mock_ndex2_cls):
    wrapper = NDExClientWrapper(AUTH_CONFIG)
    # Client is lazy — access .client to trigger creation
    _ = wrapper.client
    mock_ndex2_cls.assert_called_once_with(
        "https://test.ndexbio.org", "testuser", "testpass"
    )
    assert wrapper._client is mock_ndex2_cls.return_value


@patch(PATCH_TARGET)
def test_construct_anonymous(mock_ndex2_cls):
    wrapper = NDExClientWrapper(ANON_CONFIG)
    _ = wrapper.client
    mock_ndex2_cls.assert_called_once_with("https://test.ndexbio.org")
    assert wrapper._client is mock_ndex2_cls.return_value


# ------------------------------------------------------------------
# _require_auth
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_require_auth_raises_when_anonymous(mock_ndex2_cls):
    wrapper = NDExClientWrapper(ANON_CONFIG)
    with pytest.raises(PermissionError, match="NDEx authentication required"):
        wrapper._require_auth()


@patch(PATCH_TARGET)
def test_require_auth_passes_when_authenticated(mock_ndex2_cls):
    wrapper = NDExClientWrapper(AUTH_CONFIG)
    wrapper._require_auth()  # should not raise


# ------------------------------------------------------------------
# _wrap_call
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_wrap_call_returns_success(mock_ndex2_cls):
    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper._wrap_call(lambda: 42)
    assert result == {"status": "success", "data": 42}


@patch(PATCH_TARGET)
def test_wrap_call_returns_error_on_exception(mock_ndex2_cls):
    wrapper = NDExClientWrapper(AUTH_CONFIG)

    def boom():
        raise RuntimeError("something broke")

    result = wrapper._wrap_call(boom)
    assert result["status"] == "error"
    assert result["message"] == "something broke"
    assert result["error_type"] == "RuntimeError"


# ------------------------------------------------------------------
# search_networks
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_search_networks(mock_ndex2_cls):
    client = mock_ndex2_cls.return_value
    client.search_networks.return_value = [{"name": "net1"}]

    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper.search_networks("TP53", account_name="bob", start=0, size=10)

    assert result["status"] == "success"
    assert result["data"] == [{"name": "net1"}]
    client.search_networks.assert_called_once_with(
        search_string="TP53", account_name="bob", start=0, size=10
    )


# ------------------------------------------------------------------
# get_network_summary
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_get_network_summary(mock_ndex2_cls):
    client = mock_ndex2_cls.return_value
    client.get_network_summary.return_value = {"name": "mynet"}

    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper.get_network_summary("uuid-1234")

    assert result["status"] == "success"
    assert result["data"] == {"name": "mynet"}
    client.get_network_summary.assert_called_once_with(network_id="uuid-1234")


# ------------------------------------------------------------------
# create_network (requires auth)
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_create_network_requires_auth(mock_ndex2_cls):
    wrapper = NDExClientWrapper(ANON_CONFIG)
    cx2 = Mock()

    with pytest.raises(PermissionError):
        wrapper.create_network(cx2)


@patch(PATCH_TARGET)
def test_create_network_success(mock_ndex2_cls):
    client = mock_ndex2_cls.return_value
    client.save_new_cx2_network.return_value = "https://ndex/uuid-new"

    cx2 = Mock()
    cx2.to_cx2.return_value = {"cx2": "data"}

    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper.create_network(cx2)

    assert result["status"] == "success"
    assert result["data"] == "https://ndex/uuid-new"
    client.save_new_cx2_network.assert_called_once_with({"cx2": "data"})


# ------------------------------------------------------------------
# delete_network (requires auth)
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_delete_network_requires_auth(mock_ndex2_cls):
    wrapper = NDExClientWrapper(ANON_CONFIG)
    with pytest.raises(PermissionError):
        wrapper.delete_network("uuid-1234")


@patch(PATCH_TARGET)
def test_delete_network_success(mock_ndex2_cls):
    client = mock_ndex2_cls.return_value
    client.delete_network.return_value = None

    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper.delete_network("uuid-1234")

    assert result["status"] == "success"
    client.delete_network.assert_called_once_with("uuid-1234")


# ------------------------------------------------------------------
# download_network (no auth required)
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_download_network_no_auth_needed(mock_ndex2_cls):
    client = mock_ndex2_cls.return_value
    stream_resp = Mock()
    stream_resp.json.return_value = [{"nodes": []}]
    client.get_network_as_cx2_stream.return_value = stream_resp

    wrapper = NDExClientWrapper(ANON_CONFIG)
    result = wrapper.download_network("uuid-public")

    assert result["status"] == "success"
    assert result["data"] == [{"nodes": []}]
    client.get_network_as_cx2_stream.assert_called_once_with("uuid-public")


# ------------------------------------------------------------------
# set_network_visibility
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_set_visibility_public(mock_ndex2_cls):
    client = mock_ndex2_cls.return_value
    client.make_network_public.return_value = ""

    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper.set_network_visibility("uuid-1234", "PUBLIC")

    assert result["status"] == "success"
    client.make_network_public.assert_called_once_with("uuid-1234")


@patch(PATCH_TARGET)
def test_set_visibility_private(mock_ndex2_cls):
    client = mock_ndex2_cls.return_value
    client.make_network_private.return_value = ""

    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper.set_network_visibility("uuid-1234", "PRIVATE")

    assert result["status"] == "success"
    client.make_network_private.assert_called_once_with("uuid-1234")


@patch(PATCH_TARGET)
def test_set_visibility_invalid_returns_error(mock_ndex2_cls):
    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper.set_network_visibility("uuid-1234", "SHARED")

    assert result["status"] == "error"
    assert result["error_type"] == "ValueError"
    assert "Invalid visibility" in result["message"]


# ------------------------------------------------------------------
# get_connection_status
# ------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_get_connection_status_authenticated(mock_ndex2_cls):
    wrapper = NDExClientWrapper(AUTH_CONFIG)
    result = wrapper.get_connection_status()

    assert result["status"] == "success"
    assert result["data"]["server"] == "https://test.ndexbio.org"
    assert result["data"]["username"] == "testuser"
    assert result["data"]["authenticated"] is True


@patch(PATCH_TARGET)
def test_get_connection_status_anonymous(mock_ndex2_cls):
    wrapper = NDExClientWrapper(ANON_CONFIG)
    result = wrapper.get_connection_status()

    assert result["status"] == "success"
    assert result["data"]["username"] == "anonymous"
    assert result["data"]["authenticated"] is False
