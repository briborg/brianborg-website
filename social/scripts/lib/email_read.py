"""Reads approval replies from Gmail over IMAP, using the SAME app password as
sending. Lets the pipeline close the loop (draft email out, approval reply in,
post to X) with one credential and no extra OAuth.
"""

import email
import imaplib
import os
import re
from email.header import decode_header

IMAP_HOST = "imap.gmail.com"
DRAFT_SUBJECT_MARKER = "X post drafts for review"

# Cut quoted history out of a reply so we only parse what Brian actually typed.
_QUOTE_START = re.compile(
    r"^\s*(On .*wrote:|-{3,}\s*Original Message|From:\s|>.*)", re.I | re.M
)


def _decode(s) -> str:
    if not s:
        return ""
    parts = decode_header(s)
    out = []
    for txt, enc in parts:
        out.append(txt.decode(enc or "utf-8", "replace") if isinstance(txt, bytes) else txt)
    return "".join(out)


def _plain_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "replace")


def strip_quote(body: str) -> str:
    """Return only the new text above the quoted original."""
    m = _QUOTE_START.search(body)
    return (body[: m.start()] if m else body).strip()


def fetch_unseen_replies(owner: str, mark_seen: bool = True) -> list[dict]:
    """Return unseen INBOX replies to a draft email, FROM the owner only.
    Marks each returned message \\Seen so it isn't processed twice.
    Each dict: {uid, subject, body (quote-stripped)}.
    """
    user = os.environ["GMAIL_USER"]
    pw = os.environ["GMAIL_APP_PASSWORD"]
    out = []
    M = imaplib.IMAP4_SSL(IMAP_HOST)
    try:
        M.login(user, pw)
        M.select("INBOX")
        # Unseen replies whose subject carries the draft marker.
        typ, data = M.search(None, 'UNSEEN', 'SUBJECT', f'"{DRAFT_SUBJECT_MARKER}"')
        if typ != "OK":
            return out
        for uid in data[0].split():
            # BODY.PEEK doesn't set \Seen, so a dry-run can read without consuming.
            typ, msgdata = M.fetch(uid, "(RFC822)" if mark_seen else "(BODY.PEEK[])")
            if typ != "OK":
                continue
            msg = email.message_from_bytes(msgdata[0][1])
            sender = _decode(msg.get("From", ""))
            if owner.lower() not in sender.lower():
                continue  # only act on Brian's own replies
            out.append({
                "uid": uid,
                "subject": _decode(msg.get("Subject", "")),
                "body": strip_quote(_plain_body(msg)),
            })
            if mark_seen:
                M.store(uid, "+FLAGS", "\\Seen")
    finally:
        try:
            M.logout()
        except Exception:
            pass
    return out


def parse_reply(body: str) -> tuple[set, dict, bool]:
    """Parse an approval reply. Returns (approved_ids, edits {id: new_text}, approve_all).

    Recognized, case-insensitive, line by line:
      approve all          -> approve every post in the batch (approve_all=True)
      approve all 3        -> ALSO approve_all; the word "all" wins over the digit
      approve 1, 3, 7      -> approve those ids
      1, 3, 7              -> a numbers-only line also approves
      edit 2: new text     -> replace post 2's text and approve it
    Anything else is ignored, so a reply with no numbers/all posts nothing.

    The caller expands approve_all to the batch's real ids — parse_reply has no
    knowledge of how many posts the batch contains.
    """
    approved: set = set()
    edits: dict = {}
    approve_all = False
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"edit\s+(\d+)\s*[:\-]\s*(.+)", line, re.I)
        if m:
            pid = int(m.group(1))
            edits[pid] = m.group(2).strip()
            approved.add(pid)
            continue
        m = re.match(r"approve\b(.*)", line, re.I)
        if m:
            rest = m.group(1)
            if re.search(r"\ball\b", rest, re.I):  # "approve all" / "approve all 3"
                approve_all = True
            approved.update(int(n) for n in re.findall(r"\d+", rest))
            continue
        if re.fullmatch(r"\s*all\s*", line, re.I):  # a bare "all" line
            approve_all = True
            continue
        if re.fullmatch(r"[\d,\s]+", line):  # a bare list of numbers
            approved.update(int(n) for n in re.findall(r"\d+", line))
    return approved, edits, approve_all


def date_from_subject(subject: str) -> str | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", subject)
    return m.group(1) if m else None
