# Procedure: onboard-new-agent-ndex-account

**Owner**: rdaneel (development persona)
**Flavor**: dev-agent (this markdown is the source of truth; `rdaneel-procedures` network carries a pointer via `workflow_path`)
**Current version**: v1.0
**Last refined**: 2026-04-18

## Summary

Create an NDEx account for a new agent on the local agent-communication server (`http://127.0.0.1:8080`), so that subsequent `ndex` MCP calls authenticate successfully. This is the step that comes **before** bootstrapping an agent's self-knowledge networks — if the account doesn't exist, `create_network` / `get_user_networks` / `cache_network` all fail with opaque `401 Client Error` responses.

## When to use

- User has added a new agent directory (`agents/<agent>/CLAUDE.md`) and profile (`local-<agent>` in `~/.ndex/config.json`) but no NDEx account exists yet on the local server.
- You attempt to use `mcp__ndex__*` tools for the new agent and get `401 Client Error: for url: http://127.0.0.1:8080/v2/user?username=<agent>`.
- You are about to run the `bootstrap-agent-self-knowledge` procedure for a new agent and want to pre-check that the account exists.

## Preconditions

- Local NDEx server is running at `http://127.0.0.1:8080` (verify by checking that a known-good profile like `local-rcorona` returns data from `get_user_networks`).
- The target profile exists in `~/.ndex/config.json` with `username: <agent>` and `password: <some-password>`. The password in that file is what we register with; NDEx does not rehash or negotiate.
- Account on the target server does not already exist with a mismatched password (see Pitfalls).

## Steps

**1. Read the password from config.**

```bash
python3 -c "
import json
cfg = json.load(open('/Users/dexterpratt/.ndex/config.json'))
for p in ['local-<agent>']:
    pr = cfg['profiles'][p]
    print(f\"{pr['username']}\t{pr['password']}\")
"
```

Replace `<agent>` with the real name. Confirm output shows the expected username + the password you want to register.

**2. POST to `/v2/user`.**

```bash
curl -s -X POST "http://127.0.0.1:8080/v2/user" \
  -H "Content-Type: application/json" \
  -d '{
    "userName": "<agent>",
    "password": "<agent-password>",
    "emailAddress": "<agent>@ndexbio.local",
    "firstName": "<agent>",
    "lastName": "Agent",
    "isIndividual": true
  }' \
  -w "\nHTTP %{http_code}\n"
```

Expected: `HTTP 201` and a response body that is a URL like `http://localhost:8080/v3/user/<uuid>`. The UUID is the agent's NDEx `ownerUUID` — worth recording in the session history for later reference (user-account UUIDs are stable even as network UUIDs change).

**3. Verify auth works via MCP.**

Call `mcp__ndex__get_user_networks(username="<agent>", profile="local-<agent>", limit=3)`. Expected:

```json
{"status": "success", "data": []}
```

An empty `data` array is the correct result for a brand-new account. If you see the previous 401, the credentials in `~/.ndex/config.json` don't match what you just POSTed (unlikely if you read them from the same file in step 1) **or** the ndex MCP wrapper has a cached bad `NDExClientWrapper` from a prior poisoned attempt (see `tools/CLAUDE.md` L2).

**4. Record in session history.**

Append to `rdaneel-session-history` a note of the form:
- `action: "created NDEx account for <agent>"`
- `ndex_owner_uuid: "<uuid from step 2>"`
- `server: "http://127.0.0.1:8080"`

Append this procedure to the session's `used_in_sessions` on the procedure-node in `rdaneel-procedures`.

## Pitfalls

- **Account already exists with a different password**: `POST /v2/user` returns `400` or `409` instead of `201`. The local NDEx server does **not** let you overwrite a password via this endpoint — you would need admin-level intervention (`/v2/admin/*` endpoints; or, pragmatically, register a fresh username like `<agent>-v2` and update `~/.ndex/config.json`).
- **Bad request body**: NDEx is strict about the JSON keys. `userName` (not `username`), `emailAddress` (not `email`), `isIndividual` (not `individual`). If you hit `400` with a cryptic message, check keys first.
- **URL confusion**: the endpoint is `/v2/user`, but NDEx returns `/v3/user/<uuid>` as the created-resource URL. This is normal (v2 create returns v3 resource URL; API versioning quirk). The UUID is valid on both.
- **localhost vs 127.0.0.1**: the ndex2 Python library has a hardcoded path override when it sees `localhost` in a URL. Always use `127.0.0.1` in profile `server` fields. `curl` is fine with either; the asymmetry bites later when MCP tools are used.
- **401 on first MCP call after successful POST**: ndex MCP caches `NDExClientWrapper` per-profile in-process. If the profile was previously attempted with wrong credentials, the cache may stick until full desktop restart. Workaround: use a fresh profile name (`local-<agent>-v2`) for the session, OR advise the user to restart the desktop. See `tools/CLAUDE.md` § L2.

## When to refine

- **NDEx API version changes** (`/v3/user` becomes creation endpoint): update steps 2 and 3.
- **Local NDEx server URL changes** (when symposium.ndexbio.org comes online): update the server URL in all examples.
- **New required field** in `POST /v2/user`: add to the JSON body in step 2.
- **If admin-reset-password endpoint becomes available**, add a "fix mismatched-password account" recovery path to Pitfalls rather than the v2 fallback.
- **If new class of agent account** (org accounts, team accounts, etc.) becomes needed: either add a variant procedure or branch this one.
