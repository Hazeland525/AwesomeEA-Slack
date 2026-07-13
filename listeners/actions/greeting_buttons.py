from logging import Logger

from slack_bolt import Ack, Say


def handle_morning_huddle(ack: Ack, logger: Logger):
    ack()
    logger.debug("Morning Huddle button clicked")


def handle_my_tasks(ack: Ack, say: Say, logger: Logger):
    ack()
    try:
        say("📋 *My Tasks* — this feature is coming soon!")
    except Exception as e:
        logger.exception(f"my_tasks handler failed: {e}")


def handle_brainstorm(ack: Ack, say: Say, logger: Logger):
    ack()
    try:
        say("💡 *Brainstorm* — this feature is coming soon!")
    except Exception as e:
        logger.exception(f"brainstorm handler failed: {e}")
