#!/usr/bin/env python3
"""
One-command setup wizard for LinkedIn Auto-Poster.

Run this AFTER:
  1. Using this template to create your own GitHub repo
  2. Cloning it locally

This script will, in order:
  1. Install Python dependencies
  2. Auto-publish a privacy policy page via GitHub Pages (needed for the
     LinkedIn app form) and copy its URL to your clipboard
  3. Pause while you go create your LinkedIn Developer app using that URL
     (and default-logo.png in this folder, if you don't have your own logo)
  4. Walk you through LinkedIn's login/consent screen once
  5. Save your access token locally as tokens.json (never committed)
  6. If the GitHub CLI (gh) is installed and logged in, automatically push
     that token to your repo's Actions secrets — no manual copy-pasting
"""

import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import date

# requests isn't imported at module level: check_python_deps() (called first
# in main()) is what installs it, so importing it here would crash on a
# machine that doesn't have it yet, before we get the chance to install it.


def run(cmd, **kwargs):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, **kwargs)


def check_python_deps():
    print("Checking Python dependencies...")
    try:
        import requests  # noqa
        import PIL  # noqa
        print("  requests and pillow already installed.")
    except ImportError:
        print("  Installing requests and pillow...")
        result = run([sys.executable, "-m", "pip", "install", "requests", "pillow", "--break-system-packages"])
        if result.returncode != 0:
            run([sys.executable, "-m", "pip", "install", "requests", "pillow"])


def check_gh_cli():
    if shutil.which("gh") is None:
        return False
    result = run(["gh", "auth", "status"], capture_output=True, text=True)
    return result.returncode == 0


def copy_to_clipboard(text):
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif system == "Windows":
            subprocess.run(["clip"], input=text.encode(), check=True, shell=True)
        else:
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
            except FileNotFoundError:
                subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode(), check=True)
        return True
    except Exception:
        return False


