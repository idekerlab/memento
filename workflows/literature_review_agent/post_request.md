# Post a Review Request to an Agent

## Overview

These instructions describe how to post a literature review request
that an agent will discover and process. The request is an NDEx
network with structured properties that the agent searches for during
its check-in cycle.

You can post a request using NDEx MCP tools (if you're an agent or
have Claude Code), or via the web app (once available). This document
covers the MCP tool method.

## What You Need

- NDEx account credentials configured in `~/.ndex/config.json`
- The target agent's NDEx username (e.g. `rdaneel`)
- A topic for the literature review

## Step 1: Create the Request Network

Use `create_network` with this spec:

```json
{
  "name": "ndexagent request: <short description of your topic>",
  "description": "<your instructions to the agent — see below>",
  "properties": {
    "ndex-agent": "<target agent username>",
    "ndex-message-type": "request",
    "ndex-workflow": "literature-review",
    "ndex-request-status": "pending"
  }
}
```

No nodes or edges are needed — the description carries the instructions.

### Writing the description

The description is free-form text that the agent will parse for
parameters. Include:

- **Topic** (required): What to search for. Be specific — this
  becomes the bioRxiv search query.
- **Category** (optional): A bioRxiv category to filter by
  (e.g. `cell_biology`, `systems_biology`, `neuroscience`,
  `bioinformatics`, `genetics`, `genomics`, `immunology`,
  `microbiology`, `cancer_biology`, `molecular_biology`).
- **Time range** (optional): How far back to search.
  Default is 7 days.
- **Any special instructions**: Focus areas, entities of interest,
  types of mechanisms to prioritize.

Example description:

```
Please review recent preprints on KRAS signaling in pancreatic cancer.

Focus on papers describing new therapeutic approaches or resistance
mechanisms. Look in the cancer_biology category from the last 14 days.
Prioritize papers that describe specific molecular mechanisms suitable
for pathway modeling.
```

## Step 2: Set Visibility

Set the request network to PUBLIC so the agent can find it via search:

```
set_network_visibility(network_id, "PUBLIC")
```

Note: In production with folder-based inboxes, requests could be
PRIVATE and placed in the agent's inbox. For Phase 1.5 (search-based
discovery), PUBLIC visibility is required.

## Step 3: Verify

Confirm the request is discoverable:

```
search_networks("ndexagent request")
```

Your request should appear in the results.

## What Happens Next

1. The agent runs its check-in workflow (`check_requests.md`)
2. It searches for `ndexagent request` networks with
   `ndex-request-status` = `pending` addressed to it
3. It claims your request (status → `in-progress`)
4. It executes the literature review pipeline
5. It posts the review as a new network with `ndex-reply-to`
   pointing to your request
6. It updates your request: status → `completed`,
   `ndex-reply-network` → UUID of the review

## Checking Status

To check if your request has been processed:

```
get_network_summary(request_network_id)
```

Look at the `ndex-request-status` property:
- `pending` — not yet picked up
- `in-progress` — agent is working on it
- `completed` — done; check `ndex-reply-network` for the review UUID
- `error` — something failed; check `ndex-error-message`

## Example: Full Request via MCP Tools

```python
# 1. Create the request
spec = {
    "name": "ndexagent request: KRAS signaling in pancreatic cancer",
    "description": "Review recent preprints on KRAS signaling in pancreatic cancer. Focus on resistance mechanisms and new therapeutic targets. Search cancer_biology category, last 14 days.",
    "properties": {
        "ndex-agent": "rdaneel",
        "ndex-message-type": "request",
        "ndex-workflow": "literature-review",
        "ndex-request-status": "pending"
    }
}

# 2. Post it
result = create_network(json.dumps(spec))
request_id = result  # UUID

# 3. Make it visible
set_network_visibility(request_id, "PUBLIC")
```
