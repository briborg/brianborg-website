#!/usr/bin/env python3
"""process_x_posts.py — Close the loop: read Brian's approval replies and post
the approved drafts to X. The brianborg-x analogue of OnPath's process_posts.py,
but driven by email replies instead of Slack reactions.

Flow per run:
  1. Read unseen Gmail replies (from Brian) to a draft email.
  2. Parse which post numbers he approved (and any inline edits).
  3. Load that day's batch JSON, post the approved ones to X, record tweet ids.
  4. Email a confirmation with links.

Idempotent: a post with a recorded posted_id is never posted twice, even if a
run re-reads the same batch.

Usage:
  python process_x_posts.py            # live: read replies, post, confirm
  python process_x_posts.py --dry-run  # parse + show intended posts, post nothing
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import context, email_read  # noqa: E402

X_HARD_LIMIT = 280


def _longest_part(text: str) -> int:
    return max(len(p.strip()) for p in text.split("\\n---\\n"))


def batch_path(date: str) -> str:
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(pkg_root, "drafts", f"x-drafts-{date}.json")


def process_reply(reply: dict, dry_run: bool) -> dict:
    """Process one approval reply. Returns a summary dict."""
    date = email_read.date_from_subject(reply["subject"])
    if not date:
        return {"skipped": "no date in subject", "subject": reply["subject"]}
    path = batch_path(date)
    if not os.path.exists(path):
        return {"skipped": f"no batch file for {date}"}

    batch = json.load(open(path, encoding="utf-8"))
    approved, edits = email_read.parse_reply(reply["body"])
    by_id = {p["id"]: p for p in batch["posts"]}

    posted, skipped, errors = [], [], []
    for pid in sorted(approved):
        post = by_id.get(pid)
        if not post:
            errors.append(f"#{pid}: no such post"); continue
        if post.get("posted_id"):
            skipped.append(f"#{pid}: already posted"); continue
        text = edits.get(pid, post["text"])
        if _longest_part(text) > X_HARD_LIMIT:
            errors.append(f"#{pid}: edited text over {X_HARD_LIMIT} chars, not posted"); continue
        if dry_run:
            posted.append(f"#{pid}: WOULD POST -> {text[:60]}..."); continue
        from lib import x_client
        try:
            tweet_id = x_client.post(text)
            post["posted_id"] = tweet_id
            post["text"] = text  # persist the edited version actually posted
            posted.append(f"#{pid}: https://x.com/i/web/status/{tweet_id}")
        except Exception as e:
            errors.append(f"#{pid}: post failed — {e}")

    if not dry_run:
        json.dump(batch, open(path, "w", encoding="utf-8"), indent=2)
    return {"date": date, "posted": posted, "skipped": skipped, "errors": errors}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    context.load_env()
    owner = os.environ.get("REVIEW_EMAIL_TO") or os.environ.get("GMAIL_USER", "")
    if not owner or not os.environ.get("GMAIL_APP_PASSWORD"):
        print("  SKIPPED: GMAIL_USER / GMAIL_APP_PASSWORD not set — cannot read "
              "approval replies yet. Add them to enable auto-posting.", file=sys.stderr)
        return  # exit 0 so the scheduled job stays green until configured

    replies = email_read.fetch_unseen_replies(owner)
    print(f"  {len(replies)} unseen approval repl{'y' if len(replies)==1 else 'ies'}", file=sys.stderr)

    summaries = [process_reply(r, args.dry_run) for r in replies]
    posted_any = [s for s in summaries if s.get("posted")]

    for s in summaries:
        print("  " + json.dumps(s), file=sys.stderr)

    # Confirmation email (live runs that posted something).
    if posted_any and not args.dry_run:
        from lib import email_send
        lines = []
        for s in posted_any:
            lines.append(f"Batch {s['date']}:")
            lines += [f"  posted {x}" for x in s["posted"]]
            lines += [f"  skipped {x}" for x in s["skipped"]]
            lines += [f"  ERROR {x}" for x in s["errors"]]
        body = "\n".join(lines)
        try:
            email_send.send_email(
                subject="X posts published",
                html_body="<pre style='font:14px monospace'>" + body + "</pre>",
                text_body=body,
            )
        except Exception as e:
            print(f"  (confirmation email failed: {e})", file=sys.stderr)


if __name__ == "__main__":
    main()
