import json
import os
from logging import Logger

from slack_bolt import BoltContext
from slack_sdk import WebClient

from listeners.views.app_home_builder import build_app_home_view

PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "preferences.json")


def handle_app_home_opened(client: WebClient, context: BoltContext, logger: Logger):
    """Publish the App Home view when a user opens the app's Home tab."""
    try:
        pref = None
        try:
            with open(PREFS_PATH) as f:
                pref = json.load(f).get(context.user_id)
        except Exception:
            pass
        view = build_app_home_view(pref=pref)
        client.views_publish(user_id=context.user_id, view=view)
    except Exception as e:
        logger.exception(f"Failed to publish App Home: {e}")
