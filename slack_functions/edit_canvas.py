from slack_sdk import WebClient


def edit_canvas(client: WebClient, canvas_id: str, items: list[dict]) -> dict:
    """Append items to an existing canvas via canvases.edit.

    Each item in `items` should have "title" (str) and optionally "link" (str).
    Note: the Slack API does not support changing a canvas title after creation,
    and background images are not available via the Canvas API.
    Returns {"ok", "canvas_id"}.
    """
    lines = []
    for item in items:
        item_title = item.get("title", "")
        link = item.get("link", "")
        lines.append(f"- [{item_title}]({link})" if link else f"- {item_title}")

    response = client.canvases_edit(
        canvas_id=canvas_id,
        changes=[{
            "operation": "insert_at_end",
            "document_content": {
                "type": "markdown",
                "markdown": "\n".join(lines),
            },
        }],
    )
    return {"ok": response["ok"], "canvas_id": canvas_id}
