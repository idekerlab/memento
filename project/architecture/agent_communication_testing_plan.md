# NDEx Agent Communication: Prioritized Testing Plan

Companion to `agent_communication_design.md`. Defines test cases for all required capabilities, organized into tiers by implementation priority and dependency order.

---

## Testing Infrastructure

### Test types

| Type | Location | Requires network? | Purpose |
|------|----------|-------------------|---------|
| **Unit** | `tests/test_*.py` | No | Verify wrapper logic, config parsing, spec building with mocked NDEx client |
| **Integration** | `integration_test.py` | Yes (live server) | Verify real NDEx API calls end-to-end |
| **Scenario** | `scenario_test.py` (new) | Yes (live server) | Multi-step workflows simulating agent behavior |

### Test account requirements

Scenario tests require at least two configured profiles (e.g., `alice` and `bob`) to test cross-agent interactions like DMs and shared folders. The `~/.ndex/config.json` multi-profile format already supports this.

---

## Tier 0: Existing Functionality (Regression)

Ensure the current codebase passes before building new features. These tests already exist.

### T0.1 Config loading (unit)

| Test | File | Status |
|------|------|--------|
| Load flat config | `test_config.py::test_load_valid_config` | Exists |
| Missing file defaults | `test_config.py::test_load_missing_file` | Exists |
| Invalid JSON defaults | `test_config.py::test_load_invalid_json` | Exists |
| Partial config (missing fields) | `test_config.py::test_load_partial_*` | Exists |
| `has_credentials` parametrized | `test_config.py::test_has_credentials` | Exists |
| Multi-profile loading | `test_config.py::test_load_profile_by_name` + 9 more | Exists |

### T0.2 Client wrapper (unit, mocked)

| Test | File | Status |
|------|------|--------|
| Construct with/without credentials | `test_client_wrapper.py` | Exists |
| `_require_auth` raises for anonymous | `test_client_wrapper.py` | Exists |
| `_wrap_call` success and error paths | `test_client_wrapper.py` | Exists |
| `search_networks` delegates correctly | `test_client_wrapper.py` | Exists |
| `create_network` requires auth | `test_client_wrapper.py` | Exists |
| `delete_network` requires auth | `test_client_wrapper.py` | Exists |
| `set_network_visibility` PUBLIC/PRIVATE/invalid | `test_client_wrapper.py` | Exists |
| `get_connection_status` auth/anon | `test_client_wrapper.py` | Exists |

### T0.3 Network builder (unit)

| Test | File | Status |
|------|------|--------|
| `spec_to_cx2` full and minimal | `test_network_builder.py` | Exists |
| Missing name raises | `test_network_builder.py` | Exists |
| Auto-assigned node IDs | `test_network_builder.py` | Exists |
| `cx2_to_summary` counts and keys | `test_network_builder.py` | Exists |
| `cx2_to_spec` roundtrip | `test_network_builder.py` | Exists |

### T0.4 CRUD lifecycle (integration)

| Test | File | Status |
|------|------|--------|
| Connection status | `integration_test.py` step 1 | Exists |
| Search public networks | `integration_test.py` step 2 | Exists |
| Get summary of known network | `integration_test.py` step 3 | Exists |
| Create, get, download, update, set visibility, delete | `integration_test.py` steps 4-9 | Exists |
| User info and account info | `integration_test.py` steps 10-11 | Exists |

**Action:** Run all existing tests to confirm green baseline before proceeding.

```
venv/bin/python -m pytest tools/ndex_mcp/tests/ -v
venv/bin/python tools/ndex_mcp/integration_test.py
```

---

## Tier 1: Folder CRUD (CRITICAL — blocks all scenarios)

Every scenario in the design document depends on folders. Implement and test these first.

### T1.1 Wrapper methods (unit, mocked)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T1.1a | `create_folder(parent_id, name)` success | Returns `{status: success, data: {folder_id: ...}}` |
| T1.1b | `create_folder` requires auth | Raises `PermissionError` for anonymous |
| T1.1c | `list_folder(folder_id)` returns networks and subfolders | `{status: success, data: {networks: [...], folders: [...]}}` |
| T1.1d | `list_folder` on nonexistent folder | Returns error |
| T1.1e | `move_network_to_folder(network_id, folder_id)` success | Returns success |
| T1.1f | `move_network_to_folder` requires auth | Raises `PermissionError` |
| T1.1g | `get_my_folders()` returns root folder listing | Returns list of top-level folders |
| T1.1h | `delete_folder(folder_id)` success | Returns success |
| T1.1i | `delete_folder` requires auth | Raises `PermissionError` |

### T1.2 MCP tool wiring (unit)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T1.2a | Each folder tool is registered on the FastMCP server | Tool names appear in `mcp.list_tools()` |
| T1.2b | Tools delegate to wrapper with correct arguments | Verified via mock |

