import os

import requests
from slack_sdk import WebClient


def search_workspace(client: WebClient, query: str) -> dict:
    """Search the workspace via Slack's RTS (assistant.search.context).

    Uses SLACK_USER_TOKEN (needs search:read.public scope).
    Returns ranked messages with channel name, author, content, and permalink.
    For pulling full history of a known channel, use ramp_up instead.
    """
    resp = requests.post(
        "https://slack.com/api/assistant.search.context",
        headers={"Authorization": f"Bearer {os.environ['SLACK_USER_TOKEN']}"},
        json={"query": query, "team_id": os.environ["SLACK_TEAM_ID"]},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"assistant.search.context error: {data.get('error')}")
    return data["results"]
