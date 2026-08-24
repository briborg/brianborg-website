#!/usr/bin/env python3
"""generate_x_posts.py — Generate a batch of X / Twitter posts in Brian's
personal voice, then email them for review (or preview to stdout).

This is the brianborg-website analogue of OnPath's generate_posts.py:
  - X-only (not LinkedIn/FB)
  - Brian's PERSONAL first-person voice (corpus/brian-voice.md)
  - Three lanes: founder journey, building in public with AI, AI + code quality
  - Review by EMAIL reply instead of Slack reactions

Usage:
  python generate_x_posts.py                 # preview 7 posts to stdout + save draft file
  python generate_x_posts.py --count 10      # generate 10
  python generate_x_posts.py --email         # also email the batch for review

Env: ANTHROPIC_API_KEY (+ GMAIL_USER / GMAIL_APP_PASSWORD when --email).
All loaded from operations/.env automatically.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import context  # noqa: E402

X_HARD_LIMIT = 280  # single-tweet ceiling on the free tier

PROMPT_TEMPLATE = """You are drafting posts for Brian Borg's PERSONAL X / Twitter account.
You are not a brand account. You are Brian, writing as himself. The bar: a sharp
peer who follows Brian must believe HE wrote every one of these. If a post reads
like a content tool wrote it, it has failed.

Today is {current_date}. The current year is {current_year}. Any "now" reference
must be {current_year}. Do not write any other year as if it is the present.

TENURE RULE — Never write a specific start year (not "2009", not "1999", and no
"since 2009"/"since 1999"). Use soft phrasing only: "almost 20 years running OnPath",
"nearly 30 years in dev/QA", "a decade ago". The only year allowed to appear in any
post is {current_year}, and only if it genuinely needs a year at all (most do not).

Generate {count} standalone X posts. Spread them across Brian's three lanes,
roughly evenly, mixed in order (do not group by lane):
  1. Founder / builder journey
  2. Building in public with AI
  3. AI + code quality

Use the SPECIFIC facts and angles from the source material below. Pull a concrete
detail rather than making a generic claim. Never invent a client, company, or
person name.

HARD RULES (a post that breaks any of these will be thrown out):
- Each post is a SINGLE tweet, {limit} characters MAX. Shorter is better. Count characters.
- No em-dashes. No hashtags. No emoji (one rarely, never a rocket).
- No AI-content-bot tells: no "Here's the thing", no "Let that sink in", no
  "It's not just X, it's Y", no "leverage/unlock/delve/seamless/robust/game-changer",
  no "in today's fast-paced", no throat-clearing "As a founder,".
- Vary the rhythm. Some posts one line. Use contractions. Have a real opinion.
- At most ONE post may be a short thread; if so, return its parts joined by the
  literal token "\\n---\\n" inside the "text" field and set "thread": true.

VOICE (tov-social) — the examples below, if present, are real sentences Brian
actually wrote (PII-scrubbed). Match their rhythm and directness directly;
don't paraphrase them into a description of his tone. Complete sentences over
clipped fragments, a little warmth is fine, still no corporate filler.

{voice_examples}

{corpus}

Return ONLY a JSON array of {count} objects, each:
  - "text": the post, ready to publish
  - "lane": one of "founder", "building", "quality"
  - "thread": true only if it is a multi-part thread, else false
