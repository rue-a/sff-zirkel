# %%
import json
import re
import os
from datetime import datetime
from pathlib import Path

import requests

from utilities import (
    notice,
    warn,
    join_and,
    extract_field,
    load_books,
    load_club,
    save_books,
    post_issue_comment,
)

# ---------- Configuration ----------
BOOKS_FILE = Path("data/books.json")
CLUB_FILE = Path("data/club.json")
COVERS_PATH = Path("covers")
NOTICES = []
WARNINGS = []


def add_book(isbn, proposer, participants, review_date):
    books = load_books(BOOKS_FILE)

    # Fetch metadata to validate ISBN exists
    meta = fetch_openlibrary_metadata(isbn, books)

    if meta:
        ratings = {
            name: None for name in [participant.title() for participant in participants]
        }

        reviews = {
            name: None for name in [participant.title() for participant in participants]
        }

        new_book = {
            "query": isbn,
            "review_date": review_date,
            "proposer": proposer.title(),
            "ratings": ratings,
            "reviews": reviews,
            "meta": meta,
        }

        books.append(new_book)
        save_books(BOOKS_FILE, books)
        print(f"✔ Added book {isbn}")
    return meta


def build_summary(
    *,
    query: str,
    review_date: str,
    proposer: str,
    participants: list[str],
    meta: dict | None,
    warnings: list[str],
    notices: list[str],
) -> str:
    """
    Build a human-readable Markdown summary of what happened,
    including warnings (if any).
    """

    prepared = requests.Request(
        "GET", f"{OPEN_LIBRARY_URL}/search.json", params={"q": query, "limit": LIMIT}
    ).prepare()
    query_url = prepared.url

    lines = ["# SUMMARY"]
    lines.append(f"**Query:** {query} ({query_url})\n\n")

    if not meta:
        lines.append("❌ **No book entry created**\n")
    else:
        # Header
        lines.append("✅ **Book entry created**\n")

        # Core info

        lines.append("## Metadata")
        lines.append("### Fetched Data")

        for key, val in meta.items():
            lines.append(f"**{key}:** {val}")

        lines.append("### Review Data")
        if review_date:
            lines.append(f"**Review date:** {review_date}")

        if proposer:
            lines.append(f"**Proposed by:** {proposer}")

        if participants:
            lines.append(f"**Participants:** {', '.join(participants)}")

    # Warnings section
    if warnings:
        lines.append("### Warnings")
        lines.append("\n> [!WARNING]\n>")

        for w in warnings:
            lines.append(f"> - {w}")

    # Warnings section
    if notices:
        lines.append("### Notes")
        lines.append("\n> [!NOTE]\n>")

        for n in notices:
            lines.append(f"> - {n}")

    return "\n".join(lines)


def parse_issue():
    """
    Parse GitHub issue payload and add a review.
    Extracts book_id, reviewer, grade, and text from issue.
    Emits warnings for placeholder values and invalid dates.
    """

    event_path = Path(os.environ.get("GITHUB_EVENT_PATH", ""))

    if not event_path.exists():
        raise RuntimeError(
            "GITHUB_EVENT_PATH not found. Are you running in GitHub Actions?"
        )

    with event_path.open("r", encoding="utf-8") as f:
        event = json.load(f)

    issue = event.get("issue", {})
    title = issue.get("title", "").strip()
    body = issue.get("body", "")

    # -------------------------------
    # ISBN from title
    # -------------------------------
    # Keep digits and X only (ISBN-10 or 13)
    isbn = re.sub(r"[^0-9X]", "", extract_field(body, "ISBN"))
    query = isbn

    # if isbn is not valid, try with entered title
    if len(query) not in (10, 13):
        fallback = title.strip()
        WARNINGS.append(
            warn((f"No valid ISBN detected, trying issue title: `{fallback}`"))
        )
        query = fallback

    # -------------------------------
    # Metadata from body
    # -------------------------------
    review_date = extract_field(body, "review date")
    proposer = extract_field(body, "proposer")
    guests_raw = extract_field(body, "guests")

    # -------------------------------
    # Detect placeholder / defaults
    # -------------------------------
    defaults = {
        "review date": "YYYY-MM-DD",
        "proposer": "namehere",
        "guests": "namehere, namehere, namehere",
    }

    if review_date == defaults["review date"]:
        WARNINGS.append(warn(("Review date is still placeholder (`YYYY-MM-DD`).")))

    if proposer == defaults["proposer"]:
        WARNINGS.append(warn(("Proposer is still placeholder (`namehere`).")))

    if guests_raw == defaults["guests"]:
        WARNINGS.append(warn(("Guests are still placeholder, not adding guests.")))
        guests_raw = ""

    # -------------------------------
    # Date validation (non-fatal)
    # -------------------------------
    if review_date:
        try:
            datetime.strptime(review_date, "%Y-%m-%d")
        except ValueError:
            WARNINGS.append(
                warn((f"Review date `{review_date}` is not in YYYY-MM-DD format."))
            )

    # -------------------------------
    # Participants parsing
    # -------------------------------

    club_meta = load_club(CLUB_FILE)
    participants = club_meta["permanent_members"] + [
        p.strip() for p in guests_raw.split(",") if p.strip()
    ]

    if not participants:
        WARNINGS.append(warn(("No participants specified.")))

    # -------------------------------
    # Add book
    # -------------------------------
    book_meta = add_book(
        isbn=query,
        proposer=proposer,
        participants=participants,
        review_date=review_date,
    )

    summary = build_summary(
        query=query,
        review_date=review_date,
        proposer=proposer,
        participants=participants,
        meta=book_meta,
        warnings=WARNINGS,
        notices=NOTICES,
    )

    post_issue_comment(summary)
    print(f"::notice::{summary}")

    return bool(book_meta)


if __name__ == "__main__":
    title_added = parse_issue()
    # Exit code 1 if nothing was added (optional)
    exit(0 if title_added else 1)
