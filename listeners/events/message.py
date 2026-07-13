import json
import os
import time
from logging import Logger

from slack_bolt import BoltContext
from slack_sdk import WebClient

from agent.agent import run_agent
from agent.deps import AgentDeps
from thread_context.store import ConversationStore

GREETING_STATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "greeting_state.json"
)
_COOLDOWN = 12 * 3600  # 12 hours
_store = ConversationStore()


def build_greeting_payload(first_name: str, voice_url: str) -> dict:
    """Return the text + blocks for the greeting DM.  Single source of truth."""
    text = f"Good morning {first_name}. How would you like to get started?"
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "action_id": "morning_huddle",
                    "text": {"type": "plain_text", "text": "🎧 Morning Huddle"},
                    "url": voice_url,
                },
                {
                    "type": "button",
                    "action_id": "my_tasks",
                    "text": {"type": "plain_text", "text": "📋 My Tasks"},
                },
                {
                    "type": "button",
                    "action_id": "brainstorm",
                    "text": {"type": "plain_text", "text": "💡 Brainstorm"},
                },
            ],
        },
    ]
    return {"text": text, "blocks": blocks}


def _should_greet(user_id: str) -> bool:
    try:
        with open(GREETING_STATE_PATH) as f:
            last = json.load(f).get(user_id, 0)
        return time.time() - last > _COOLDOWN
    except Exception:
        return True


def _record_greeted(user_id: str) -> None:
    try:
        try:
            with open(GREETING_STATE_PATH) as f:
                state = json.load(f)
        except Exception:
            state = {}
        state[user_id] = time.time()
        with open(GREETING_STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def handle_message(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
):
    if event.get("subtype") or event.get("bot_id"):
        return
    if event.get("channel_type") != "im":
        return

    user_id = context.user_id
    channel_id = event["channel"]
    message_ts = event["ts"]
    thread_ts = event.get("thread_ts") or message_ts
    text = event.get("text", "").strip()

    # Send greeting if within cooldown window
    if _should_greet(user_id):
        first_name = "there"
        try:
            info = client.users_info(user=user_id)
            profile = info.get("user", {}).get("profile", {})
            first_name = (
                profile.get("first_name") or profile.get("display_name") or "there"
            )
        except Exception:
            pass
        try:
            payload = build_greeting_payload(first_name, os.environ.get("VOICE_PAGE_URL", ""))
            client.chat_postMessage(channel=channel_id, **payload)
            _record_greeted(user_id)
        except Exception as e:
            logger.exception(f"Failed to send greeting: {e}")
        return

    if not text:
        return

    # Run agent and reply in thread
    try:
        history = _store.get_history(channel_id, thread_ts) or []
        input_items = history + [{"role": "user", "content": text}]

        deps = AgentDeps(
            client=client,
            user_id=user_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            message_ts=message_ts,
            user_token=os.environ.get("SLACK_USER_TOKEN"),
        )

        result = run_agent(input_items, deps)
        reply = result.final_output or ""

        _store.set_history(channel_id, thread_ts, result.to_input_list())

        if reply:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=reply,
            )
    except Exception as e:
        logger.exception(f"Agent failed: {e}")
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="Sorry, something went wrong. Please try again.",
        )
