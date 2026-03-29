#!/usr/bin/env python3
"""Integration test for NDEx MCP client against the live server.

Requires:
  - Network access to www.ndexbio.org
  - ~/.ndex/config.json with valid credentials

Exercises the full CRUD lifecycle:
  1. Check connection status
  2. Search for public networks
  3. Create a small test network
  4. Get its summary
  5. Download it
  6. Update its profile
  7. Set visibility to PRIVATE
  8. Delete it
  9. Look up the authenticated user's info

Run:  python tools/ndex_mcp/integration_test.py
"""

import json
import sys
import time

from tools.ndex_mcp.config import load_ndex_config, has_credentials
from tools.ndex_mcp.ndex_client_wrapper import NDExClientWrapper
from tools.ndex_mcp.network_builder import spec_to_cx2

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"


def report(label: str, result: dict) -> bool:
    ok = result.get("status") == "success"
    tag = PASS if ok else FAIL
    print(f"  {tag} {label}")
    if not ok:
        print(f"        {result.get('error_type', '?')}: {result.get('message', '?')}")
    return ok


def main():
    config = load_ndex_config()
    wrapper = NDExClientWrapper(config)
    created_network_id = None
    all_passed = True

    print(f"Server:   {config.server}")
    print(f"Username: {config.username or '(anonymous)'}")
    print(f"Auth:     {has_credentials(config)}")
    print()

    # 1. Connection status
    print("1. Connection status")
    r = wrapper.get_connection_status()
    all_passed &= report("get_connection_status", r)

    # 2. Search
    print("\n2. Search public networks")
    r = wrapper.search_networks("NCI", size=3)
    all_passed &= report("search_networks('NCI', size=3)", r)
    if r["status"] == "success":
        count = r["data"].get("numFound", len(r["data"].get("networks", [])))
        print(f"        Found {count} results")

    # 3. Get summary of a well-known public network (PCNet)
    print("\n3. Get network summary (PCNet: f93f402c-86d4-11e7-a10d-0ac135e8bacf)")
    r = wrapper.get_network_summary("f93f402c-86d4-11e7-a10d-0ac135e8bacf")
    all_passed &= report("get_network_summary", r)

    if not has_credentials(config):
        print("\n--- Skipping write operations (no credentials) ---")
        sys.exit(0 if all_passed else 1)

    # 4. Create a test network
    print("\n4. Create test network")
    test_spec = {
        "name": f"MCP Integration Test {int(time.time())}",
        "description": "Temporary network created by integration_test.py. Safe to delete.",
        "nodes": [
            {"id": 0, "v": {"name": "TP53"}},
            {"id": 1, "v": {"name": "MDM2"}},
            {"id": 2, "v": {"name": "CDKN1A"}},
        ],
        "edges": [
            {"s": 0, "t": 1, "v": {"interaction": "inhibits"}},
            {"s": 0, "t": 2, "v": {"interaction": "activates"}},
        ],
    }
    cx2 = spec_to_cx2(test_spec)
    r = wrapper.create_network(cx2)
    all_passed &= report("create_network", r)

    if r["status"] == "success":
        raw_url = r["data"]
        # The API returns a URL like https://www.ndexbio.org/v2/network/UUID
        created_network_id = raw_url.split("/")[-1] if isinstance(raw_url, str) else str(raw_url)
        print(f"        Network ID: {created_network_id}")

        # Brief pause for server indexing
        time.sleep(2)

        # 5. Get summary of created network
        print("\n5. Get created network summary")
        r = wrapper.get_network_summary(created_network_id)
        all_passed &= report("get_network_summary (created)", r)

        # 6. Download it
        print("\n6. Download created network")
        r = wrapper.download_network(created_network_id)
        all_passed &= report("download_network", r)

        # 7. Update profile
        print("\n7. Update network profile")
        r = wrapper.update_network_profile(
            created_network_id,
            {"name": f"MCP Test (updated) {int(time.time())}"},
        )
        all_passed &= report("update_network_profile", r)

        # 8. Set visibility to PRIVATE
        print("\n8. Set visibility PRIVATE")
        r = wrapper.set_network_visibility(created_network_id, "PRIVATE")
        all_passed &= report("set_network_visibility(PRIVATE)", r)

        # 9. Delete the test network
        print("\n9. Delete test network")
        r = wrapper.delete_network(created_network_id)
        all_passed &= report("delete_network", r)
    else:
        print("        Skipping steps 5-9 (create failed)")

    # 10. User info
    print("\n10. Get user info")
    r = wrapper.get_user_info(config.username)
    all_passed &= report(f"get_user_info('{config.username}')", r)

    # 11. My account info
    print("\n11. Get my account info")
    r = wrapper.get_my_account_info()
    all_passed &= report("get_my_account_info", r)

    # Summary
    print("\n" + ("=" * 40))
    if all_passed:
        print("All tests passed.")
    else:
        print("Some tests FAILED. See above.")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
