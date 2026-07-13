from slack_sdk import WebClient


def post_message(client: WebClient, target: str, text: str) -> dict:
    """Post a message to a channel or user (by ID).

    If target is a user ID (starts with 'U'), opens a DM first.
    Returns {"ok", "channel", "ts"}.
    """
    if target.startswith("U"):
        dm = client.conversations_open(users=[target])
        channel = dm["channel"]["id"]
    else:
        channel = target

    response = client.chat_postMessage(channel=channel, text=text)
    return {"ok": response["ok"], "channel": response["channel"], "ts": response["ts"]}
