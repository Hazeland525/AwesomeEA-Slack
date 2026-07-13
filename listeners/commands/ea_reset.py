import logging
import os
import time

from slack_bolt import Ack
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from listeners.events.message import GREETING_STATE_PATH, build_greeting_payload
from listeners.views.app_home_builder import build_app_home_view

PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "preferences.json")

logger = logging.getLogger(__name__)


def _safe_delete(client: WebClient, channel: str, ts: str) -> bool:
    """Delete one message; on ratelimited, sleep Retry-After and try once more."""
    for attempt in range(2):
        try:
            client.chat_delete(channel=channel, ts=ts)
            return True
        except SlackApiError as e:
            err = e.response.get("error", "")
            if err == "ratelimited" and attempt == 0:
                wait = int(e.response.headers.get("Retry-After", 1))
                logger.warning("ea-reset: rate limited, sleeping %ds", wait)
                time.sleep(wait)
                continue
            if err in ("cant_delete_message", "message_not_found", "channel_not_found"):
                return False
            logger.warning("ea-reset: chat.delete failed: %s ts=%s", err, ts)
            return False
    return False


def handle_ea_reset(ack: Ack, command: dict, client: WebClient, respond):
    if os.environ.get("DEV_TOOLS", "").lower() != "true":
        ack(text="Reset is disabled.")
        return

    ack(text="Resetting…")

    user_id = command["user_id"]
    clear_all = command.get("text", "").strip().lower() == "all"

    # DM channel
    try:
        dm_channel = client.conversations_open(users=[user_id])["channel"]["id"]
    except Exception:
        logger.exception("ea-reset: failed to open DM")
        respond(text=":warning: Could not open DM channel.")
        return

    # Bot identity (to distinguish bot messages from user messages)
    try:
        bot_user_id = client.auth_test()["user_id"]
    except Exception:
        logger.exception("ea-reset: failed to resolve bot identity")
        respond(text=":warning: Could not resolve bot identity.")
        return

    user_client = WebClient(token=os.environ.get("SLACK_USER_TOKEN", ""))

    # Collect full message history (paginated)
    messages = []
    cursor = None
    while True:
        try:
            resp = client.conversations_history(
                channel=dm_channel,
                limit=200,
                **({"cursor": cursor} if cursor else {}),
            )
            messages.extend(resp["messages"])
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        except SlackApiError as e:
            logger.exception("ea-reset: conversations.history failed: %s", e.response.get("error"))
            break

    # Delete: bot messages with bot token, user messages with user token
    deleted = 0
    for msg in messages:
        ts = msg["ts"]
        if msg.get("user") == bot_user_id or msg.get("bot_id"):
            if _safe_delete(client, dm_channel, ts):
                deleted += 1
        elif msg.get("user") == user_id:
            if _safe_delete(user_client, dm_channel, ts):
                deleted += 1

    # Reset greeting throttle
    try:
        if os.path.exists(GREETING_STATE_PATH):
            os.remove(GREETING_STATE_PATH)
    except Exception:
        logger.exception("ea-reset: failed to remove greeting_state.json")

    # /ea-reset all: also wipe preferences + republish empty Home tab
    if clear_all:
        try:
            if os.path.exists(PREFS_PATH):
                os.remove(PREFS_PATH)
        except Exception:
            logger.exception("ea-reset: failed to remove preferences.json")
        try:
            client.views_publish(user_id=user_id, view=build_app_home_view())
        except Exception:
            logger.exception("ea-reset: failed to republish Home tab")

    # Send a fresh greeting
    first_name = "there"
    try:
        info = client.users_info(user=user_id)
        profile = info.get("user", {}).get("profile", {})
        first_name = profile.get("first_name") or profile.get("display_name") or "there"
    except Exception:
        pass

    try:
        payload = build_greeting_payload(first_name, os.environ.get("VOICE_PAGE_URL", ""))
        client.chat_postMessage(channel=dm_channel, **payload)
    except Exception:
        logger.exception("ea-reset: failed to send greeting")

    respond(text=f"Reset complete — {deleted} messages cleared.")
