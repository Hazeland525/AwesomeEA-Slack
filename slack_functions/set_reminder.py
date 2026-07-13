import os

from slack_sdk import WebClient


def set_reminder(client: WebClient, text: str, when: str, user_id: str | None = None) -> dict:
    """Create a reminder via reminders.add.

    Uses the SLACK_USER_TOKEN from env because bot tokens are rejected by
    reminders.add with not_allowed_token_type on Enterprise Grid.
    `when` accepts a Unix timestamp (int/str) or Slack natural-language time
    strings like "in 10 minutes" or "tomorrow at noon".
    Returns the reminder object from Slack.
    """
    user_client = WebClient(token=os.environ["SLACK_USER_TOKEN"])
    response = user_client.reminders_add(
        text=text,
        time=when,
        team_id=os.environ["SLACK_TEAM_ID"],
    )
    return response["reminder"]
