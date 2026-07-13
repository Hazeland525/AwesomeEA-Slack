from logging import Logger

from slack_bolt import Ack


def handle_start_voice_call(ack: Ack, logger: Logger):
    """Acknowledge the App Home 'Start a voice call' button.

    The button itself opens VOICE_URL client-side via its `url` field;
    this just acks the interaction payload Slack also sends.
    """
    ack()
    logger.debug("App Home voice call button clicked")
