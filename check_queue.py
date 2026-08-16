"""
Checks queue.json's health before posting: empty, running low, malformed, or fine.
Mirrors check_expiry.py's pattern — used by the GitHub Actions workflow
to decide whether to post and whether to open a warning issue.

Rule: the queue should always have at least 2 posts as a buffer. If it
drops to 1 or 0, the workflow still posts what's available (unless truly
empty) but opens a GitHub Issue warning the user to add more content.

If queue.json isn't valid JSON, or doesn't match the expected shape (a
list of {"text": ..., "hook": ...} objects, or plain strings), status is
"error" and a human-readable "message" describing exactly what's wrong
is printed/written, so the workflow can open an issue that tells the
user precisely how to fix it instead of just failing silently.
"""

import json
import os
import sys

LOW_THRESHOLD = 2  # warn once queue count is below this


def validate_queue(queue):
    """Returns None if the parsed queue is well-formed, otherwise a
    human-readable string describing the first problem found."""
    if not isinstance(queue, list):
        return (
            f"queue.json must be a JSON array (a list in [ ... ]), "
            f"but found a {type(queue).__name__} instead."
        )

    for i, item in enumerate(queue):
        label = f"Item #{i + 1} in queue.json"

        if isinstance(item, str):
            if not item.strip():
                return f"{label} is an empty string. Remove it or add real post text."
            continue

        if not isinstance(item, dict):
            return (
                f'{label} must be an object like {{"text": "...", "hook": "..."}} '
                f"or a plain string, but found a {type(item).__name__} instead."
            )

        if "text" not in item:
            return f'{label} is missing the required "text" field.'
        if not isinstance(item["text"], str) or not item["text"].strip():
            return f'{label} has an empty or non-text "text" field.'

        if "hook" in item and item["hook"] is not None and not isinstance(item["hook"], str):
            return f'{label} has a "hook" field that isn\'t text.'

    return None


def main():
    try:
        with open("queue.json") as f:
            raw = f.read()
    except FileNotFoundError:
        print("status=empty")
        print("count=0")
        write_output("empty", 0)
        sys.exit(0)

    try:
        queue = json.loads(raw)
    except json.JSONDecodeError as e:
        message = f"queue.json isn't valid JSON: {e.msg} at line {e.lineno}, column {e.colno}."
        print("status=error")
        print("count=0")
        print(f"message={message}")
        write_output("error", 0, message)
        sys.exit(0)

    error = validate_queue(queue)
    if error:
        print("status=error")
        print("count=0")
        print(f"message={error}")
        write_output("error", 0, error)
        sys.exit(0)

    count = len(queue)

    if count == 0:
        status = "empty"
    elif count < LOW_THRESHOLD:
        status = "low"
    else:
        status = "ok"

    print(f"status={status}")
    print(f"count={count}")
    write_output(status, count)


def write_output(status, count, message=None):
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"status={status}\n")
            f.write(f"count={count}\n")
            if message:
                f.write(f"message<<QUEUE_MESSAGE_EOF\n{message}\nQUEUE_MESSAGE_EOF\n")


if __name__ == "__main__":
    main()
