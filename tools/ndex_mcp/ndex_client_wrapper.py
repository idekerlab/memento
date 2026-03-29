"""Thin wrapper around ndex2.client.Ndex2.

Handles initialization from NDExConfig and provides
uniform error-handling for all MCP tool calls.
"""

import ndex2.client

from .config import NDExConfig, has_credentials


class NDExClientWrapper:
    """Wrapper providing error-handled methods over an Ndex2 client."""

    def __init__(self, config: NDExConfig) -> None:
        self._config = config
        self._client = None

    @property
    def client(self):
        """Lazy-initialise the Ndex2 client on first use."""
        if self._client is None:
            if has_credentials(self._config):
                self._client = ndex2.client.Ndex2(
                    self._config.server,
                    self._config.username,
                    self._config.password,
                )
            else:
                self._client = ndex2.client.Ndex2(self._config.server)
        return self._client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_auth(self) -> None:
        """Raise PermissionError if the client has no credentials."""
        if not has_credentials(self._config):
            raise PermissionError(
                "NDEx authentication required. "
                "Configure credentials in ~/.ndex/config.json"
            )

    def _wrap_call(self, fn, *args, **kwargs) -> dict:
        """Call *fn* and return a uniform result dict."""
        try:
            result = fn(*args, **kwargs)
            return {"status": "success", "data": result}
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "error_type": type(e).__name__,
            }

    # ------------------------------------------------------------------
    # Public API – each returns a _wrap_call result dict
    # ------------------------------------------------------------------

    def search_networks(
        self,
        query: str,
        account_name: str = None,
        start: int = 0,
        size: int = 25,
    ) -> dict:
        return self._wrap_call(
            lambda: self.client.search_networks(
                search_string=query,
                account_name=account_name,
                start=start,
                size=size,
            )
        )

    def get_network_summary(self, network_id: str) -> dict:
        return self._wrap_call(
            lambda: self.client.get_network_summary(network_id=network_id)
        )

    def create_network(self, cx2_network) -> dict:
        self._require_auth()
        return self._wrap_call(
            lambda: self.client.save_new_cx2_network(cx2_network.to_cx2())
        )

    def update_network(self, network_id: str, cx2_network) -> dict:
        self._require_auth()

        def _update():
            import io
            import json
            cx2_data = cx2_network.to_cx2()
            stream = io.BytesIO(json.dumps(cx2_data).encode("utf-8"))
            return self.client.update_cx2_network(stream, network_id)

        return self._wrap_call(_update)

    def delete_network(self, network_id: str) -> dict:
        self._require_auth()
        return self._wrap_call(lambda: self.client.delete_network(network_id))

    def update_network_profile(self, network_id: str, profile: dict) -> dict:
        self._require_auth()
        return self._wrap_call(
            lambda: self.client.update_network_profile(network_id, profile)
        )

    def set_network_properties(
        self, network_id: str, properties: list
    ) -> dict:
        self._require_auth()
        return self._wrap_call(
            lambda: self.client.set_network_properties(network_id, properties)
        )

    def download_network(self, network_id: str) -> dict:
        def _download():
            resp = self.client.get_network_as_cx2_stream(network_id)
            return resp.json()

        return self._wrap_call(_download)

    def set_network_visibility(
        self, network_id: str, visibility: str
    ) -> dict:
        self._require_auth()

        def _set_visibility():
            if visibility == "PUBLIC":
                return self.client.make_network_public(network_id)
            elif visibility == "PRIVATE":
                return self.client.make_network_private(network_id)
            else:
                raise ValueError(
                    f"Invalid visibility '{visibility}'. "
                    "Must be 'PUBLIC' or 'PRIVATE'."
                )

        return self._wrap_call(_set_visibility)

    def set_read_only(self, network_id: str, value: bool) -> dict:
        self._require_auth()
        return self._wrap_call(
            lambda: self.client.set_read_only(network_id, value)
        )

    def share_network(
        self, network_id: str, username: str, permission: str
    ) -> dict:
        self._require_auth()
        return self._wrap_call(
            lambda: self.client.grant_network_to_user_by_username(
                network_id, username, permission,
            )
        )

    def get_user_info(self, username: str) -> dict:
        return self._wrap_call(
            lambda: self.client.get_user_by_username(username)
        )

    def get_user_networks(
        self, username: str, offset: int = 0, limit: int = 25
    ) -> dict:
        return self._wrap_call(
            lambda: self.client.get_user_network_summaries(
                username, offset=offset, limit=limit,
            )
        )

    def get_connection_status(self) -> dict:
        return self._wrap_call(
            lambda: {
                "server": self._config.server,
                "username": self._config.username or "anonymous",
                "authenticated": has_credentials(self._config),
            }
        )

    def set_network_system_properties(
        self, network_id: str, properties: dict
    ) -> dict:
        self._require_auth()
        return self._wrap_call(
            lambda: self.client.set_network_system_properties(
                network_id, properties
            )
        )

    def get_my_account_info(self) -> dict:
        self._require_auth()

        def _account_info():
            user_info = self.client.get_user_by_username(
                self._config.username
            )
            network_ids = self.client.get_network_ids_for_user(
                self._config.username
            )
            return {
                **user_info,
                "network_count": len(network_ids),
            }

        return self._wrap_call(_account_info)
