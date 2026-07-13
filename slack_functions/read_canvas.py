import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def _extract_text(blocks: list) -> str:
    """Recursively pull plain text out of Slack rich_text blocks."""
    parts = []
    for block in blocks:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif "elements" in block:
                parts.append(_extract_text(block["elements"]))
    return " ".join(p for p in parts if p).strip()


def read_canvas(client: WebClient, canvas_id: str) -> dict:
    """Read a canvas by ID.

    Returns title, permalink, and a heading_text extracted from title_blocks.
    Note: the Slack Canvas API does not expose body content — only the canvas
    title/heading is readable via files.info. Body content can only be viewed
    by opening the permalink in Slack.
    """
    try:
        r = client.files_info(file=canvas_id)
        f = r["file"]
        heading = _extract_text(f.get("title_blocks", []))
        return {
            "id": canvas_id,
            "title": f.get("title", "Untitled"),
            "heading_text": heading,
            "permalink": f.get("permalink", ""),
            "channels": f.get("channels", []),
            "created": f.get("created"),
            "note": "Body content is not readable via the Slack API — share the permalink with the user to let them view it.",
        }
    except SlackApiError as e:
        if e.response.get("error") != "missing_scope":
            raise

    # Fallback via search if files:read scope isn't granted yet
    user_client = WebClient(token=os.environ["SLACK_USER_TOKEN"])
    tid = os.environ["SLACK_TEAM_ID"]
    resp = user_client.search_files(query=canvas_id, count=5, team_id=tid)
    matches = resp.get("files", {}).get("matches", [])
    match = next((m for m in matches if m["id"] == canvas_id), None)
    if not match:
        return {"id": canvas_id, "error": "canvas not found"}
    return {
        "id": canvas_id,
        "title": match.get("title", "Untitled"),
        "heading_text": None,
        "permalink": match.get("permalink", ""),
        "channels": match.get("channels", []),
        "created": match.get("created"),
        "note": "Body content is not readable via the Slack API — share the permalink with the user to let them view it.",
    }
