#!/usr/bin/env python3
"""Set job titles on Slack user profiles via users.profile.set (SLACK_USER_TOKEN)."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

TITLES = {
    "U0BC33DJ4UD": ("Jane Miller",      "Product Lead"),
    "U0BC6F831FC": ("Tim Smith",        "Frontend Engineer"),
    "U0BCA4D6VU4": ("Sue Chen",         "User Researcher"),
    "U0BC4CWJ4GN": ("Steven Johnson",   "Engineering Manager"),
    "U0BC6F9BLCS": ("Philip Lim",       "Product Designer"),
    "U0BC04NFXV1": ("Elizabeth Barry",  "Product Designer"),
    "U0BC04MJ71R": ("Rosario Bennett",  "QA Engineer"),
}

client = WebClient(token=os.environ["SLACK_USER_TOKEN"])

ok = failed = 0
for user_id, (name, title) in TITLES.items():
    try:
        client.users_profile_set(user=user_id, profile={"title": title})
        print(f"  ✓ {name} ({user_id}) → \"{title}\"")
        ok += 1
    except SlackApiError as e:
        print(f"  ✗ {name} ({user_id}): {e.response['error']}", file=sys.stderr)
        failed += 1

print(f"\nDone — {ok} set, {failed} failed.")
if failed:
    sys.exit(1)
