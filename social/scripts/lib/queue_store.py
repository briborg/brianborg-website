"""Durable post queue for the once-per-day drip.

Lifecycle of an item: draft (generated + emailed) -> approved (Brian replied)
-> posted (published to X, one per day). Stored in social/queue.json, committed
to the repo so state persists across stateless GitHub Actions runs.
"""

import json
import os

X_HARD_LIMIT = 280


def _path() -> str:
    pkg = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(pkg, "queue.json")


def load() -> dict:
    try:
        with open(_path(), encoding="utf-8") as f:
            q = json.load(f)
    except FileNotFoundError:
        q = {}
    q.setdefault("items", [])
    return q


def save(q: dict) -> None:
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2)


def _has(q: dict, batch_date: str, batch_id: int) -> bool:
    return any(i["batch_date"] == batch_date and i["batch_id"] == batch_id for i in q["items"])


def add_drafts(q: dict, batch_date: str, posts: list[dict], now_iso: str) -> int:
    """Append a freshly-generated batch as draft items. Idempotent by
    (batch_date, batch_id) so re-running generate for a date won't duplicate."""
    added = 0
    for p in posts:
        if _has(q, batch_date, p["id"]):
            continue
        q["items"].append({
            "batch_date": batch_date,
            "batch_id": p["id"],
            "lane": p.get("lane"),
            "thread": bool(p.get("thread")),
            "text": p["text"],
            "status": "draft",
            "posted_id": None,
            "posted_at": None,
            "enqueued_at": now_iso,
        })
        added += 1
    return added


def approve(q: dict, batch_date: str, approved_ids: set, approve_all: bool, edits: dict) -> list[int]:
    """Flip draft items of a batch to approved (applying any edits). Returns the
    batch_ids newly approved. Edits over the char limit are left as draft."""
    changed = []
    for i in q["items"]:
        if i["batch_date"] != batch_date or i["status"] != "draft":
            continue
        if approve_all or i["batch_id"] in approved_ids:
            if i["batch_id"] in edits:
                new = edits[i["batch_id"]]
                if max(len(p.strip()) for p in new.split("\\n---\\n")) > X_HARD_LIMIT:
                    continue  # too long; leave as draft, skip
                i["text"] = new
            i["status"] = "approved"
            changed.append(i["batch_id"])
    return changed


def next_to_post(q: dict) -> dict | None:
    """The oldest approved-not-yet-posted item (FIFO by batch date then id)."""
    pending = [i for i in q["items"] if i["status"] == "approved" and not i["posted_id"]]
    if not pending:
        return None
    pending.sort(key=lambda i: (i["batch_date"], i["batch_id"]))
    return pending[0]


def posted_today(q: dict, today: str) -> bool:
    """True if something already published today (enforces 1/day even on a
    manual re-trigger of the daily job)."""
    return any((i.get("posted_at") or "").startswith(today) for i in q["items"])


def counts(q: dict) -> dict:
    c = {"draft": 0, "approved": 0, "posted": 0}
    for i in q["items"]:
        c[i["status"]] = c.get(i["status"], 0) + 1
    return c
