# sl_tools — DepMap + GDSC MCP Server

Unified MCP server exposing DepMap (CRISPR dependency, mutations, CNV, expression) and GDSC (drug sensitivity) tools for R. Corona and other NDExBio agents.

## Attribution

This code is vendored from the SL hypothesis project developed by the collaborator repo at `sl_agent_project_dev/src/sl_hypothesis/mcp_tools/`. The plugin-per-source architecture, client implementations, anti-hallucination checks (`check_gene_coverage`), version pinning, and SHA256 data manifests are all from that upstream. Only these adaptations were made during vendoring (2026-04-15):

- Import paths rewritten `sl_hypothesis.mcp_tools.*` → `tools.sl_tools.*`
- Default data directory changed from `retro_testing_data/` → `~/.ndex/cache/sl_tools_data/` (see `_config.py`)
- `registry.py` `PLUGIN_MODULES` trimmed to depmap + gdsc only; the other seven plugins (biogrid, encode, lincs, msigdb, ccle, tcga, edison) remain available in the upstream repo and can be re-vendored here when a concrete R. Corona query needs them
- Attribution README added

The upstream code is actively maintained and should be the source of truth for bug fixes. When pulling updates, redo the three small diffs above.

## Data

Data files are NOT vendored. They are downloaded separately per each plugin's `data_manifest.json`.

- **DepMap 25Q3** (~1.2 GB, required files): manual browser download from https://depmap.org/portal/download/ → place in `~/.ndex/cache/sl_tools_data/depmap/`
- **GDSC 8.5** (~52 MB, required files): auto-downloadable via the URLs in `gdsc/data_manifest.json` → place in `~/.ndex/cache/sl_tools_data/gdsc/`

Verify integrity against SHA256 checksums in each `data_manifest.json` where provided.

## Running

Standalone for testing:

```bash
cd /path/to/memento
.venv/bin/python -m tools.sl_tools.mcp_server --depmap-version 25Q3
```

Via Claude Code `.mcp.json`:

```json
"sl_tools": {
  "command": ".venv/bin/python",
  "args": ["-m", "tools.sl_tools.mcp_server", "--depmap-version", "25Q3"]
}
```

## Registered tools

See `depmap/mcp_tools.py` (~28 tools) and `gdsc/mcp_tools.py` (~13 tools). Cross-database unified tools `mcp_check_coverage` and `mcp_ensure_all_data` are in `registry.py`.

All tools are profile-free — this MCP does not need a `--profile` flag because it is read-only database access, not agent-identified writes. Per the R. Corona onboarding plan (`ndexbio/project/rcorona_onboarding_plan.md` §6), all analytical queries route through R. Corona via network-mediated request/reply; other memento-based agents should invoke R. Corona rather than calling this MCP directly even though technically possible.
