"""
Unified sl-tools MCP Server — single entry point for all biological database tools.

Registers plugins for: DepMap, BioGRID, ENCODE, LINCS, GDSC, MSigDB.
Also provides unified cross-database tools (mcp_check_coverage, mcp_ensure_all_data).

Usage:
    uv run sl-mcp-server [--depmap-version 25Q3]
"""

import argparse
import sys

from mcp.server.fastmcp import FastMCP

from . import _config
from .registry import discover_and_register

mcp_app = FastMCP(
    "sl-tools",
    instructions=(
        "Unified synthetic lethality tools server. Provides access to DepMap (CRISPR "
        "dependency, mutations, CNV, expression), BioGRID (protein/genetic interactions), "
        "ENCODE (TF ChIP-seq binding), LINCS (L1000 knockout transcriptional effects), "
        "GDSC (drug sensitivity), and MSigDB (pathway gene sets). Use mcp_check_coverage "
        "to verify gene availability across all databases before analysis."
    ),
)


def main():
    parser = argparse.ArgumentParser(description="sl-tools MCP Server (stdio)")
    parser.add_argument(
        "--depmap-version", default="23Q2", help="DepMap release version (e.g., 25Q3, 24Q4, 23Q2)"
    )
    args = parser.parse_args()

    # Store config for plugins to read
    _config.depmap_version = args.depmap_version

    print(f"sl-tools MCP server starting (DepMap {args.depmap_version})...", file=sys.stderr)
    discover_and_register(mcp_app)
    print("All plugins registered. Starting stdio transport.", file=sys.stderr)

    mcp_app.run(transport="stdio")


if __name__ == "__main__":
    main()
