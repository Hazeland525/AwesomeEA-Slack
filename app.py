import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from listeners import register_listeners
from listeners.events.message import build_greeting_payload

load_dotenv(dotenv_path=".env", override=False)

logging.basicConfig(level=logging.DEBUG)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    client=WebClient(
        base_url=os.environ.get("SLACK_API_URL", "https://slack.com/api"),
        token=os.environ.get("SLACK_BOT_TOKEN"),
    ),
)

register_listeners(app)


def _send_startup_greeting() -> None:
    """Send a greeting DM on startup, bypassing the 12h throttle."""
    if os.environ.get("GREET_ON_STARTUP", "").lower() != "true":
        return
    demo_user_id = os.environ.get("DEMO_USER_ID", "").strip()
    if not demo_user_id:
        return

    logger = logging.getLogger(__name__)
    try:
        info = app.client.users_info(user=demo_user_id)
        profile = info.get("user", {}).get("profile", {})
        first_name = (
            profile.get("first_name") or profile.get("display_name") or "there"
        )
        dm_channel = app.client.conversations_open(users=[demo_user_id])["channel"]["id"]
        payload = build_greeting_payload(first_name, os.environ.get("VOICE_PAGE_URL", ""))
        app.client.chat_postMessage(channel=dm_channel, **payload)
        logger.info(f"Startup greeting sent to {demo_user_id}")
    except Exception:
        logger.exception("Failed to send startup greeting")


if __name__ == "__main__":
    _send_startup_greeting()
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
