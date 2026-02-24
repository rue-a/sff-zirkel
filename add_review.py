# %%
import json
import os
from pathlib import Path


from utilities import (
    notice,
    warn,
    join_and,
    extract_field,
    load_books,
    save_books,
    post_issue_comment,
)

# ---------- Configuration ----------
BOOKS_FILE = Path("data/books.json")
CLUB_FILE = Path("data/club.json")
COVERS_PATH = Path("covers")
NOTICES = []
WARNINGS = []


def build_summary(
    *,
    book_id: str,
    reviewer: str,
    grade: str,
    review: list[str],
    meta: dict | None,
    warnings: list[str],
    notices: list[str],
) -> str:
    """
    Build a human-readable Markdown summary of what happened,
    including warnings (if any).
    """

    lines = ["# SUMMARY"]
    lines.append(f"book id: {book_id}")
    lines.append(f"reviewer: {reviewer}")
    lines.append(f"grade: {grade}")
    lines.append(f"review: {review}")

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

    if not (isinstance(int(grade), (int)) and 1 <= int(grade) <= 15):
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
