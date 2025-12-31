# %%
import json
import re
import os
from datetime import datetime
from pathlib import Path

import requests


# ---------- Configuration ----------
BOOKS_FILE = Path("data/books.json")
COVERS_PATH = Path("covers")
WARNINGS = []
# -----------------------------------


def warn(msg):
    print(f"::warning::{msg}")
    WARNINGS.append(msg)


def extract_field(body: str, field: str) -> str:
    """
    Extracts values like:
    - ISBN: `9781234567890`
    - review date: `2025-03-14`
    - proposer: `arne`
    """
    pattern = rf"- {re.escape(field)}:\s*`([^`]*)`"
    match = re.search(pattern, body, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def download_cover(url: str, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    with open(out_path, "wb") as f:
        f.write(resp.content)

    print(f"Saved cover to {out_path}")


def fetch_openlibrary_metadata(query: str, books: list) -> dict:
    open_library_url = "https://openlibrary.org"
    existing_queries = [book["query"] for book in books]
    existing_work_keys = [book["meta"]["key"] for book in books]

    # do not run the same query twice
    if query in existing_queries:
        warn(f"The query '{query}' was already queried — skipping.")
        return False

    book_search_response = requests.get(
        f"{open_library_url}/search.json", params={"q": query}, timeout=10
    )

    # raise_for_status() throws exception if request failed
    book_search_response.raise_for_status()
    book_search_data = book_search_response.json()

    # check if we found a book (numFound > 0)
    if not book_search_data.get("numFound", False):
        warn(f"No results found on OpenLibrary for query '{query}'.")
        return False

    # data is in the docs attribute
    book_search_data = book_search_data["docs"][0]

    # in open library terms, a work is the sum of all editions
    work_id = book_search_data["key"]

    # Check for duplicates, stop if book already exists in db
    if work_id in existing_work_keys:
        warn(f"Book with key {work_id} already exists — skipping.")
        return False

    work_response = requests.get(f"{open_library_url}/{work_id}.json", timeout=10)
    work_response.raise_for_status()
    work_data = work_response.json()

    # the cover edition is the edition (book) used to represent the work
    cover_edition_key = book_search_data["cover_edition_key"]
    cover_edition_response = requests.get(
        f"{open_library_url}/books/{cover_edition_key}.json",
        timeout=10,
    )
    cover_edition_response.raise_for_status()
    cover_edition_data = cover_edition_response.json()
    cover_url = f"https://covers.openlibrary.org/b/olid/{cover_edition_key}.jpg"
    cover_path = COVERS_PATH / f"{cover_edition_key}.jpg"

    # store cover at covers
    download_cover(cover_url, cover_path)

    data = {
        "title": book_search_data.get("title", ""),
        "key": book_search_data.get("key", ""),
        "authors": ", ".join(book_search_data.get("author_name", [""])),
        "first_publish_year": book_search_data.get("first_publish_year", ""),
        "edition_count": book_search_data.get("edition_count", ""),
        "subjects": ", ".join(work_data.get("subjects", [""])),
        "pages": cover_edition_data.get("pagination", ""),
        "weight": cover_edition_data.get("weight", ""),
        "description": work_data.get("description", {"value": ""})["value"],
        "first_sentence": work_data.get("first_sentence", {"value": ""})["value"],
        "cover_path": cover_path.as_posix(),
    }

    return data


def load_books() -> list:
    if not BOOKS_FILE.exists():
        return []

    with BOOKS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_books(books: list) -> None:
    BOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with BOOKS_FILE.open("w", encoding="utf-8") as f:
        json.dump(books, f, indent=2)


def add_book(isbn, proposer, participants, review_date):
    books = load_books()

    # Fetch metadata to validate ISBN exists
    meta = fetch_openlibrary_metadata(isbn, books)

    if meta:
        ratings = {name: None for name in participants}

        new_book = {
            "query": isbn,
            "review_date": review_date,
            "proposer": proposer,
            "participants": participants,
            "ratings": ratings,
            "meta": meta,
        }

        books.append(new_book)
        save_books(books)
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
) -> str:
    """
    Build a human-readable Markdown summary of what happened,
    including warnings (if any).
    """

    lines = ["# SUMMARY"]

    if not meta:
        lines.append("❌ **No book entry created**\n")
    else:
        # Header
        lines.append("✅ **Book entry created**\n")

        # Core info
        lines.append(f"**Query:** {query}")

        title = meta.get("title", "")
        authors = meta.get("authors", "")
        if title:
            lines.append(f"**Title:** *{title}*")
        if authors:
            lines.append(f"**Authors:** {authors}")

        if review_date:
            lines.append(f"**Review date:** {review_date}")

        if proposer:
            lines.append(f"**Proposed by:** {proposer}")

        if participants:
            lines.append(f"**Participants:** {', '.join(participants)}")

    # Warnings section
    if warnings:
        lines.append("\n⚠️ **Warnings**")
        for w in warnings:
            lines.append(f"- {w}")

    return "\n".join(lines)


def post_issue_comment(body: str):
    """
    Post a comment to the current GitHub issue.
    """
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    issue_number = os.environ.get("GITHUB_ISSUE_NUMBER")

    if not all([token, repo, issue_number]):
        print("Missing GitHub context — not posting comment.")
        return

    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    resp = requests.post(
        url,
        headers=headers,
        json={"body": body},
        timeout=10,
    )

    resp.raise_for_status()
    print("✔ Posted summary comment")


def parse_issue():
    """
    Parse GitHub issue payload and add a book entry.
    Extracts ISBN from issue title and metadata from body.
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

    # if isbn is not valid, try with entered title
    if len(isbn) not in (10, 13):
        fallback = title.strip()
        warn(f"No valid ISBN detected, trying issue title: `{fallback}`")
        isbn = fallback

    # -------------------------------
    # Metadata from body
    # -------------------------------
    review_date = extract_field(body, "review date")
    proposer = extract_field(body, "proposer")
    participants_raw = extract_field(body, "participants")

    # -------------------------------
    # Detect placeholder / defaults
    # -------------------------------
    defaults = {
        "review date": "YYYY-MM-DD",
        "proposer": "namehere",
        "participants": "namehere, namehere2, namehere3",
    }

    if review_date == defaults["review date"]:
        warn("Review date is still placeholder (YYYY-MM-DD).")

    if proposer == defaults["proposer"]:
        warn("Proposer is still placeholder (namehere).")

    if participants_raw == defaults["participants"]:
        warn("Participants are still placeholder (p1, p2, p3).")

    # -------------------------------
    # Date validation (non-fatal)
    # -------------------------------
    if review_date:
        try:
            datetime.strptime(review_date, "%Y-%m-%d")
        except ValueError:
            warn(f"Review date '{review_date}' is not in YYYY-MM-DD format.")

    # -------------------------------
    # Participants parsing
    # -------------------------------
    participants = [p.strip() for p in participants_raw.split(",") if p.strip()]

    if not participants:
        warn("No participants specified.")

    # -------------------------------
    # Add book
    # -------------------------------
    book_meta = add_book(
        isbn=isbn,
        proposer=proposer,
        participants=participants,
        review_date=review_date,
    )

    summary = build_summary(
        query=isbn,
        review_date=review_date,
        proposer=proposer,
        participants=participants,
        meta=book_meta,
        warnings=WARNINGS,
    )

    post_issue_comment(summary)
    print(f"::notice::{summary}")


if __name__ == "__main__":
    parse_issue()
