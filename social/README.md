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
| `scripts/process_x_posts.py` | Reads approval replies, posts approved drafts to X | Confirmation email |

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

# read approval replies and post approved drafts to X:
./.venv/bin/python scripts/process_x_posts.py            # live
./.venv/bin/python scripts/process_x_posts.py --dry-run  # parse only, post nothing

# confirm WHICH X account the tokens post as (run before relying on auto-post):
./.venv/bin/python scripts/whoami_x.py
```

## Review + approval workflow (how you approve)

1. A draft email lands in your inbox with numbered posts.
2. **Reply to that email** to signal approval:
   - `approve 1, 3, 7` posts those three to X.
   - `edit 2: your new text` posts an edited version of post 2.
   - a bare line of numbers (`1 3 7`) also approves.
   - reply with no numbers (or "looks good") and nothing posts.
3. `process_x_posts.py` runs on a schedule, reads your reply over IMAP, posts the
   approved drafts to X via the API, and emails a confirmation with the links.

It only acts on replies from your own address, never posts a draft twice (tracked by
`posted_id` in the batch JSON), and rejects an edited post over 280 chars. The same Gmail
app password powers both sending and reading replies, so no extra OAuth is needed. Posting
uses the X API (free tier allows posting); it never follows or likes anything.

## Scheduling

GitHub Actions workflows (in this repo's `.github/workflows/`):
- `x-generate.yml` — Monday morning, generates the week's post batch
- `x-engage.yml` — daily, sends the engage-list
- `x-process.yml` — twice daily, posts approved drafts

These need repo secrets set on `briborg/brianborg-website`: `ANTHROPIC_API_KEY`,
`GMAIL_USER`, `GMAIL_APP_PASSWORD`, `REVIEW_EMAIL_TO`, and `X_API_KEY` / `X_API_SECRET` /
`X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` for the process job. Jobs degrade quietly (exit
green with a warning) until the Gmail secret is set, so they don't spam failures before setup.

## Files

```
social/
  corpus/
    brian-voice.md      # how Brian writes (weight 3.0)
    brian-themes.md     # source material / facts (weight 2.0)
  seed_accounts.json    # curated accounts for the engage-list (grow this)
  scripts/
    generate_x_posts.py     # draft posts -> email
    build_engage_list.py    # daily engage targets -> email
    process_x_posts.py      # read approvals -> post to X
    whoami_x.py             # which account do the X_* tokens post as?
    lib/{context,email_send,email_read,x_client}.py
  drafts/               # dated draft .txt + batch .json (gitignored)
  requirements.txt
  .env.example
```
