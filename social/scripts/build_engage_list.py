#!/usr/bin/env python3
"""build_engage_list.py — The SAFE X growth engine.

Instead of auto-following 100 people a day (which violates X's spam rules and
risks getting Brian's personal account locked), this emails Brian a focused
daily list of high-relevance tech accounts to engage with BY HAND, each with a
suggested reply angle in his voice. The script does the research; Brian does the
human, account-safe part.

Pulls from seed_accounts.json. Rotates a daily slice so coverage cycles over
time without repeating. Grow the seed list to widen the pool.

Usage:
  python build_engage_list.py               # preview today's list to stdout
  python build_engage_list.py --count 15    # 15 accounts today
  python build_engage_list.py --email       # email the list
"""

import argparse
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import context  # noqa: E402


def flatten_accounts(seed: dict) -> list[dict]:
    out = []
    for cat, accts in seed.get("categories", {}).items():
        for a in accts:
            out.append({**a, "category": cat})
    return out


def todays_slice(accounts: list[dict], count: int) -> list[dict]:
    """Deterministic rotating window keyed to the date, so the list cycles
    through everyone over successive days rather than repeating."""
    if not accounts:
        return []
    n = len(accounts)
    count = min(count, n)
    start = (date.today().toordinal() * count) % n
    return [accounts[(start + i) % n] for i in range(count)]


ANGLE_PROMPT = """For each X account below, write ONE specific reply angle Brian Borg could use
to engage authentically. Brian is the founder of OnPath Testing, nearly 30 years
in dev/QA, building in public with AI, deeply opinionated about whether AI-generated
code actually works.

The angle must be something Brian would genuinely say in HIS voice: a real take, a
sharp question from his QA lens, or a hard-won counterpoint. Not flattery, not
"great post!", not generic. One or two sentences. No em-dashes, no hashtags.

Brian's voice + lanes:
{corpus}

Accounts:
{accounts}

Return ONLY a JSON array, one object per account in the same order:
  - "handle": the handle
  - "angle": the reply angle, in Brian's voice
No markdown, just the JSON array.
"""


def render_text(items: list[dict], d: str) -> str:
    lines = [f"X engage-list — {d}", "=" * 40,
             "Follow + reply to these by hand. Human-paced, account-safe.", ""]
    for i, it in enumerate(items, 1):
        lines.append(f"[{i}] @{it['handle']} — {it.get('name', '')}  ({it['category']})")
        lines.append(f"    why: {it.get('why', '')}")
        lines.append(f"    reply angle: {it.get('angle', '(none)')}")
        lines.append("")
    return "\n".join(lines)


def render_html(items: list[dict], d: str) -> str:
    rows = []
    for i, it in enumerate(items, 1):
        rows.append(f"""
        <div style="border:1px solid #e5e7eb;border-radius:10px;padding:14px;margin:0 0 12px">
          <div style="font:600 15px -apple-system,sans-serif">
            <a href="https://x.com/{it['handle']}" style="color:#2563eb;text-decoration:none">@{it['handle']}</a>
            <span style="color:#6b7280;font-weight:400">· {it.get('name','')}</span>
          </div>
          <div style="font:13px -apple-system,sans-serif;color:#6b7280;margin:4px 0">{it.get('why','')}</div>
          <div style="font:14px/1.5 -apple-system,sans-serif;color:#111;background:#f9fafb;border-radius:6px;padding:8px 10px;margin-top:6px">
            <b style="color:#a855f7">Reply angle:</b> {it.get('angle','')}
          </div>
        </div>""")
    return f"""<div style="max-width:600px;margin:0 auto;font-family:-apple-system,sans-serif">
      <h2 style="font-size:18px;color:#111">X engage-list — {d}</h2>
      <p style="color:#6b7280;font-size:14px">Follow and reply to these by hand today. Human-paced and
      account-safe (no automation touches your account). The reply angles are starting points in your voice.</p>
      {''.join(rows)}
    </div>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--email", dest="email", action="store_true")
    ap.add_argument("--no-email", dest="email", action="store_false")
    ap.set_defaults(email=False)
    args = ap.parse_args()

    context.load_env()
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed = context.read_json(os.path.join(pkg_root, "seed_accounts.json"))

    items = todays_slice(flatten_accounts(seed), args.count)
    if not items:
        print("No accounts in seed_accounts.json", file=sys.stderr)
        return

    # Draft a reply angle for each in one batched call.
    accounts_block = "\n".join(
        f"- @{it['handle']} ({it.get('name','')}): {it.get('why','')}" for it in items
    )
    print(f"  Drafting reply angles for {len(items)} accounts...", file=sys.stderr)
    angles = context.generate_json(
        ANGLE_PROMPT.format(corpus=context.load_corpus(), accounts=accounts_block),
        max_tokens=2048,
    )
    by_handle = {a.get("handle", "").lstrip("@"): a.get("angle", "") for a in angles}
    for it in items:
        it["angle"] = by_handle.get(it["handle"], "")

    d = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(os.path.join(pkg_root, "drafts"), exist_ok=True)
    draft_path = os.path.join(pkg_root, "drafts", f"engage-list-{d}.txt")
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(render_text(items, d))
    print(f"  Saved {draft_path}", file=sys.stderr)

    if args.email:
        from lib import email_send
        try:
            to = email_send.send_email(
                subject=f"X engage-list — {d}",
                html_body=render_html(items, d),
                text_body=render_text(items, d),
            )
            print(f"  Emailed engage-list to {to}", file=sys.stderr)
        except email_send.EmailNotConfigured as e:
            print(f"  SKIPPED email (not configured yet): {e}", file=sys.stderr)
    else:
        print("\n" + render_text(items, d))


if __name__ == "__main__":
    main()
