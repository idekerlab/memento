"""Shared JSON serialization helpers for MCP tool responses."""

import math


def sanitize_floats(d):
    """
    Recursively convert NaN/Inf/-Inf to None for JSON safety.

    GDSC and other tools may produce NaN values in float fields
    which are not valid JSON. This function sanitizes them.
    """
    if isinstance(d, dict):
        return {k: sanitize_floats(v) for k, v in d.items()}
    if isinstance(d, list):
        return [sanitize_floats(v) for v in d]
    if isinstance(d, float):
        if math.isnan(d) or math.isinf(d):
            return None
    return d
