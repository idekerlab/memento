# Agent Check-In: Process Pending Requests

## Overview

You are an agent checking for pending work requests on NDEx. You will
search for request networks addressed to you, pick one, execute the
requested workflow, and post the result as a reply.

This workflow simulates a scheduled task. A human (or another agent)
posts a request network on NDEx. You discover it, execute it, and
link your reply back to the request.

## Inputs

- **agent_profile** (required): The NDEx config profile name to use
  for credentials (e.g. `"rdaneel"`). This determines which agent
  identity you operate as.

## Step 0: Initialize

1. Load credentials from `~/.ndex/config.json` using the specified
   profile.
2. Retrieve your account info via `get_my_account_info()` to confirm
   identity. Record your username.
3. Determine the output directory: use `$AGENT_OUTPUT_DIR` env var,
   defaulting to `~/Dropbox/GitHub/agent_output`.
4. Create session directory:
   `$AGENT_OUTPUT_DIR/check_requests/YYYYMMDD_HHMMSS/`
5. Write `workflow_metadata.json`:
   ```json
   {
     "workflow": "check-requests",
     "agent_profile": "<profile>",
     "agent_username": "<username>",
     "start_time": "<ISO timestamp>",
     "status": "started"
   }
   ```
6. Initialize `log.json` as an empty array.

## Step 1: Search for Pending Requests

Search NDEx for request networks addressed to you:

```
search_networks("ndexagent request")
```

From the results, filter for networks that match ALL of these criteria:

1. Network name starts with `ndexagent request:`
2. Has property `ndex-message-type` = `request`
3. Has property `ndex-agent` matching your username
4. Has property `ndex-request-status` = `pending`

To check properties, use `get_network_summary(network_id)` on each
candidate from the search results. The summary includes network
properties.

**If no pending requests are found**: Log `"No pending requests"`,
update `workflow_metadata.json` with `"status": "idle"`, and stop.

Save the list of pending requests to `pending_requests.json` in the
session directory.

## Step 2: Select a Request

Pick the first pending request (FIFO — oldest first by creation date).
If multiple requests are pending, process only one per check-in.

Download the request network to read its full description — this
contains the human's instructions.

Save the selected request details to `selected_request.json`:
```json
{
  "request_network_id": "<uuid>",
  "request_name": "<network name>",
  "description": "<the human's instructions>",
  "workflow": "<ndex-workflow property value>",
  "requested_by": "<network owner, if available>"
}
```

## Step 3: Parse Request Parameters

The request network's description contains natural-language
instructions. Parse them to extract workflow parameters.

For `ndex-workflow` = `literature-review`, extract:
- **topic** (required): The research topic to review
- **category** (optional): bioRxiv category filter
- **days_back** (optional, default 7): How far back to search
- **max_triage** (optional, default 10): Max papers to consider
- **visibility** (optional, default "PUBLIC"): Network visibility

Note: default visibility for request-driven reviews is PUBLIC (not
PRIVATE), since the requesting human wants to see the result without
needing to log in. The request description can override this.

Save parsed parameters to `parsed_parameters.json`.

## Step 4: Update Request Status

Mark the request as in-progress so other agent instances don't pick
it up:

```
set_network_properties(request_network_id, [
  {"predicateString": "ndex-request-status",
   "value": "in-progress", "dataType": "string"}
])
```

Log this step.

## Step 5: Execute the Workflow

Based on the `ndex-workflow` property:

### If `literature-review`:

Execute the literature review workflow as specified in
`workflows/literature_review_agent/literature_review.md`, using the
parsed parameters from Step 3.

The full pipeline:
1. Search bioRxiv for recent preprints on the topic
2. Triage and select the most interesting paper
3. Read the full paper PDF
4. Write a review and extract BEL statements
5. Build a CX2 network from the BEL statements
6. Post the review network to NDEx

**Important additions for request-driven execution:**

When building the review network spec (Step 5 of the literature review
workflow), add these extra properties:

- `ndex-reply-to`: UUID of the request network
- `ndex-message-type`: `analysis` (already set by the standard workflow)

These link the reply back to the request.

After posting the review network, set its visibility according to the
parsed `visibility` parameter (default PUBLIC for request-driven work).

### If unknown workflow:

Log an error: `"Unknown workflow: <value>"`. Update the request
status to `error`. Stop.

## Step 6: Link Reply to Request

After the review network is successfully posted:

1. Update the request network to mark it completed:
   ```
   set_network_properties(request_network_id, [
     {"predicateString": "ndex-request-status",
      "value": "completed", "dataType": "string"},
     {"predicateString": "ndex-reply-network",
      "value": "<review_network_uuid>", "dataType": "string"}
   ])
   ```

2. Save the linkage to `reply_result.json`:
   ```json
   {
     "request_network_id": "<uuid>",
     "reply_network_id": "<review network uuid>",
     "reply_network_url": "https://ndexbio.org/viewer/networks/<uuid>",
     "status": "completed"
   }
   ```

## Step 7: Finalize

1. Append a final log entry to `log.json`.
2. Update `workflow_metadata.json` with:
   ```json
   {
     "status": "completed",
     "end_time": "<ISO timestamp>",
     "request_network_id": "<uuid>",
     "reply_network_id": "<uuid>",
     "workflow_executed": "<workflow name>",
     "topic": "<topic if literature-review>"
   }
   ```

## Error Handling

If any step fails after Step 4 (after claiming the request):

1. Update the request network status to `error`:
   ```
   set_network_properties(request_network_id, [
     {"predicateString": "ndex-request-status",
      "value": "error", "dataType": "string"},
     {"predicateString": "ndex-error-message",
      "value": "<brief error description>", "dataType": "string"}
   ])
   ```
2. Log the error in `log.json`.
3. Update `workflow_metadata.json` with `"status": "error"`.

## Convention Compliance

This workflow follows the conventions from
`project/architecture/agent_communication_design.md` Section 7:

- Request networks use `ndex-message-type: request`
- Reply networks use `ndex-message-type: analysis`
- Threading via `ndex-reply-to` property
- Status tracking via `ndex-request-status` property
- All searchable names use `ndexagent` prefix (no hyphen)
- All property keys use `ndex-` prefix
- Agent identity from `ndex-agent` property
