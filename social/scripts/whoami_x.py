#!/usr/bin/env python3
"""whoami_x.py — print which X account the X_* tokens authenticate as.

Run this BEFORE relying on auto-post, so personal-voice posts don't land on the
wrong account (e.g. the @OnPathTesting corporate account instead of a personal
handle). Read-only: it never posts, follows, or likes.

  python scripts/whoami_x.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import context, x_client  # noqa: E402

context.load_env()
try:
    print("Posts will publish as:", x_client.whoami())
except Exception as e:
    print(f"Could not verify X account: {e}", file=sys.stderr)
    sys.exit(1)
