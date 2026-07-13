from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def delete_canvas(client: WebClient, canvas_id: str) -> dict:
    """Delete a canvas and remove it from every channel tab it appears in.

    First calls canvases.access.delete to detach the canvas from all its
    channel tabs, then canvases.delete to permanently remove it.
    Returns {"ok", "canvas_id", "removed_from_channels"}.
    """
    removed = []
    try:
        info = client.files_info(file=canvas_id)
        channel_ids = info["file"].get("channels", [])
        if channel_ids:
            client.canvases_access_delete(canvas_id=canvas_id, channel_ids=channel_ids)
            removed = channel_ids
    except SlackApiError:
        pass  # best-effort tab removal; proceed to delete regardless

    response = client.canvases_delete(canvas_id=canvas_id)
    return {"ok": response["ok"], "canvas_id": canvas_id, "removed_from_channels": removed}
