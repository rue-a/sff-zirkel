# %%
import json
import re
import os
from datetime import datetime
from pathlib import Path
import uuid

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

OPEN_LIBRARY_URL = "https://openlibrary.org"
LIMIT = 10

BOOK_GENRES = [
    "Arts",
    "Architecture",
    "Art Instruction",
    "Art History",
    "Dance",
    "Design",
    "Fashion",
    "Film",
    "Graphic Design",
    "Music",
    "Music Theory",
    "Painting",
    "Photography",
    "Animals",
    "Bears",
    "Cats",
    "Kittens",
    "Dogs",
    "Puppies",
    "Fiction",
    "Fantasy",
    "Historical Fiction",
    "Horror",
    "Humor",
    "Literature",
    "Magic",
    "Mystery and detective stories",
    "Plays",
    "Poetry",
    "Romance",
    "Science Fiction",
    "Short Stories",
    "Thriller",
    "Young Adult",
    "Science & Mathematics",
    "Biology",
    "Chemistry",
    "Mathematics",
    "Physics",
    "Programming",
    "Business & Finance",
    "Management",
    "Entrepreneurship",
    "Business Economics",
    "Business Success",
    "Finance",
    "Children's",
    "Kids Books",
    "Stories in Rhyme",
    "Baby Books",
    "Bedtime Books",
    "Picture Books",
    "History",
    "Ancient Civilization",
    "Archaeology",
    "Anthropology",
    "World War II",
    "Social Life and Customs",
    "Health & Wellness",
    "Cooking",
    "Cookbooks",
    "Mental Health",
    "Exercise",
    "Nutrition",
    "Self-help",
    "Biography",
    "Autobiographies",
    "History",
    "Politics and Government",
    "World War II",
    "Women",
    "Kings and Rulers",
    "Composers",
    "Artists",
    "Social Sciences",
    "Anthropology",
    "Religion",
    "Political Science",
    "Psychology",
    "Places",
    "Brazil",
    "India",
    "Indonesia",
    "United States",
    "Textbooks",
    "History",
    "Mathematics",
    "Geography",
    "Psychology",
    "Algebra",
    "Education",
    "Business & Economics",
    "Science",
    "Chemistry",
    "English Language",
    "Physics",
    "Computer Science",
]

# -----------------------------------


def download_cover(url: str, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    with open(out_path, "wb") as f:
        f.write(resp.content)

    print(f"Saved cover to {out_path}")


def fetch_openlibrary_metadata(query: str, books: dict) -> dict:

    existing_queries = [book["query"] for book in books.values()]
    existing_work_keys = [book["meta"]["key"] for book in books.values()]

    # %%
    fields = [
        "key",
        "type",
        "title",
        "author_name",
        "first_publish_year",
        "first_edition",
        "number_of_pages_median",
        "first_sentence",
        "description",
        "subject",
        "edition_count",
        "id_wikidata",
        "place",
        "time",
        "cover_i",
    ]
    # %%
    params = {"q": query, "limit": LIMIT, "sorts": "editions", "fields": fields}

    # do not run the same query twice
    if query in existing_queries:
        WARNINGS.append(warn(f"The query `{query}` was already queried — skipping."))
        return False

    response = requests.get(
        f"{OPEN_LIBRARY_URL}/search.json",
        params=params,
        timeout=10,
    )
    NOTICES.append(notice((f"Querying: {query} (actual query URL: {response.url})")))

    # raise_for_status() throws exception if request failed
    response.raise_for_status()
    response_data = response.json()

    # check if we found a book (numFound > 0)
    if not response_data.get("numFound", False):
        WARNINGS.append(warn(f"No results found on OpenLibrary for query `{query}`."))
        return False

    if response_data["numFound"] > 1:
        WARNINGS.append(
            warn(
                f"Result is ambigous, {response_data['numFound']} matches found. Selecting match with most editions."
            )
        )

    # data is in the docs attribute (we sorted by edition count in the query -> first entry has most editions)
    response_data = response_data["docs"][0]

    for field in fields:
        if field not in response_data.keys():
            NOTICES.append(notice((f"The field `{field}` yielded no data")))

    # in open library terms, a work is the sum of all editions
    work_id = response_data["key"]

    # Check for duplicates, stop if book already exists in db
    if work_id in existing_work_keys:
        WARNINGS.append(
            warn(
                f"A work with key `{work_id}` ({next(((item['meta']['title'], item['id']) for item in books.values() if item.get('meta', {}).get('key') == work_id), None)}) already exists — skipping."
            )
        )
        return False

    cover_path = ""
    cover_url = ""
    if "cover_i" in response_data.keys():
        cover_url = (
            f"https://covers.openlibrary.org/b/id/{response_data['cover_i']}-M.jpg"
        )
        cover_path = COVERS_PATH / f"{response_data['cover_i']}.jpg"

        # store cover at covers
        download_cover(cover_url, cover_path)
    else:
        NOTICES.append(notice(("The query yielded no cover image")))

    stringified_data = {
        "key": response_data.get("key", ""),
        "type": response_data.get("type", ""),
        "title": response_data.get("title", ""),
        "authors": join_and(response_data.get("author_name", [""])),
        "first_publish_year": response_data.get("first_publish_year", ""),
        "first_edition": response_data.get("first_edition", ""),
        "number_of_pages_median": response_data.get("number_of_pages_median", ""),
        "first_sentence": response_data.get("first_sentence", [""])[0],
        "description": response_data.get("description", ""),
        "subjects": ", ".join(
            [
                genre
                for genre in response_data.get("subject", [""])
                if genre in BOOK_GENRES
            ]
        ),
        "edition_count": response_data.get("edition_count", ""),
        "id_wikidata": list(set(response_data.get("id_wikidata", []))),
        "place": response_data.get("place", ""),
        "time": response_data.get("time", ""),
        "cover_path": cover_path.as_posix() if cover_path else None,
        "cover_url": cover_url,
    }

    return stringified_data


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

        # reuse Open Library work key as ID
        books[meta["key"].split("/")[1]] = new_book
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
