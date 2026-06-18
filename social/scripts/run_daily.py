#!/usr/bin/env python3
"""run_daily.py — the once-per-day drip.

Each run:
  1. Reads unseen approval replies and flips matching queued drafts to approved.
  2. Publishes the SINGLE oldest approved post (one per day), unless something
     already went out today.
  3. Emails a short confirmation and rewrites queue.json (the workflow commits it).

Replaces the old "post everything the moment you approve" behavior so posts
trickle out like a human instead of in a bot-like burst.

Usage:
  python run_daily.py            # live
  python run_daily.py --dry-run  # read + plan, post nothing, change nothing
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import context, email_read, queue_store  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    context.load_env()
    owner = os.environ.get("REVIEW_EMAIL_TO") or os.environ.get("GMAIL_USER", "")
    if not owner or not os.environ.get("GMAIL_APP_PASSWORD"):
        print("  SKIPPED: GMAIL_USER / GMAIL_APP_PASSWORD not set.", file=sys.stderr)
        return

    today = datetime.now().strftime("%Y-%m-%d")
    q = queue_store.load()

    # 1. Pull in any new approvals (dry-run uses peek so it won't consume them).
    replies = email_read.fetch_unseen_replies(owner, mark_seen=not args.dry_run)
    newly = []
    for r in replies:
        date = email_read.date_from_subject(r["subject"])
        if not date:
            continue
        approved, edits, approve_all = email_read.parse_reply(r["body"])
        newly += queue_store.approve(q, date, approved, approve_all, edits)
    if newly:
        print(f"  Approved {len(newly)} item(s) from replies: {sorted(newly)}", file=sys.stderr)

    # 2. Publish one — unless we already posted today.
    posted_line = None
    if queue_store.posted_today(q, today):
        print("  Already posted today — holding (1/day).", file=sys.stderr)
    else:
        item = queue_store.next_to_post(q)
        if not item:
            print("  Nothing approved is waiting to post.", file=sys.stderr)
        elif args.dry_run:
            posted_line = f"WOULD POST {item['batch_date']}#{item['batch_id']}: {item['text'][:60]}..."
            print("  " + posted_line, file=sys.stderr)
        else:
            from lib import x_client
            try:
                tid = x_client.post(item["text"])
                item["status"] = "posted"
                item["posted_id"] = tid
                item["posted_at"] = datetime.now().isoformat(timespec="seconds")
                posted_line = f"Posted {item['batch_date']}#{item['batch_id']} -> https://x.com/briborg/status/{tid}"
                print("  " + posted_line, file=sys.stderr)
            except Exception as e:
                print(f"  POST FAILED: {e}", file=sys.stderr)
                posted_line = f"POST FAILED: {e}"

    c = queue_store.counts(q)
    print(f"  Queue now: {c['approved']} approved waiting, {c['draft']} unapproved drafts, "
          f"{c['posted']} posted all-time", file=sys.stderr)

    if not args.dry_run:
        queue_store.save(q)
        # Confirmation email only when something actually published.
        if posted_line and posted_line.startswith("Posted"):
            from lib import email_send
            remaining = c["approved"]
            body = (f"{posted_line}\n\n{remaining} approved post(s) still queued — "
                    f"the next one goes out tomorrow.")
            try:
                email_send.send_email("X post published", f"<pre>{body}</pre>", body)
            except Exception as e:
                print(f"  (confirmation email failed: {e})", file=sys.stderr)


if __name__ == "__main__":
    main()