No markdown, no code fence, just the JSON array.
"""

# Seatbelts — same philosophy as OnPath generate_posts.py. The model has the
# rules in-prompt; these catch regressions before anything reaches Brian.
BANNED_BIO_PHRASES = ["27 years", "17 years", "since 1999", "since 2009", "15 years"]

# AI-content-bot tells. Lowercased substring match.
AI_SLOP = [
    "here's the thing", "let that sink in", "read that again", "it's not just",
    "isn't dead", "leverage", "unlock", "delve", "seamless", "robust",
    "game-changer", "game changer", "in today's fast-paced", "as a founder,",
    "as someone who", "supercharge", "navigate the landscape", "at the end of the day",
    "double down", "north star", "dive in", "buckle up", "the future is",
]

YEAR_RE = re.compile(r"\b(20\d{2})\b")
EM_DASH_RE = re.compile(r"[—–]")  # em dash, en dash
HASHTAG_RE = re.compile(r"(?:^|\s)#\w+")


def _post_len(text: str) -> int:
    """Longest single part (threads are split on the literal \\n---\\n token)."""
    return max(len(part.strip()) for part in text.split("\\n---\\n"))


def validate(posts: list[dict], current_year: int) -> None:
    errors = []
    for i, post in enumerate(posts, 1):
        text = post.get("text", "")
        low = text.lower()
        for ph in BANNED_BIO_PHRASES:
            if ph in low:
                errors.append(f"#{i}: banned bio phrase {ph!r}")
        for ph in AI_SLOP:
            if ph in low:
                errors.append(f"#{i}: AI-slop phrase {ph!r}")
        if EM_DASH_RE.search(text):
            errors.append(f"#{i}: contains an em/en dash")
        if HASHTAG_RE.search(text):
            errors.append(f"#{i}: contains a hashtag")
        for m in YEAR_RE.finditer(text):
            if int(m.group(1)) != current_year:
                errors.append(f"#{i}: suspicious year {m.group(1)} (current {current_year})")
        n = _post_len(text)
        if n > X_HARD_LIMIT:
            errors.append(f"#{i}: {n} chars exceeds {X_HARD_LIMIT} limit")
    if errors:
        raise ValueError(
            "CONTENT VALIDATION FAILED — nothing sent:\n  " + "\n  ".join(errors)
            + "\n\nRe-run to regenerate (the model occasionally regresses)."
        )


LANE_LABEL = {"founder": "Founder / journey", "building": "Building in public", "quality": "AI + code quality"}


def render_text(posts: list[dict], date: str) -> str:
    lines = [f"X post drafts — {date}", "=" * 40, ""]
    for i, p in enumerate(posts, 1):
        lane = LANE_LABEL.get(p.get("lane"), p.get("lane", "?"))
        tag = " [THREAD]" if p.get("thread") else ""
        lines.append(f"[{i}] {lane}{tag}  ({_post_len(p['text'])} chars)")
        lines.append(p["text"].replace("\\n---\\n", "\n  ---\n"))
        lines.append("")
    lines += ["", "TO APPROVE: reply to this email with  approve 1, 3, 7  — those post to X automatically.",
              "TO EDIT: reply with  edit 2: <your new text>  and the edited version posts.",
              "Reply with nothing (or no numbers) and nothing posts."]
    return "\n".join(lines)


def render_html(posts: list[dict], date: str) -> str:
    cards = []
    for i, p in enumerate(posts, 1):
        lane = LANE_LABEL.get(p.get("lane"), p.get("lane", "?"))
        tag = ' <span style="color:#a855f7">· thread</span>' if p.get("thread") else ""
        body = p["text"].replace("\\n---\\n", "<hr style='border:none;border-top:1px dashed #ccc;margin:8px 0'>").replace("\n", "<br>")
        n = _post_len(p["text"])
        color = "#16a34a" if n <= X_HARD_LIMIT else "#dc2626"
        cards.append(f"""
        <div style="border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin:0 0 14px">
          <div style="font:600 12px -apple-system,sans-serif;color:#6b7280;text-transform:uppercase;letter-spacing:.04em">
            #{i} · {lane}{tag} · <span style="color:{color}">{n}/280</span>
          </div>
          <div style="font:16px/1.5 -apple-system,Segoe UI,sans-serif;color:#111;margin-top:8px;white-space:pre-wrap">{body}</div>
        </div>""")
    return f"""<div style="max-width:600px;margin:0 auto;font-family:-apple-system,sans-serif">
      <h2 style="font-size:18px;color:#111">X post drafts — {date}</h2>
      <p style="color:#6b7280;font-size:14px"><b>To approve:</b> reply to this email with
      <code style="background:#f3f4f6;padding:1px 5px;border-radius:4px">approve 1, 3, 7</code> and those post to X automatically.
      <b>To edit:</b> reply <code style="background:#f3f4f6;padding:1px 5px;border-radius:4px">edit 2: your new text</code>.
      Reply with no numbers and nothing posts.</p>
      {''.join(cards)}
    </div>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=7)
    ap.add_argument("--email", dest="email", action="store_true", help="email the batch for review")
    ap.add_argument("--no-email", dest="email", action="store_false")
    ap.set_defaults(email=False)
    args = ap.parse_args()

    context.load_env()
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")

    prompt = PROMPT_TEMPLATE.format(
        count=args.count,
        limit=X_HARD_LIMIT,
        corpus=context.load_corpus(),
        voice_examples=context.load_real_voice_examples(),
        current_date=now.strftime("%A, %B %d, %Y"),
        current_year=now.year,
    )

    print(f"  Generating {args.count} X posts...", file=sys.stderr)
    posts = context.generate_json(prompt, max_tokens=4096)
    validate(posts, now.year)
    print(f"  Generated + validated {len(posts)} posts", file=sys.stderr)

    # Save the human-readable draft + a structured batch JSON. The JSON is what
    # process_x_posts.py reads when an approval reply comes back: each post gets a
    # stable 1-based id and a posted_id slot (null until posted, for idempotency).
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(pkg_root, "drafts"), exist_ok=True)
    draft_path = os.path.join(pkg_root, "drafts", f"x-drafts-{date}.txt")
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(render_text(posts, date))

    batch = {
        "date": date,
        "posts": [
            {"id": i, "text": p["text"], "lane": p.get("lane"),
             "thread": bool(p.get("thread")), "posted_id": None}
            for i, p in enumerate(posts, 1)
        ],
    }
    json_path = os.path.join(pkg_root, "drafts", f"x-drafts-{date}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2)
    print(f"  Saved {draft_path} + {json_path}", file=sys.stderr)

    if args.email:
        from lib import email_send
        try:
            to = email_send.send_email(
                subject=f"X post drafts for review — {date}",
                html_body=render_html(posts, date),
                text_body=render_text(posts, date),
            )
            print(f"  Emailed drafts to {to}", file=sys.stderr)
            from lib import queue_store
            q = queue_store.load()
            n = queue_store.add_drafts(q, date, posts, now.isoformat(timespec="seconds"))
            queue_store.save(q)
            print(f"  Queued {n} drafts for the daily drip (awaiting approval)", file=sys.stderr)
        except email_send.EmailNotConfigured as e:
            print(f"  SKIPPED email (not configured yet): {e}", file=sys.stderr)
    else:
        print("\n" + render_text(posts, date))


if __name__ == "__main__":
    main()
