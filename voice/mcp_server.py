"""
Alternate MCP-based implementation of the awesome-ea Slack tools.

NOT part of the live call path. The voice agent uses direct function-calling
via voice/server.py's /execute-tool endpoint instead. This file exists as a
reference implementation and can be run standalone for MCP client testing:

    ../.venv/bin/python voice/mcp_server.py   # starts on port 5051

Transport: streamable-http on port 5051 (Flask voice server is on 5050).
"""

import os
import sys

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from slack_sdk import WebClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from slack_functions import (
    create_canvas,
    post_message,
    ramp_up,
    resolve_contact,
    set_reminder,
)

mcp = FastMCP(
    "awesome-ea",
    port=5051,
    host="127.0.0.1",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _client() -> WebClient:
    return WebClient(token=os.environ["SLACK_BOT_TOKEN"])


# ── search ────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_workspace(query: str) -> dict:
    """Search the entire Slack workspace with a natural-language query.

    Use this for open-ended discovery — 'what's happening with the campaign?',
    'catch me up', 'find anything about the Q3 launch' — when you don't yet
    know which channel holds the relevant information.  Returns a ranked list
    of matching messages with channel names, authors, and permalinks.

    For pulling the full message history of a channel whose ID you already
    know, use ramp_up instead — RTS for discovery, ramp_up for detail.
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


@mcp.tool()
def ramp_up(channel_id: str, limit: int = 50) -> list:
    """Pull the recent message history of a specific Slack channel.

    Use this once you already know the channel ID — either because the user
    named it, or because search_workspace returned it.  Fetches up to `limit`
    messages and auto-joins the channel if the bot isn't already a member.

    For discovering which channel is relevant when the user hasn't specified
    one, use search_workspace first.
    """
    from slack_functions import ramp_up as _ramp_up
    return _ramp_up(_client(), channel_id=channel_id, limit=limit)


# ── contacts & messaging ──────────────────────────────────────────────────────

@mcp.tool()
def resolve_contact(query: str) -> dict:
    """Fuzzy-match a name or partial string against Slack users and channels.

    Returns a single best match or up to five candidates when ambiguous.
    Always call this before post_message or ramp_up if you only have a name,
    not an ID.
    """
    from slack_functions import resolve_contact as _resolve
    return _resolve(_client(), query=query)


@mcp.tool()
def post_message(target: str, text: str) -> dict:
    """Post a message to a Slack channel or user.

    `target` must be a Slack ID: channel ID (C…) or user ID (U…).
    If you only have a name, call resolve_contact first.
    Opens a DM automatically when target is a user ID.
    """
    from slack_functions import post_message as _post
    return _post(_client(), target=target, text=text)


# ── reminders ─────────────────────────────────────────────────────────────────

@mcp.tool()
def set_reminder(text: str, when: str) -> dict:
    """Create a Slack reminder for the authenticated user.

    `when` accepts natural-language strings ('in 10 minutes', 'tomorrow at
    9am') or a Unix timestamp.  Uses the user token internally — reminders
    appear in Slack's Later tab.
    """
    from slack_functions import set_reminder as _remind
    return _remind(_client(), text=text, when=when)


# ── canvases ──────────────────────────────────────────────────────────────────

@mcp.tool()
def create_canvas(
    channel_id: str,
    items: list,
    title: str = "Materials for review",
) -> dict:
    """Create a titled Slack canvas attached to a channel.

    The canvas appears in the channel's Canvas tab with `title` as its header.
    Each item in `items` must be a dict with a required "title" key and an
    optional "link" key.
    """
    from slack_functions import create_canvas as _canvas
    return _canvas(_client(), channel_id=channel_id, items=items, title=title)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting awesome-ea MCP server on http://127.0.0.1:5051")
    mcp.run(transport="streamable-http")
