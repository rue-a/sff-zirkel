from issue_ingestion import (
    BOOKS_FILE,
    CLUB_FILE,
    extract_issue_fields,
    load_books,
    load_club,
    load_issue,
    post_summary,
    save_books,
    validate_reviewer,
    warn,
)

class ParsingError(ValueError):
    """Raised when a rating cannot be parsed."""


def parse_german_grade(rating: str) -> int:
    if not (rating.isdigit() and 1 <= int(rating) <= 15):
        raise ParsingError(
            f"Rating '{rating}' is not an integer between 1 and 15."
        )
    return int(rating)


def parse_five_star(rating: str) -> float:
    try:
        value = float(rating)
    except ValueError as exc:
        raise ParsingError(f"Rating '{rating}' is not a valid number.") from exc

    if not (0.5 <= value <= 5.0 and (value * 2) % 1 == 0):
        raise ParsingError(
            f"Rating '{rating}' must be a multiple of 0.5 between 0.5 and 5."
        )

    return value


RATING_PARSERS = {
    "german_grades": parse_german_grade,
    "five_stars": parse_five_star,
}


def parse_rating(rating: str, club: dict) -> int | float:
    system_type = club.get("rating_system_id", "german_grades")

    try:
        parser = RATING_PARSERS[system_type]
    except KeyError as exc:
        raise ParsingError(f"Unknown rating system '{system_type}'.") from exc

    return parser(rating)


def build_rating_summary(
    *,
    book_id: str,
    reviewer: str,
    rating: str,
    warnings: list[str],
    notices: list[str],
    success: bool,
) -> str:
    lines = ["# SUMMARY"]
    lines.append("✅ **Rating saved**" if success else "❌ **Rating not saved**")
    lines.append(f"book id: {book_id}")
    lines.append(f"reviewer: {reviewer}")
    lines.append(f"rating: {rating}")

    if warnings:
        lines.append("### Warnings")
        lines.append("\n> [!WARNING]\n>")

        for warning in warnings:
            lines.append(f"> - {warning}")

    if notices:
        lines.append("### Notes")
        lines.append("\n> [!NOTE]\n>")

        for notice in notices:
            lines.append(f"> - {notice}")

    return "\n".join(lines)


def parse_issue():
    """
    Parse GitHub issue payload and add a rating.
    Extracts book_id, reviewer, and rating from issue.
    """
    warnings = []
    notices = []
    success = True

    event = load_issue()
    body = event.get("issue", {}).get("body", "")

    fields = extract_issue_fields(body, "book id", "reviewer", "rating")
    book_id = fields["book id"]
    reviewer = fields["reviewer"]
    rating = fields["rating"]

    books = load_books(BOOKS_FILE)
    club = load_club(CLUB_FILE)

    book = books.get(book_id)
    if not book:
        warnings.append(warn(f"Book id '{book_id}' not found! Aborted."))
        success = False

    if book:
        if not validate_reviewer(
                book=book,
                reviewer=reviewer,
                participant_field="ratings",
            ):
                warnings.append(warn(f"Reviewer '{reviewer}' was no participant. Aborted."))
                success = False

    try:
        parsed_rating = parse_rating(rating, club)
    except ParsingError as e:
        warnings.append(warn(str(e)))
        success = False
        parsed_rating = None # This should not be necessary, but ensures a set variable.


    summary = build_rating_summary(
        book_id=book_id,
        reviewer=reviewer,
        rating=rating,
        warnings=warnings,
        notices=notices,
        success=success,
    )

    post_summary(summary)

    if not success:
        return False

    book["ratings"][reviewer] = parsed_rating

    save_books(BOOKS_FILE, books)

    return True


if __name__ == "__main__":
    title_added = parse_issue()
    # Exit code 1 if nothing was added (optional)
    exit(0 if title_added else 1)
