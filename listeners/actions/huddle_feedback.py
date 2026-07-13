import json
import os
from logging import Logger

from slack_bolt import Ack
from slack_sdk import WebClient

from listeners.views.app_home_builder import build_app_home_view

PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "preferences.json")

PREF_STRINGS = {
    "feedback_just_right": "Current pace and detail level works well; keep it.",
    "feedback_concise": "Be faster and more concise; short confirmations only.",
    "feedback_detail": "Give more detail and context when reporting.",
}


def _write_pref(user_id: str, pref: str) -> None:
    try:
        with open(PREFS_PATH) as f:
            prefs = json.load(f)
    except Exception:
        prefs = {}
    prefs[user_id] = pref
    with open(PREFS_PATH, "w") as f:
        json.dump(prefs, f, indent=2)


def _make_handler(action_id: str):
    def handler(ack: Ack, body: dict, client: WebClient, logger: Logger):
        ack()
        user_id = body["user"]["id"]
        pref = PREF_STRINGS[action_id]
        try:
            _write_pref(user_id, pref)
        except Exception as e:
            logger.exception(f"Failed to write preference: {e}")
        try:
            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                text="Got it — I'll remember that. 🧠",
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "Got it — I'll remember that. 🧠"},
                    }
                ],
            )
        except Exception as e:
            logger.exception(f"Failed to update feedback message: {e}")
        try:
            client.views_publish(user_id=user_id, view=build_app_home_view(pref=pref))
        except Exception as e:
            logger.exception(f"Failed to republish Home tab: {e}")
    return handler


handle_feedback_just_right = _make_handler("feedback_just_right")
handle_feedback_concise    = _make_handler("feedback_concise")
handle_feedback_detail     = _make_handler("feedback_detail")
