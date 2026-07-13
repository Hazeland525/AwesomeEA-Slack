"""Delete all messages in the bot↔user DM and reset greeting_state.json."""

import json
import os
import sys
import time

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

bot_client  = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
user_client = WebClient(token=os.environ["SLACK_USER_TOKEN"])

# Resolve identities
bot_user_id  = bot_client.auth_test()["user_id"]
user_id      = user_client.auth_test()["user_id"]

# Open / find the DM channel
dm_channel = bot_client.conversations_open(users=[user_id])["channel"]["id"]
print(f"DM channel: {dm_channel}  (bot={bot_user_id}, user={user_id})")

# Collect every message (paginated)
messages = []
cursor = None
while True:
    resp = bot_client.conversations_history(
        channel=dm_channel,
        limit=200,
        **({"cursor": cursor} if cursor else {}),
    )
    messages.extend(resp["messages"])
    cursor = resp.get("response_metadata", {}).get("next_cursor")
    if not cursor:
        break

print(f"Found {len(messages)} messages — deleting…")

deleted = skipped = failed = 0
for msg in messages:
    ts = msg["ts"]
    poster = msg.get("user") or msg.get("bot_id", "")
    try:
        if msg.get("user") == bot_user_id or msg.get("bot_id"):
            bot_client.chat_delete(channel=dm_channel, ts=ts)
        else:
            user_client.chat_delete(channel=dm_channel, ts=ts)
        deleted += 1
    except SlackApiError as e:
        code = e.response.get("error", "")
        if code in ("cant_delete_message", "message_not_found"):
            skipped += 1
        else:
            print(f"  ✗ ts={ts}: {code}", file=sys.stderr)
            failed += 1
    time.sleep(0.3)  # stay under Tier-2 rate limit

print(f"Done — deleted {deleted}, skipped {skipped}, failed {failed}")

# Reset greeting state for this user
state_path = os.path.join(os.path.dirname(__file__), "..", "greeting_state.json")
try:
    with open(state_path) as f:
        state = json.load(f)
    if user_id in state:
        del state[user_id]
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        print(f"Greeting state cleared for {user_id}")
except FileNotFoundError:
    pass
