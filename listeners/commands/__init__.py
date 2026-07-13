import json
import logging

from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from slack_functions import ramp_up, resolve_contact, post_message, set_reminder, create_canvas
from .ea_reset import handle_ea_reset

logger = logging.getLogger(__name__)


def _fmt(obj) -> str:
    return f"```{json.dumps(obj, indent=2, default=str)}```"


def handle_test_rampup(ack, respond, command, client: WebClient):
    """Usage: /test-rampup <channel_id>"""
    ack()
    channel_id = command["text"].strip()
    if not channel_id:
        respond(text="Usage: `/test-rampup <channel_id>`")
        return
    try:
        messages = ramp_up(client, channel_id)
        respond(text=f"*{len(messages)} messages from {channel_id}*\n{_fmt(messages)}")
    except SlackApiError as e:
        respond(text=f":warning: Slack error: `{e.response['error']}`")
    except Exception as e:
        logger.exception(e)
        respond(text=f":warning: {e}")


def handle_test_resolve(ack, respond, command, client: WebClient):
    """Usage: /test-resolve <query>"""
    ack()
    query = command["text"].strip()
    if not query:
        respond(text="Usage: `/test-resolve <query>`")
        return
    try:
        result = resolve_contact(client, query)
        respond(text=f"*resolve_contact({query!r})*\n{_fmt(result)}")
    except SlackApiError as e:
        respond(text=f":warning: Slack error: `{e.response['error']}`")
    except Exception as e:
        logger.exception(e)
        respond(text=f":warning: {e}")


def handle_test_postmessage(ack, respond, command, client: WebClient):
    """Usage: /test-postmessage <target> | <message text>"""
    ack()
    parts = command["text"].split("|", 1)
    if len(parts) < 2:
        respond(text="Usage: `/test-postmessage <channel_or_user_id> | <text>`")
        return
    target, text = parts[0].strip(), parts[1].strip()
    try:
        result = post_message(client, target, text)
        respond(text=f"*post_message sent*\n{_fmt(result)}")
    except SlackApiError as e:
        respond(text=f":warning: Slack error: `{e.response['error']}`")
    except Exception as e:
        logger.exception(e)
        respond(text=f":warning: {e}")


def handle_test_setreminder(ack, respond, command, client: WebClient):
    """Usage: /test-setreminder <text> | <when>"""
    ack()
    parts = command["text"].split("|", 1)
    if len(parts) < 2:
        respond(text="Usage: `/test-setreminder <text> | <when>`\nExample: `/test-setreminder Buy milk | in 10 minutes`")
        return
    text, when = parts[0].strip(), parts[1].strip()
    user_id = command["user_id"]
    try:
        result = set_reminder(client, text, when, user_id=user_id)
        respond(text=f"*Reminder set*\n{_fmt(result)}")
    except SlackApiError as e:
        respond(text=f":warning: Slack error: `{e.response['error']}`\n_Note: reminders.add may require a user token._")
    except Exception as e:
        logger.exception(e)
        respond(text=f":warning: {e}")


def handle_test_createcanvas(ack, respond, command, client: WebClient):
    """Usage: /test-createcanvas <channel_id> | <title1> <url1> | <title2> <url2> ...

    Each section after the first | is "title url" (space-separated, url optional).
    """
    ack()
    raw = command["text"].strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 2:
        respond(text="Usage: `/test-createcanvas <channel_id> | <title> <url> | <title> <url> ...`")
        return

    channel_id = parts[0]
    items = []
    for part in parts[1:]:
        if not part:
            continue
        tokens = part.rsplit(None, 1)
        if len(tokens) == 2 and tokens[1].startswith(("http://", "https://")):
            title, link = tokens[0], tokens[1]
        else:
            title, link = part, ""
        items.append({"title": title, "link": link})

    try:
        result = create_canvas(client, channel_id, items)
        respond(text=f"*Canvas created*\n{_fmt(result)}")
    except SlackApiError as e:
        respond(text=f":warning: Slack error: `{e.response['error']}`")
    except Exception as e:
        logger.exception(e)
        respond(text=f":warning: {e}")


def register(app: App):
    app.command("/test-rampup")(handle_test_rampup)
    app.command("/test-resolve")(handle_test_resolve)
    app.command("/test-postmessage")(handle_test_postmessage)
    app.command("/test-setreminder")(handle_test_setreminder)
    app.command("/test-createcanvas")(handle_test_createcanvas)
    app.command("/ea-reset")(handle_ea_reset)
