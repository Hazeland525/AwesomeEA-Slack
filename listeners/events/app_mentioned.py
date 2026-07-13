from logging import Logger

from slack_bolt import BoltContext, Say
from slack_sdk import WebClient


def handle_app_mentioned(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
):
    """Handle @mentions in channels — direct the user to DM the bot."""
    if event.get("subtype") or event.get("bot_id"):
        return
    try:
        thread_ts = event.get("thread_ts") or event["ts"]
        say(
            text="Hi! I work through direct messages. Send me a DM to get started.",
            thread_ts=thread_ts,
        )
    except Exception as e:
        logger.exception(f"Failed to handle app mention: {e}")
