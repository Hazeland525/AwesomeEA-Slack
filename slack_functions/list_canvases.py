import os

from slack_sdk import WebClient


def list_canvases(client: WebClient, channel_id: str | None = None) -> dict:
    """List canvases the user can access, optionally filtered to a channel.

    Uses search.files with the SLACK_USER_TOKEN (search:read scope).
    Returns a list of {id, title, permalink, channels}.
    """
    user_client = WebClient(token=os.environ["SLACK_USER_TOKEN"])
    tid = os.environ["SLACK_TEAM_ID"]

    if channel_id:
        info = client.conversations_info(channel=channel_id)
        ch_name = info["channel"]["name"]
        query = f"in:#{ch_name}"
    else:
        query = "type:canvas"

    resp = user_client.search_files(query=query, count=20, team_id=tid)
    matches = resp.get("files", {}).get("matches", [])

    canvases = [
        {
            "id": m["id"],
            "title": m.get("title", "Untitled"),
            "permalink": m.get("permalink", ""),
            "channels": [
                ch
                for entries in m.get("shares", {}).get("public", {}).values()
                for ch in [entries[0].get("channel_name")] if entries
            ],
            "created": m.get("created"),
        }
        for m in matches
        if m.get("filetype") == "quip"
    ]
    return {"canvases": canvases, "count": len(canvases)}
