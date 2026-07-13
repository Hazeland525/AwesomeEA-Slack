import logging
import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


def ramp_up(client: WebClient, channel_id: str, limit: int = 50,
            oldest: str | None = None) -> list[dict]:
    """Pull message history from a channel.

    If oldest is provided (a Slack timestamp string), only messages newer than
    that timestamp are returned — used to surface only unread messages.
    """
    team_id = os.environ["SLACK_TEAM_ID"]
    try:
        client.conversations_join(channel=channel_id, team_id=team_id)
    except SlackApiError as e:
        logger.debug("conversations_join skipped for %s: %s", channel_id, e.response["error"])

    kwargs: dict = {"channel": channel_id, "limit": limit, "team_id": team_id}
    if oldest:
        kwargs["oldest"] = oldest

    response = client.conversations_history(**kwargs)
    return response["messages"]
