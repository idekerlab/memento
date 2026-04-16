"""
Plugin registry for the sl-tools MCP server.

Discovers and registers tool plugins, and provides unified
cross-database tools (coverage check, ensure data).
"""

import importlib
import traceback

PLUGIN_MODULES = [
    "tools.sl_tools.depmap.mcp_tools",
    "tools.sl_tools.gdsc.mcp_tools",
    # Additional plugins (biogrid, encode, lincs, msigdb, ccle, tcga, edison)
    # are available in the upstream collaborator repo and can be vendored here
    # when a concrete R. Corona query needs them. Enable by copying the plugin
    # directory from the upstream repo, adding its import path to this list,
    # and downloading the associated data per its data_manifest.json.
]

# Registered plugins: name -> {check_coverage, ensure_data}
_plugins = {}


def register_plugin(name, check_coverage_fn=None, ensure_data_fn=None):
    """Called by each plugin's register() to register its cross-database functions."""
    _plugins[name] = {
        "check_coverage": check_coverage_fn,
        "ensure_data": ensure_data_fn,
    }


def discover_and_register(mcp_app):
    """Import each plugin module and call its register(mcp_app)."""
    for module_path in PLUGIN_MODULES:
        try:
            mod = importlib.import_module(module_path)
            mod.register(mcp_app)
            print(f"  Registered plugin: {module_path}")
        except Exception as e:
            print(f"  WARNING: Failed to register {module_path}: {e}")
            traceback.print_exc()

    # Register unified cross-database tools
    @mcp_app.tool()
    def mcp_check_coverage(genes: list[str], tools: list[str] | None = None) -> dict:
        """
        Check which genes have data across all registered databases.
        Returns a dict keyed by tool name, each containing per-gene coverage info.
        Optionally filter to specific tools (e.g. ["depmap", "biogrid"]).
        """
        results = {}
        for name, plugin in _plugins.items():
            if tools and name not in tools:
                continue
            fn = plugin.get("check_coverage")
            if fn:
                try:
                    results[name] = fn(genes)
                except Exception as e:
                    results[name] = {"error": str(e)}
        return results

    @mcp_app.tool()
    def mcp_ensure_all_data(tools: list[str] | None = None) -> dict:
        """
        Ensure data files are available for all registered databases.
        Returns a dict keyed by tool name with status info.
        Optionally filter to specific tools.
        """
        results = {}
        for name, plugin in _plugins.items():
            if tools and name not in tools:
                continue
            fn = plugin.get("ensure_data")
            if fn:
                try:
                    results[name] = fn()
                except Exception as e:
                    results[name] = {"error": str(e)}
        return results