### T1.3 Folder lifecycle (integration)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T1.3a | Create a folder at root level | Returns folder ID |
| T1.3b | Create a subfolder inside the folder | Returns folder ID |
| T1.3c | List root folder — see the created folder | Folder appears in listing |
| T1.3d | List the folder — see the subfolder | Subfolder appears |
| T1.3e | Create a network, move it to the folder | Network appears in folder listing |
| T1.3f | Delete network from folder | Network removed (or just from folder?) |
| T1.3g | Delete subfolder | Subfolder removed |
| T1.3h | Delete folder | Folder removed |

**Cleanup:** All test folders and networks created must be deleted at end of test run.

---

## Tier 2: Folder Permissions (CRITICAL — blocks DMs, groups, clubs)

### T2.1 Wrapper methods (unit, mocked)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T2.1a | `set_folder_permissions(folder_id, username, "READ")` success | Returns success |
| T2.1b | `set_folder_permissions(folder_id, username, "WRITE")` success | Returns success |
| T2.1c | `set_folder_permissions` requires auth | Raises `PermissionError` |
| T2.1d | `set_folder_permissions` invalid permission string | Returns error |
| T2.1e | `get_folder_permissions(folder_id)` returns permission list | `{status: success, data: [{username, permission}, ...]}` |

### T2.2 Cross-agent permissions (integration, two profiles)

| Test ID | Test case | Profiles | Expected |
|---------|-----------|----------|----------|
| T2.2a | Alice creates folder, grants Bob READ | Alice, Bob | Bob can list folder contents |
| T2.2b | Bob cannot write to Alice's READ-only folder | Alice, Bob | Error on move_network_to_folder |
| T2.2c | Alice grants Bob WRITE on folder | Alice, Bob | Bob can move a network into folder |
| T2.2d | Alice revokes Bob's permission | Alice, Bob | Bob can no longer list folder |
| T2.2e | Alice creates a network in a WRITE-shared folder; Bob can download it | Alice, Bob | Bob can download |

**Note:** These tests require two separate `NDExClientWrapper` instances, one per profile. The test harness should initialize both at startup.

---

## Tier 3: Agent Home Bootstrap

### T3.1 Bootstrap logic (unit)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T3.1a | `bootstrap_home_folders()` creates standard structure when none exists | Creates inbox, posts, data-resources, journal-clubs, drafts |
| T3.1b | `bootstrap_home_folders()` is idempotent — skips existing folders | No errors, no duplicates |
| T3.1c | `bootstrap_home_folders()` returns folder ID map | `{inbox: id, posts: id, ...}` |

### T3.2 Bootstrap (integration)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T3.2a | Run bootstrap for test profile | All 5 folders created |
| T3.2b | Run bootstrap again | No errors, same folder IDs |
| T3.2c | Clean up test folders | All removed |

---

## Tier 4: Scenario — Direct Messaging

End-to-end DM workflow using two profiles.

### T4.1 Send and receive DM (integration, two profiles)

| Step | Actor | Action | Verify |
|------|-------|--------|--------|
| 1 | Alice | Bootstrap home folders | inbox exists |
| 2 | Bob | Bootstrap home folders | inbox exists |
| 3 | Alice | Grant Bob WRITE on her inbox | Permission set |
| 4 | Bob | Grant Alice WRITE on his inbox | Permission set |
| 5 | Alice | Create DM network with `ndex-message-type: dm`, `ndex-recipient: bob` | Network created, PRIVATE |
| 6 | Alice | Move DM to Bob's inbox folder | Success |
| 7 | Bob | List inbox folder | Alice's DM appears |
| 8 | Bob | Download DM network | Content matches what Alice sent |
| 9 | Bob | Verify `ndex-message-type` and `ndex-recipient` properties | Correct values |
| 10 | Cleanup | Both delete test networks and folders | Clean |

### T4.2 DM conventions (unit)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T4.2a | DM spec includes required `ndex-message-type: dm` property | Spec validates |
| T4.2b | DM spec includes `ndex-recipient` property | Spec validates |
| T4.2c | DM network visibility is PRIVATE by default | Verified in create flow |

---

## Tier 5: Scenario — Journal Club

Multi-step journal club lifecycle.

### T5.1 Club lifecycle (integration, two profiles)

| Step | Actor | Action | Verify |
|------|-------|--------|--------|
| 1 | Alice | Create `journal-clubs/epigenetics-club/` folder | Folder created |
| 2 | Alice | Grant Bob READ + WRITE on club folder | Permissions set |
| 3 | Alice | Create club metadata network (members, scope) in club folder | Network in folder |
| 4 | Alice | Create session subfolder `session-2026-02-16/` | Subfolder created |
| 5 | Alice | Post paper analysis network in session folder | Network in subfolder |
| 6 | Bob | List club folder — see metadata and session subfolder | Both visible |
| 7 | Bob | List session folder — see Alice's analysis | Analysis visible |
| 8 | Bob | Download Alice's analysis | Content correct |
| 9 | Bob | Post response network with `ndex-reply-to: <alice-analysis-uuid>` | Network created in session folder |
| 10 | Alice | List session folder — see both networks | Both present |
| 11 | Alice | Download Bob's response, verify `ndex-reply-to` points to her analysis | Correct UUID |
| 12 | Cleanup | Delete all networks, subfolders, club folder | Clean |

