#!/usr/bin/env python3
"""Print the merged jarbas config and the files it came from.

Read this first in a planning run: `overlays` names the skills whose HOOKS.md
the plan must follow, and `extensions` shows what gather.py will run.

Usage: config.py
"""

from __future__ import annotations

import json
import sys

from _common import CONFIG, config_paths


def main() -> int:
    files = [{"path": str(p), "exists": p.exists()} for p in config_paths()]
    print(json.dumps({"files": files, "config": CONFIG}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
