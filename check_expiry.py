"""
Checks how many days remain before the LinkedIn access token expires.
Used by the GitHub Actions workflow to decide whether to post normally,
post with a warning, or skip posting and flag for reauthorization.

Prints one of: ok / warning / expired, followed by the number of days left.
Also writes these to GITHUB_OUTPUT if running inside GitHub Actions.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

WARNING_THRESHOLD_DAYS = 7


def main():
    try:
        with open("tokens.json") as f:
            tokens = json.load(f)
    except FileNotFoundError:
        print("status=expired")
        print("days_left=0")
        write_output("expired", 0)
        sys.exit(0)

    authorized_at_str = tokens.get("authorized_at")
    expires_in = tokens.get("expires_in", 0)

    if not authorized_at_str:
        # Older tokens.json from before this field existed — can't compute
        # a real expiry, so play it safe and treat as needing reauth soon.
        print("status=unknown")
        print("days_left=unknown")
        write_output("unknown", "unknown")
        sys.exit(0)

    authorized_at = datetime.fromisoformat(authorized_at_str)
    expires_at = authorized_at + timedelta(seconds=expires_in)
    days_left = (expires_at - datetime.now(timezone.utc)).days

    if days_left <= 0:
        status = "expired"
    elif days_left <= WARNING_THRESHOLD_DAYS:
        status = "warning"
    else:
        status = "ok"

    print(f"status={status}")
    print(f"days_left={days_left}")
    write_output(status, days_left)


def write_output(status, days_left):
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"status={status}\n")
            f.write(f"days_left={days_left}\n")


if __name__ == "__main__":
    main()
