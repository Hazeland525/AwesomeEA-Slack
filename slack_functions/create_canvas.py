from slack_sdk import WebClient


def create_canvas(
    client: WebClient,
    channel_id: str,
    items: list[dict],
    title: str = "Materials for review",
) -> dict:
    """Create a canvas attached to a channel using conversations.canvases.create.

    This is the only Slack API call that produces a canvas visible in the
    channel's Canvas tab. The title becomes the first # heading so Slack
    displays it as the canvas title in the tab listing.
    Each item in `items` should have "title" (str) and optionally "link" (str).
    Returns {"ok", "canvas_id"}.
    """
    lines = [f"# {title}", ""]
    for item in items:
        item_title = item.get("title", "")
        link = item.get("link", "")
        lines.append(f"- [{item_title}]({link})" if link else f"- {item_title}")

    response = client.canvases_create(
        channel_id=channel_id,
        title=title,
        document_content={
            "type": "markdown",
            "markdown": "\n".join(lines),
        },
    )
    return {"ok": response["ok"], "canvas_id": response["canvas_id"]}
