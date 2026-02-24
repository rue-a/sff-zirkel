import os
import re
import json
import requests


def notice(msg):
    print(f"::notice::{msg}")
    return msg


def warn(msg):
    print(f"::warning::{msg}")
    return msg


def join_and(xs, oxford=True):
    if len(xs) <= 2:
        return " and ".join(xs)
    sep = ", and " if oxford else " and "
    return ", ".join(xs[:-1]) + sep + xs[-1]


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


def load_books(books_file) -> list:
    if not books_file.exists():
        return []

    with books_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_club(club_file) -> dict:
    if not club_file.exists():
        return {}

    with club_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_books(books_file, books: list) -> None:
    books_file.parent.mkdir(parents=True, exist_ok=True)
    with books_file.open("w", encoding="utf-8") as f:
        json.dump(books, f, indent=2)


def post_issue_comment(body: str):
    """
    Post a comment to the current GitHub issue.
    """
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not all([token, repo, event_path]):
        print("Missing GitHub context — not posting comment.")
        return

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    issue_number = event.get("issue", {}).get("number")
    if not issue_number:
        print("Could not determine issue number from event — skipping comment.")
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
