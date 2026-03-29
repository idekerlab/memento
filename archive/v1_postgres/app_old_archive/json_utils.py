"""
JSON utilities for Memento Access server.
"""

import json
import datetime
from typing import Any

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)
