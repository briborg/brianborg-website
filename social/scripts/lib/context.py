"""Shared helpers for the brianborg-x pipeline: env loading, corpus loading,
and the Anthropic call. Mirrors the OnPath social-posts approach but X-only and
keyed to Brian's PERSONAL voice.
"""

import glob
import json
import os
import re

# Canonical secret store (X_*, ANTHROPIC_API_KEY, GMAIL_*), per the global
# CLAUDE.md. Fallback for local runs; a repo-local social/.env wins if present,
# and CI injects real secrets as env vars (both files then skipped).
DEFAULT_ENV_PATH = os.path.expanduser("~/Projects/onpath-org/operations/.env")

MODEL = os.environ.get("BRIANBORG_X_MODEL", "claude-sonnet-4-6")


def _pkg_root() -> str:
    """social/ — two levels up from this file (scripts/lib/context.py)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_one(path: str) -> None:
    """Set KEY=VALUE pairs from one .env into os.environ without overwriting
    anything already set. Never prints values. No-op if the file is absent."""
    if not path or not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def load_env(path: str | None = None) -> None:
    """Load secrets: repo-local social/.env first (self-contained option), then
    the canonical operations/.env. Existing env vars always win, so CI ignores
    both files."""
    _load_one(os.path.join(_pkg_root(), ".env"))
    _load_one(path or DEFAULT_ENV_PATH)


def load_corpus() -> str:
    """Concatenate every corpus/*.md, highest weight first. The voice doc
    (weight 3.0) is the backbone; themes (2.0) are source material."""
    corpus_dir = os.path.join(_pkg_root(), "corpus")
    fm_weight = re.compile(r"weight:\s*([0-9.]+)")
    docs = []
    for p in glob.glob(os.path.join(corpus_dir, "*.md")):
        try:
            text = open(p, encoding="utf-8").read()
        except Exception:
            continue
        weight, body = 1.0, text
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        if m:
            w = fm_weight.search(m.group(1))
            weight = float(w.group(1)) if w else 1.0
            body = m.group(2)
        docs.append((weight, body.strip()))
    docs.sort(key=lambda d: d[0], reverse=True)
    return "\n\n---\n\n".join(b for _w, b in docs)


def anthropic_client():
    import anthropic
    return anthropic.Anthropic()


def generate_json(prompt: str, max_tokens: int = 4096):
    """Call the model and parse its reply as JSON (array or object).
    Strips a ```json fence if the model adds one."""
    client = anthropic_client()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


def read_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
