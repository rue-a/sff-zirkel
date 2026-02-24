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
    failed = False

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
    # review data from body
    # -------------------------------
    book_id = extract_field(body, "book id")
    reviewer = extract_field(body, "reviewer")
    grade = extract_field(body, "grade")
    review = extract_field(body, "review")

    # -------------------------------
    # Detect placeholder / defaults
    # -------------------------------
    # defaults = {
    #     "book id": "enter-book-id-here",
    #     "reviewer": "enter-reviewer-name-here",
    #     "grade": "enter-grade-here",
    #     "review": "enter-review-text-here",
    # }

    # -------------------------------
    # Date validation (non-fatal)
    # -------------------------------
    books = load_books(BOOKS_FILE)

    if not books.get(book_id, False):
        WARNINGS.append(warn(f"Book id '{book_id}' not found! Exiting."))
        failed = True

    if reviewer not in books[book_id]["reviews"].keys():
        WARNINGS.append(
            warn(
                f"Reviewer '{reviewer}' was no participant ({join_and(books[book_id]['reviews'].keys())})."
            )
        )
        failed = True

    if not isinstance(grade, (int)) or 1 <= grade <= 15:
        WARNINGS.append(warn(f"Grade '{grade}' is not an integer between 1 and 15."))
        failed = True

    # -------------------------------
    # Participants parsing
    # ------------------------------

    summary = build_summary(
        book_id=book_id,
        reviewer=reviewer,
        grade=grade,
        review=review,
        warnings=WARNINGS,
        notices=NOTICES,
    )

    post_issue_comment(summary)
    print(f"::notice::{summary}")

    if failed:
        return False

    books[book_id]["ratings"][reviewer] = grade
    books[book_id]["reviews"][reviewer] = review

    save_books(BOOKS_FILE, books)

    return True


if __name__ == "__main__":
    title_added = parse_issue()
    # Exit code 1 if nothing was added (optional)
    exit(0 if title_added else 1)
