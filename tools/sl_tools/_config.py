"""Runtime configuration shared across all tool plugins."""

import os
from pathlib import Path

# DepMap release version (set by mcp_server.py at startup via --depmap-version)
depmap_version: str = "26Q1"

# Base directory for tool data caches.
# Default lives under the NDEx cache root so it sits alongside the per-agent
# local-store caches (~/.ndex/cache/<agent>/). Override via SL_TOOLS_DATA_DIR
# (preferred) or the legacy SL_RETRO_DATA_DIR env var.
data_dir: Path = Path(
    os.environ.get(
        "SL_TOOLS_DATA_DIR",
        os.environ.get("SL_RETRO_DATA_DIR", str(Path.home() / ".ndex" / "cache" / "sl_tools_data")),
    )
)


def get_tool_cache_dir(tool_name: str) -> Path:
    """Return the data directory for a named tool, creating it if absent.

    Resolves to ``<data_dir>/<tool_name>/`` so a file like Model.csv lives at
    ``~/.ndex/cache/sl_tools_data/depmap/Model.csv``. No extra ``cache/``
    subdirectory — the outer path already sits under the ``.ndex/cache`` root.
    """
    path = data_dir / tool_name
    path.mkdir(parents=True, exist_ok=True)
    return path
