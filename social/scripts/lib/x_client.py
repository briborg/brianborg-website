"""Minimal X / Twitter posting client. Uses OAuth 1.0a user context with the
four X_* credentials already in operations/.env. Posting (POST /2/tweets) is
allowed on the X free tier; this never follows, likes, or does anything that
trips the platform-manipulation rules.
"""

import os

import requests
from requests_oauthlib import OAuth1

TWEETS_URL = "https://api.twitter.com/2/tweets"
THREAD_SEP = "\\n---\\n"  # literal token the generator uses to mark thread parts


class XNotConfigured(RuntimeError):
    pass


def _auth() -> OAuth1:
    keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise XNotConfigured(f"missing X creds: {', '.join(missing)}")
    return OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def post_tweet(text: str, in_reply_to: str | None = None) -> str:
    """Post a single tweet; return its id. Raises on API error."""
    payload: dict = {"text": text}
    if in_reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": in_reply_to}
    resp = requests.post(TWEETS_URL, auth=_auth(), json=payload, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"X API {resp.status_code}: {resp.text[:300]}")
    return resp.json()["data"]["id"]


def post(text: str) -> str:
    """Post a post or a thread. Returns the id of the FIRST tweet.

    Threads are marked by the generator with the literal token between parts;
    each subsequent part is posted as a reply to the previous one.
    """
    parts = [p.strip() for p in text.split(THREAD_SEP) if p.strip()]
    first_id = prev_id = post_tweet(parts[0])
    for part in parts[1:]:
        prev_id = post_tweet(part, in_reply_to=prev_id)
    return first_id


def whoami() -> str:
    """Return the handle the X_* tokens authenticate as. Run this BEFORE relying
    on auto-post so personal-voice posts don't land on the wrong account."""
    resp = requests.get("https://api.twitter.com/2/users/me", auth=_auth(), timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"X API {resp.status_code}: {resp.text[:300]}")
    d = resp.json()["data"]
    return f"@{d['username']} ({d.get('name', '')}) id={d['id']}"