def get_repo_info():
    result = run(["gh", "repo", "view", "--json", "owner,name"], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    return data["owner"]["login"], data["name"]


POST_TIME_CRON = "30 3"  # 9:00 AM IST — the hour/minute used by every preset below

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_CRON_NUM = {"Mon": "1", "Tue": "2", "Wed": "3", "Thu": "4", "Fri": "5", "Sat": "6", "Sun": "0"}


def _prompt_days(count, default_days):
    """Asks for `count` comma-separated day names; falls back to
    default_days on empty or unparseable input."""
    default_str = ",".join(default_days)
    print(f"  Days: {', '.join(DAY_NAMES)}")
    raw = input(f"  Enter {count} day(s), comma-separated [default: {default_str}]: ").strip()
    if not raw:
        return default_days
    chosen = [d.strip().capitalize()[:3] for d in raw.split(",")]
    if len(chosen) != count or any(d not in DAY_CRON_NUM for d in chosen):
        print(f"  Couldn't parse that as {count} valid day(s) — using default: {default_str}")
        return default_days
    return chosen


def _prompt_days_of_month(default_days):
    """Asks for day-of-month numbers (1-28, to stay valid in every month);
    falls back to default_days on empty or unparseable input."""
    default_str = ",".join(str(d) for d in default_days)
    raw = input(
        f"  Enter {len(default_days)} day(s) of the month (1-28), comma-separated "
        f"[default: {default_str}]: "
    ).strip()
    if not raw:
        return default_days
    try:
        chosen = [int(d.strip()) for d in raw.split(",")]
    except ValueError:
        chosen = []
    if len(chosen) != len(default_days) or any(d < 1 or d > 28 for d in chosen):
        print(f"  Couldn't parse that as {len(default_days)} valid day(s)-of-month (1-28) — using default: {default_str}")
        return default_days
    return chosen


def _cron_for_days(days):
    return ",".join(DAY_CRON_NUM[d] for d in days)


def setup_branding():
    print("\n--- Graphic Branding ---")
    display_name = input("Name to show on generated graphics [default: Your Name]: ").strip() or "Your Name"
    tagline = input("Tagline to show under it [default: Your tagline here]: ").strip() or "Your tagline here"
    return display_name, tagline


def setup_config():
    display_name, tagline = setup_branding()

    print("\n--- Posting Preferences ---")

    print("\nHow often should posts go out? (all times 9:00 AM IST)")
    print("  1. Once a week")
    print("  2. Twice a week")
    print("  3. Three times a week")
    print("  4. Daily")
    print("  5. Twice a month")
    print("  6. Custom (enter your own cron expression)")
    choice = input("Choose 1-6 [default: 2]: ").strip() or "2"

    if choice == "1":
        days = _prompt_days(1, ["Mon"])
        schedule_cron = f"{POST_TIME_CRON} * * {_cron_for_days(days)}"
        schedule_label = f"Weekly ({days[0]}, 9:00 AM IST)"
    elif choice == "3":
        days = _prompt_days(3, ["Mon", "Wed", "Fri"])
        schedule_cron = f"{POST_TIME_CRON} * * {_cron_for_days(days)}"
        schedule_label = f"Three times a week ({', '.join(days)}, 9:00 AM IST)"
    elif choice == "4":
        schedule_cron = f"{POST_TIME_CRON} * * *"
        schedule_label = "Daily (9:00 AM IST)"
    elif choice == "5":
        print("\nTwice-a-month posts go out on two fixed days of the month.")
        doms = _prompt_days_of_month([1, 15])
        schedule_cron = f"{POST_TIME_CRON} {','.join(str(d) for d in doms)} * *"
        schedule_label = f"Twice a month ({' & '.join(str(d) for d in doms)}, 9:00 AM IST)"
    elif choice == "6":
        schedule_cron = input("Enter cron expression (e.g. '30 3 * * 1,4'), see crontab.guru: ").strip()
        schedule_label = f"Custom: {schedule_cron}"
    else:
        if choice != "2":
            print("Unrecognized choice, defaulting to twice a week.")
        days = _prompt_days(2, ["Mon", "Thu"])
        schedule_cron = f"{POST_TIME_CRON} * * {_cron_for_days(days)}"
        schedule_label = f"Twice a week ({' & '.join(days)}, 9:00 AM IST)"

    print("\nShould posts include an auto-generated graphic image, or text only?")
    print("  1. Text + graphic image (recommended — more engagement on LinkedIn)")
    print("  2. Text only")
    img_choice = input("Choose 1-2 [default: 1]: ").strip() or "1"
    use_images = img_choice != "2"

    config = {
        "display_name": display_name,
        "tagline": tagline,
        "use_images": use_images,
        "schedule_label": schedule_label,
        "schedule_cron": schedule_cron,
    }
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

    # Update the workflow file's cron line to match
    workflow_path = ".github/workflows/scheduled-post.yml"
    if os.path.exists(workflow_path):
        with open(workflow_path) as f:
            content = f.read()
        import re
        new_content = re.sub(
            r'- cron: "[^"]*"',
            f'- cron: "{schedule_cron}"',
            content,
            count=1,
        )
        with open(workflow_path, "w") as f:
            f.write(new_content)
        print(f"\nGraphic branding: {display_name} — {tagline}")
        print(f"Schedule set to: {schedule_label}")
        print(f"Images: {'on' if use_images else 'off'}")

    run(["git", "add", "config.json", workflow_path])
    run(["git", "commit", "-m", "configure posting frequency and image preference"])
    run(["git", "push"])

    return config


def _wait_for_privacy_policy_live(url, timeout_seconds=150, interval_seconds=10):
    """Polls the privacy policy URL until it returns 200, or times out.
    GitHub Pages can take a minute or two after first enabling before the
    URL actually resolves — without this check, the wizard would send the
    user straight to LinkedIn's app form with a URL that still 404s."""
    import requests

    print("Checking that the privacy policy page is actually live (LinkedIn will")
    print("reject the app form if the URL doesn't resolve)...")
    waited = 0
    while waited < timeout_seconds:
        try:
            if requests.get(url, timeout=5).status_code == 200:
                print("Confirmed live — safe to paste into the LinkedIn app form now.")
                return True
        except requests.RequestException:
            pass
        time.sleep(interval_seconds)
        waited += interval_seconds
        print(f"  ...still waiting on GitHub Pages ({waited}s elapsed)")
    print("Still not reachable after 2.5 minutes. Do NOT paste this URL into the")
    print("LinkedIn app form yet — open it in your browser first. If it's still a")
    print("404, check Settings > Pages on this repo's GitHub page for build errors.")
    return False


def setup_privacy_policy(has_gh):
    policy_path = "docs/privacy-policy.html"

    if os.path.exists(policy_path):
        print("\nPrivacy policy page already exists locally, skipping generation.")
        if has_gh:
            info = get_repo_info()
            if info:
                owner, name = info
                url = f"https://{owner}.github.io/{name}/privacy-policy.html"
                copied = copy_to_clipboard(url)
                print(f"Your privacy policy URL: {url}")
                print("(copied to clipboard)" if copied else "(couldn't auto-copy — copy it manually above)")
                _wait_for_privacy_policy_live(url)
                return url
        return None

    if not has_gh:
        print("\nSkipping automatic privacy policy publishing (GitHub CLI not available).")
        print("You can still use docs/privacy-policy-template.html manually — fill in your")
        print("email, host it anywhere (e.g. GitHub Pages), and use that URL for your LinkedIn app.")
        return None

    print("\n--- Privacy Policy Setup ---")
    print("LinkedIn requires a Privacy Policy URL for your app. This will generate one")
    print("automatically and publish it via GitHub Pages.\n")
    email = input("Enter a contact email to show on the privacy policy page: ").strip()
    if not email:
        print("No email entered, skipping automatic privacy policy setup.")
        return None

    with open("docs/privacy-policy-template.html") as f:
        template = f.read()
    content = template.replace("{{EMAIL}}", email).replace("{{DATE}}", date.today().isoformat())

    os.makedirs("docs", exist_ok=True)
    with open(policy_path, "w") as f:
        f.write(content)

    run(["git", "add", policy_path])
    run(["git", "commit", "-m", "add auto-generated privacy policy page"])
    push_result = run(["git", "push"])
    if push_result.returncode != 0:
        print("\nCouldn't push the privacy policy page automatically.")
        print("Run 'git push' manually, then re-run this script to continue.")
        return None

    info = get_repo_info()
    if not info:
        print("\nCouldn't detect repo info via GitHub CLI. Enable GitHub Pages manually")
        print("in Settings > Pages, source: main branch, /docs folder.")
        return None
    owner, name = info

    print("Enabling GitHub Pages...")
    pages_body = json.dumps({"build_type": "legacy", "source": {"branch": "main", "path": "/docs"}})
    pages_result = run(
        ["gh", "api", f"repos/{owner}/{name}/pages", "-X", "POST", "--input", "-"],
        input=pages_body, capture_output=True, text=True,
    )
    pages_enabled = pages_result.returncode == 0 or "already enabled" in pages_result.stderr
    if not pages_enabled:
        print("\nCouldn't enable GitHub Pages automatically:")
        print(f"  {pages_result.stderr.strip()}")
        if "current plan does not support" in pages_result.stderr:
            print("  Your GitHub plan doesn't support Pages on a private repo (Free tier")
            print("  requires the repo to be public, or upgrade to GitHub Pro/Team).")
        print("  Enable it manually: repo Settings > Pages > Source: 'main' branch, '/docs' folder.")

    url = f"https://{owner}.github.io/{name}/privacy-policy.html"
    copied = copy_to_clipboard(url)
    print(f"\nYour privacy policy URL: {url}")
    print("(copied to your clipboard — paste it into the LinkedIn app form)" if copied
          else "(couldn't auto-copy — copy the URL above manually)")

    if pages_enabled:
        _wait_for_privacy_policy_live(url)
    else:
        print("Do NOT proceed to create your LinkedIn app yet — enable Pages manually")
        print(f"(see above), confirm {url} loads in your browser, then continue.")
    return url


def main():
    print("=== LinkedIn Auto-Poster Setup ===\n")

    check_python_deps()
    has_gh = check_gh_cli()

    is_first_time_setup = not os.path.exists("config.json")

    policy_url = setup_privacy_policy(has_gh)

    if is_first_time_setup and has_gh:
        setup_config()
    elif is_first_time_setup:
        print("\nSkipping branding/frequency/image preference setup (requires GitHub CLI to")
        print("auto-update the workflow file). You can manually create config.json with")
        print('"display_name", "tagline", "use_images", and "schedule_cron" keys, and update')
        print("the cron line in .github/workflows/scheduled-post.yml, any time.")

    print("\n--- LinkedIn Developer App ---")
    print("Now go to https://www.linkedin.com/developers/apps and create an app:")
    print("  - LinkedIn Page: select 'Default Company Page for Individual Developer'")
    print("    if you don't have a company (or use your real company Page if you do)")
    print("  - Logo: upload default-logo.png from this folder if you don't have one")
    if policy_url:
        print(f"  - Privacy Policy URL: {policy_url}")
    else:
        print("  - Privacy Policy URL: use the URL printed above (or see README.md 'Step 3'")
        print("    for the manual fallback if automatic publishing wasn't available)")
    print("  - Add BOTH products: 'Share on LinkedIn' and")
    print("    'Sign In with LinkedIn using OpenID Connect'")
    print("  - Go to the app's Auth tab: your Client ID and Client Secret are shown there")
    print("  - On that same Auth tab, under 'OAuth 2.0 settings', add")
    print("    http://localhost:8080/callback as an Authorized redirect URL")
    input("\nPress Enter once your app is created and you have its Client ID/Secret ready...")

    client_id = input("\nPaste your LinkedIn Client ID: ").strip()
    client_secret = getpass.getpass("Paste your LinkedIn Client Secret (hidden): ").strip()

    if not client_id or not client_secret:
        print("\nBoth values are required. Re-run this script when you have them.")
        return

    env = os.environ.copy()
    env["LINKEDIN_CLIENT_ID"] = client_id
    env["LINKEDIN_CLIENT_SECRET"] = client_secret

    print("\nOpening your browser for LinkedIn authorization...")
    result = subprocess.run([sys.executable, "authorize.py"], env=env)

    if result.returncode != 0 or not os.path.exists("tokens.json"):
        print("\nSomething went wrong and tokens.json was not created.")
        print("Check the errors above, or try running 'python3 authorize.py' manually")
        print("after exporting LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET yourself.")
        return

    print("\ntokens.json created successfully.")

    if has_gh:
        print("\nGitHub CLI detected and authenticated.")
        print("Pushing your token to this repo's Actions secrets...")
        with open("tokens.json", "rb") as f:
            secret_result = run(["gh", "secret", "set", "TOKENS_JSON"], stdin=f)
        if secret_result.returncode == 0:
            print("\n✅ Setup complete!")
            print("\nNext steps:")
            print("  1. Edit queue.json with your own posts (see queue.example.json for the format)")
            print("  2. git add queue.json && git commit -m 'add my posts' && git push")
            print("  3. Your posts will publish automatically on the schedule set in")
            print("     .github/workflows/scheduled-post.yml (edit the cron line to change timing)")
        else:
            print("\nCouldn't push the secret automatically.")
            print("Follow the manual steps in README.md 'Step 4' to add TOKENS_JSON yourself.")
    else:
        print("\nGitHub CLI (gh) not found or not logged in.")
        print("Install it from https://cli.github.com, run 'gh auth login', then re-run this script.")
        print("OR follow the manual steps in README.md 'Step 4' to add the TOKENS_JSON secret yourself.")


if __name__ == "__main__":
    main()