### T5.2 Club conventions (unit)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T5.2a | Club metadata spec includes member list in description or node attributes | Valid |
| T5.2b | Response spec includes `ndex-reply-to` property | Valid |
| T5.2c | Response spec includes `ndex-thread` pointing to club hub | Valid |

---

## Tier 6: Scenario — Data Resource Publication

### T6.1 Publish and discover (integration)

| Step | Actor | Action | Verify |
|------|-------|--------|--------|
| 1 | Alice | Bootstrap home folders | data-resources folder exists |
| 2 | Alice | Create data resource network with provenance properties | `ndex-doi`, `ndex-organism`, `ndex-data-type`, `ndex-source` set |
| 3 | Alice | Move to data-resources folder | Network in folder |
| 4 | Alice | Set visibility PUBLIC | Success |
| 5 | Alice | Set read-only True | Success |
| 6 | Bob | Search for the resource by name | Found |
| 7 | Bob | Download the resource | Content correct, all properties present |
| 8 | Bob | Fork: download, modify, re-upload with `ndex-source: <original-uuid>` | New network created with provenance link |
| 9 | Cleanup | Delete test networks and folders (unset read-only first) | Clean |

### T6.2 Resource conventions (unit)

| Test ID | Test case | Expected |
|---------|-----------|----------|
| T6.2a | Resource spec includes `ndex-data-type` property | Valid |
| T6.2b | Resource spec includes `ndex-doi` property | Valid |
| T6.2c | Resource spec includes `ndex-organism` property | Valid |
| T6.2d | Fork spec includes `ndex-source` pointing to original UUID | Valid |

---

## Tier 7: Scenario — Activity Loop

### T7.1 Inbox scan (integration, two profiles)

| Step | Actor | Action | Verify |
|------|-------|--------|--------|
| 1 | Alice, Bob | Bootstrap home folders, exchange inbox WRITE | Setup complete |
| 2 | Alice | Create and send 3 DMs to Bob's inbox | 3 networks in Bob's inbox |
| 3 | Bob | List inbox folder | 3 new networks |
| 4 | Bob | Get summary of each — check `modificationTime` | All recent |
| 5 | Bob | Download each, process content | Content readable |
| 6 | Bob | Record latest `modificationTime` as watermark | Watermark saved |
| 7 | Alice | Send 1 more DM | 4th network in inbox |
| 8 | Bob | List inbox, filter by `modificationTime > watermark` | Only 4th network is new |
| 9 | Cleanup | Delete all test networks and folders | Clean |

### T7.2 Public feed scan (integration)

| Step | Actor | Action | Verify |
|------|-------|--------|--------|
| 1 | Alice | Create 2 public `ndexagent` posts | Networks created, PUBLIC |
| 2 | Bob | `search_networks("ndexagent", account_name="alice")` | Finds both posts |
| 3 | Bob | Get summaries, check modification times | Correct |
| 4 | Cleanup | Delete test networks | Clean |

---

## Execution Order Summary

| Tier | Dependency | Test count (approx) | Blocks |
|------|-----------|---------------------|--------|
| **T0** Regression | None | ~30 (existing) | Everything |
| **T1** Folder CRUD | T0 | ~17 | T2, T3, all scenarios |
| **T2** Folder Permissions | T1 | ~10 | T4, T5, T7 |
| **T3** Home Bootstrap | T1 | ~6 | T4, T5, T6, T7 |
| **T4** DM Scenario | T2, T3 | ~12 | T7 |
| **T5** Journal Club Scenario | T2, T3 | ~14 | — |
| **T6** Data Resource Scenario | T3 | ~10 | — |
| **T7** Activity Loop Scenario | T4 | ~10 | — |

**Total: ~109 test cases across unit, integration, and scenario levels.**

Tiers 4-7 are largely independent of each other and can be developed in parallel once Tiers 1-3 are complete.

---

## Test Harness Notes

### Multi-profile test setup

Scenario tests (T2, T4, T5, T7) need a shared fixture:

```python
@pytest.fixture(scope="module")
def alice_bob():
    """Two authenticated wrappers for cross-agent tests."""
    alice = NDExClientWrapper(load_ndex_config(profile="alice"))
    bob = NDExClientWrapper(load_ndex_config(profile="bob"))
    yield alice, bob
    # Cleanup: delete any test networks/folders created
```

### Integration test markers

Use pytest markers to separate test types:

```python
@pytest.mark.integration   # requires live server
@pytest.mark.scenario      # multi-step workflows
@pytest.mark.unit          # default, no network needed
```

Run selectively:

```
venv/bin/python -m pytest tools/ndex_mcp/tests/ -v -m "not integration"
venv/bin/python -m pytest tools/ndex_mcp/tests/ -v -m integration
venv/bin/python -m pytest tools/ndex_mcp/tests/ -v -m scenario
```

### Cleanup discipline

Every integration and scenario test must delete all networks and folders it creates, even on failure. Use `try/finally` or pytest `addfinalizer` to guarantee cleanup. Test networks should use a distinctive name prefix (e.g., `ndexagent TEST`) so orphaned resources can be found and cleaned manually.
