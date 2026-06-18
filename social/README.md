# social — brianborg.com X pipeline

Personal X / Twitter content + audience-growth pipeline for **Brian Borg** (the human).
Lives in the brianborg-website repo (`social/`). X-only, first-person voice, review by
**email** instead of Slack. Modeled on OnPath's `social-posts/` pipeline.

The Astro site build ignores this directory; only `src/`+`public/` are deployed. The
scripts run on GitHub Actions (this repo) and locally.

## What it does

| Script | What it produces | Delivered |
|--------|------------------|-----------|
| `scripts/generate_x_posts.py` | A batch of X posts in Brian's voice across 3 lanes | Email for review |
| `scripts/build_engage_list.py` | A daily list of tech accounts to follow + reply angles | Email |
| `scripts/run_daily.py` | Reads approvals into the queue, posts ONE approved post/day | Confirmation email |

The three content lanes: **founder / builder journey**, **building in public with AI**,
**AI + code quality**.

## Why no auto-follow bot

The original ask was a script to auto-follow 100 people a day. That is not built, on purpose:
it violates X's platform-manipulation/spam rules ("aggressive following"), is the clearest
signal that gets a real-name account locked, isn't reliably available on the X API tier, and
converts poorly anyway. `build_engage_list.py` is the replacement: it does the research
(who to engage, what to say) and leaves the actual follow/reply to Brian, by hand, human-paced.
Grows a real audience without risking the account.

## Voice

`corpus/brian-voice.md` is the source of truth for how Brian sounds, including the banned
AI-content-bot tells. `corpus/brian-themes.md` holds the specific facts and angles posts draw
from. Add to the themes file over time to keep posts fresh. The generator also runs hard
seatbelts (no em-dashes, no hashtags, no AI-slop phrases, 280-char limit, correct year,
soft tenure numbers) and aborts before sending if any post regresses.

## Setup (one-time)

1. **Python deps** (reuse a venv or make one):
   ```
   python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
   ```
2. **Email delivery** — add a Gmail app password to `~/Projects/onpath-org/operations/.env`:
   - Google Account > Security > 2-Step Verification > App passwords > generate one for "Mail"
   - Add `GMAIL_USER=brian@onpathtesting.com` and `GMAIL_APP_PASSWORD=<the password>` to the .env yourself.
   - Until that's set, run with `--no-email` (the default) to preview to stdout.

## Run it

```
# preview (no email needed):
./.venv/bin/python scripts/generate_x_posts.py --count 7
./.venv/bin/python scripts/build_engage_list.py --count 12

# email for review (after Gmail app password is set):
./.venv/bin/python scripts/generate_x_posts.py --count 7 --email
./.venv/bin/python scripts/build_engage_list.py --email

# daily drip: read approvals into the queue + post one approved post:
./.venv/bin/python scripts/run_daily.py            # live
./.venv/bin/python scripts/run_daily.py --dry-run  # read + plan only, post nothing

# confirm WHICH X account the tokens post as (run before relying on auto-post):
./.venv/bin/python scripts/whoami_x.py
```

## Review + approval workflow (how you approve)

1. A draft email lands in your inbox with numbered posts.
2. **Reply to that email** to signal approval:
   - `approve all` (or `approve all 3`) posts the entire batch.
   - `approve 1, 3, 7` posts those three to X.
   - `edit 2: your new text` posts an edited version of post 2.
   - a bare line of numbers (`1 3 7`) also approves.
   - reply with no numbers (or "looks good") and nothing posts.
3. Approved posts go into a queue and publish **one per day** (~11am Mountain) so they
   trickle out like a person posting through the week, not in a bot-like burst. `run_daily.py`
   reads your reply over IMAP, marks the matching posts approved, publishes the oldest one,
   and emails a confirmation with the link.

It only acts on replies from your own address, never posts twice (state tracked in
`queue.json`), enforces one post per day, and rejects an edited post over 280 chars. The same
Gmail app password powers both sending and reading replies. Posting uses the X API
(pay-per-use, ~1.5¢ per text post); it never follows or likes anything.

## Scheduling

GitHub Actions workflows (in this repo's `.github/workflows/`):
- `x-generate.yml` — Monday morning: generates the week's batch, emails it, enqueues drafts
- `x-engage.yml` — daily: sends the engage-list
- `x-daily.yml` — daily (~11am MT): reads approvals, posts ONE approved post, commits the queue

`queue.json` is the durable state (draft → approved → posted). The generate and daily jobs
commit it back to the repo (with `[skip ci]` so Netlify doesn't rebuild) and share a
`concurrency` group so they never clobber each other. All jobs need repo secrets on
`briborg/brianborg-website`: `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`,
`REVIEW_EMAIL_TO`, and the four `X_*` for posting. Jobs degrade quietly (exit green with a
warning) until the Gmail secret is set.

## Files

```
social/
  corpus/
    brian-voice.md      # how Brian writes (weight 3.0)
    brian-themes.md     # source material / facts (weight 2.0)
  seed_accounts.json    # curated accounts for the engage-list (grow this)
  queue.json            # durable post queue (draft -> approved -> posted); committed
  scripts/
    generate_x_posts.py     # draft posts -> email + enqueue
    build_engage_list.py    # daily engage targets -> email
    run_daily.py            # read approvals -> post ONE/day from the queue
    whoami_x.py             # which account do the X_* tokens post as?
    lib/{context,email_send,email_read,x_client,queue_store}.py
  drafts/               # dated draft .txt + batch .json (gitignored)
  requirements.txt
  .env.example
```
