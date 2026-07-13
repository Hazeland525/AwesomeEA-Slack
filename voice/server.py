import json
import logging
import os
import sys
import threading
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, request
from slack_sdk import WebClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

# Allow importing from the project root (slack_functions lives there)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from slack_functions import (  # noqa: E402
    create_canvas,
    delete_canvas,
    edit_canvas,
    list_canvases,
    post_message,
    ramp_up,
    read_canvas,
    resolve_contact,
    search_workspace,
    set_reminder,
)

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", static_url_path="/static")

def _save_memory(_client, note: str) -> dict:
    user_id = _get_user_id()
    if not user_id:
        return {"ok": False, "error": "no user_id"}
    prefs = _load_prefs()
    existing = prefs.get(user_id, "")
    # Append the new note to the existing memory
    updated = (existing.rstrip(".") + ". " + note.strip()).strip(". ")
    prefs[user_id] = updated
    with open(PREFS_PATH, "w") as f:
        json.dump(prefs, f, indent=2)
    try:
        from listeners.views.app_home_builder import build_app_home_view
        bot_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        bot_client.views_publish(user_id=user_id, view=build_app_home_view(pref=updated))
    except Exception:
        logger.exception("save_memory: failed to republish home")
    return {"ok": True, "memory_updated": True}


TOOLS = {
    "ramp_up": ramp_up,
    "resolve_contact": resolve_contact,
    "post_message": post_message,
    "set_reminder": set_reminder,
    "create_canvas": create_canvas,
    "edit_canvas": edit_canvas,
    "list_canvases": list_canvases,
    "read_canvas": read_canvas,
    "delete_canvas": delete_canvas,
    "search_workspace": search_workspace,
    "save_memory": _save_memory,
}

PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "preferences.json")

# In-memory session action log: session_id -> list[action entry]
session_log: dict[str, list[dict]] = {}

# Slack user id resolved once from SLACK_USER_TOKEN
_cached_user_id: str | None = None
_cached_first_name: str | None = None
_cached_channel_ids: dict | None = None

# Channels to include in a full morning ramp-up
BRIEFING_CHANNELS = ["product", "design-review", "user-research", "general"]


def _get_user_id() -> str:
    global _cached_user_id
    if _cached_user_id:
        return _cached_user_id
    try:
        user_client = WebClient(token=os.environ.get("SLACK_USER_TOKEN", ""))
        me = user_client.auth_test()
        _cached_user_id = me.get("user_id") or me.get("user") or ""
    except Exception:
        _cached_user_id = ""
    return _cached_user_id


def _get_first_name() -> str:
    global _cached_first_name
    if _cached_first_name is not None:
        return _cached_first_name
    try:
        uid = _get_user_id()
        if uid:
            user_client = WebClient(token=os.environ.get("SLACK_USER_TOKEN", ""))
            profile = user_client.users_profile_get(user=uid).get("profile", {})
            _cached_first_name = (
                profile.get("first_name")
                or (profile.get("real_name", "") or "").split()[0]
                or ""
            )
        else:
            _cached_first_name = ""
    except Exception:
        _cached_first_name = ""
    return _cached_first_name


def _get_channel_ids() -> dict[str, str]:
    """Return {channel_name: channel_id} for BRIEFING_CHANNELS (cached)."""
    global _cached_channel_ids
    if _cached_channel_ids is not None:
        return _cached_channel_ids
    result: dict[str, str] = {}
    try:
        bot_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        cursor = None
        while True:
            resp = bot_client.conversations_list(
                limit=200,
                types="public_channel,private_channel",
                team_id=os.environ.get("SLACK_TEAM_ID", ""),
                **({"cursor": cursor} if cursor else {}),
            )
            for ch in resp.get("channels", []):
                if ch["name"] in BRIEFING_CHANNELS:
                    result[ch["name"]] = ch["id"]
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor or len(result) == len(BRIEFING_CHANNELS):
                break
    except Exception:
        pass
    _cached_channel_ids = result
    return result


def _load_prefs() -> dict:
    try:
        with open(PREFS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _result_summary(name: str, args: dict, result) -> dict:
    if name == "post_message":
        return {"target": args.get("target", ""), "text": args.get("text", "")}
    if name == "set_reminder":
        return {"text": args.get("text", ""), "when": args.get("when", "")}
    if name == "create_canvas":
        canvas_id = result.get("canvas_id") if isinstance(result, dict) else None
        return {"title": args.get("title", "Materials for review"), "canvas_id": canvas_id}
    if name == "search_workspace":
        return {"query": args.get("query", "")}
    if name == "ramp_up":
        channel_id = args.get("channel_id", "")
        id_to_name = {v: k for k, v in (_get_channel_ids() or {}).items()}
        channel_name = id_to_name.get(channel_id, channel_id)
        messages = []
        if isinstance(result, list):
            for msg in result[:15]:
                text = msg.get("text", "").strip()
                username = msg.get("username") or msg.get("user", "unknown")
                if text:
                    messages.append({"username": username, "text": text[:300]})
        return {"channel_id": channel_id, "channel_name": channel_name, "messages": messages}
    if name == "resolve_contact":
        return {"query": args.get("query", "")}
    return {}


def _generate_recap_summary(log: list[dict]) -> str | None:
    """Call GPT to produce a narrative recap of what was discussed in the huddle."""
    channel_sections: list[str] = []
    actions: list[str] = []

    for entry in log:
        name = entry["tool_name"]
        args = entry["arguments"]
        s = entry["result_summary"]

        if name == "ramp_up":
            msgs = s.get("messages", [])
            ch = s.get("channel_name") or s.get("channel_id", "?")
            if msgs:
                lines = [f"  - {m['username']}: {m['text']}" for m in msgs]
                channel_sections.append(f"#{ch}:\n" + "\n".join(lines))
        elif name == "post_message":
            target = s.get("target") or args.get("target", "?")
            text = (s.get("text") or args.get("text", ""))[:120]
            actions.append(f"Sent message to {target}: \"{text}\"")
        elif name == "set_reminder":
            text = s.get("text") or args.get("text", "")
            when = s.get("when") or args.get("when", "")
            actions.append(f"Set reminder: \"{text}\" at {when}")
        elif name == "create_canvas":
            title = s.get("title") or args.get("title", "Canvas")
            actions.append(f"Created canvas: {title}")

    if not channel_sections and not actions:
        return None

    context_parts: list[str] = []
    if channel_sections:
        context_parts.append("Slack messages surfaced during this morning's voice huddle:\n")
        context_parts.extend(channel_sections)
    if actions:
        context_parts.append("\nActions taken:")
        context_parts.extend(f"  - {a}" for a in actions)

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={
                "model": "gpt-4.1-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are summarising a morning voice huddle. "
                            "Write exactly 2-3 ultra-short bullet points (•) in Slack mrkdwn. "
                            "Each bullet: one sentence max, specific and actionable. "
                            "Skip filler — only what matters: key decisions, blockers, actions taken. "
                            "Output only the bullets, nothing else."
                        ),
                    },
                    {"role": "user", "content": "\n".join(context_parts)},
                ],
                "max_tokens": 400,
                "temperature": 0.3,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.exception("GPT recap summary failed")
        return None


def _extract_memory_update(log: list[dict], recap: str | None, existing_pref: str) -> str | None:
    """Call GPT to derive an updated memory string from this session's activity."""
    if not log and not recap:
        return None

    actions_taken = []
    channels_checked = []
    for entry in log:
        name = entry["tool_name"]
        s = entry["result_summary"]
        if name == "ramp_up":
            channels_checked.append(s.get("channel_name") or s.get("channel_id", "?"))
        elif name == "post_message":
            actions_taken.append(f"posted message to {s.get('target', '?')}")
        elif name == "set_reminder":
            actions_taken.append(f"set reminder: {s.get('text', '')}")
        elif name == "create_canvas":
            actions_taken.append(f"created canvas: {s.get('title', '')}")

    parts = []
    if existing_pref:
        parts.append(f"Existing memory about this user:\n{existing_pref}")
    if recap:
        parts.append(f"Topics discussed in this huddle:\n{recap}")
    if channels_checked:
        parts.append(f"Channels they checked: {', '.join(channels_checked)}")
    if actions_taken:
        parts.append(f"Actions they requested: {', '.join(actions_taken)}")

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={
                "model": "gpt-4.1-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You maintain a concise memory profile about a user for a voice executive assistant. "
                            "Based on what you know about the user and what happened in this session, "
                            "write an updated profile in 2-4 short sentences. "
                            "Focus on role, communication style, working preferences, and recurring patterns. "
                            "Be specific and useful — e.g. 'Product designer. Prefers concise morning briefs. "
                            "Often delegates channel updates to the assistant.' "
                            "If the existing memory is already accurate and nothing new was learned, return it unchanged. "
                            "Output only the profile text, no heading or preamble."
                        ),
                    },
                    {"role": "user", "content": "\n\n".join(parts)},
                ],
                "max_tokens": 150,
                "temperature": 0.3,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.exception("GPT memory extraction failed")
        return None


def _build_recap_blocks(log: list[dict], summary: str | None = None) -> list[dict]:
    header = {"type": "header", "text": {"type": "plain_text", "text": "✅ Morning huddle recap"}}

    if not log:
        return [
            header,
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "We talked, but I didn't take any actions this time.",
                },
            },
        ]

    if summary:
        return [
            header,
            {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
        ]

    # Fallback when GPT summary unavailable
    bullets = []
    for entry in log:
        name = entry["tool_name"]
        args = entry["arguments"]
        s = entry["result_summary"]

        if name == "post_message":
            target = s.get("target") or args.get("target", "?")
            text = (s.get("text") or args.get("text", ""))[:60]
            bullets.append(f"• Posted to {target}: \"{text}\"")
        elif name == "set_reminder":
            text = s.get("text") or args.get("text", "")
            when = s.get("when") or args.get("when", "")
            bullets.append(f"• Reminder set: \"{text}\" at {when}")
        elif name == "create_canvas":
            title = s.get("title") or args.get("title", "Canvas")
            canvas_id = s.get("canvas_id")
            if canvas_id:
                bullets.append(f"• Canvas created: <https://app.slack.com/docs/{canvas_id}|{title}>")
            else:
                bullets.append(f"• Canvas created: {title}")
        elif name == "search_workspace":
            query = s.get("query") or args.get("query", "")
            bullets.append(f"• Searched workspace: \"{query}\"")
        elif name == "ramp_up":
            ch = s.get("channel_name") or s.get("channel_id") or args.get("channel_id", "?")
            bullets.append(f"• Caught up on #{ch}")
        elif name == "resolve_contact":
            query = s.get("query") or args.get("query", "")
            bullets.append(f"• Looked up contact: \"{query}\"")
        else:
            bullets.append(f"• {name}")

    return [
        header,
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(bullets)}},
    ]


def _post_feedback_prompt(user_id: str) -> None:
    bot_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    try:
        bot_client.chat_postMessage(
            channel=user_id,
            text="Quick one — how should I adjust?",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "Quick one — how should I adjust?"},
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "action_id": "feedback_just_right",
                            "text": {"type": "plain_text", "text": "🎯 Just right"},
                        },
                        {
                            "type": "button",
                            "action_id": "feedback_concise",
                            "text": {"type": "plain_text", "text": "🏃 Faster, more concise"},
                        },
                        {
                            "type": "button",
                            "action_id": "feedback_detail",
                            "text": {"type": "plain_text", "text": "🌊 More detail"},
                        },
                    ],
                },
            ],
        )
    except Exception:
        logger.exception("Failed to post feedback prompt")


@app.route("/")
def index():
    resp = make_response(app.send_static_file("index.html"))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/config")
def config():
    bot_client  = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    user_client = WebClient(token=os.environ.get("SLACK_USER_TOKEN", ""))
    workspace = "Slack"
    avatar_url = None
    try:
        r = bot_client.auth_test()
        workspace = r.get("team", "Slack")
    except Exception:
        pass
    try:
        me = user_client.auth_test()
        user_id = me.get("user_id") or me.get("user")
        if user_id:
            profile = user_client.users_profile_get(user=user_id)
            p = profile.get("profile", {})
            avatar_url = p.get("image_192") or p.get("image_72")
    except Exception:
        pass
    return jsonify({"workspace": workspace, "avatar_url": avatar_url})


@app.route("/token")
def token():
    # Generate a fresh session and initialise its log
    session_id = str(uuid.uuid4())
    session_log[session_id] = []

    # Build system instructions
    first_name = _get_first_name() or "there"
    channel_ids = _get_channel_ids()

    channel_list = "\n".join(
        f"  - #{name} → {cid}"
        for name, cid in sorted(channel_ids.items())
    ) or "  (channel IDs unavailable)"

    instructions = f"""You are awesome-ea, a voice-first Slack executive assistant.
The user's name is {first_name}.

At the very start of each session — before the user says anything — greet {first_name} warmly in one sentence and ask if they'd like a quick ramp-up of what's been happening. Example: "Good morning {first_name}! Want me to run through what's been happening across your channels?" Keep it natural and brief.

For a general catch-up, morning brief, or "ramp me up on everything", call ramp_up for each of these channels in sequence, then summarise what you found:
{channel_list}

When doing a ramp-up, NEVER speak between tool calls. Call every ramp_up tool silently first, then speak once with the full summary. Do not say "loading", "checking", "give me a moment", "still working on it", or anything like that. Silence until all tools are done, then one clean summary.

Help {first_name} catch up on their workspace, send messages, set reminders, and manage canvases. Be concise — this is a voice interface.

When {first_name} expresses a preference, says "next time do X", or asks you to remember something — call save_memory immediately with a concise note, before responding verbally.

When posting a message on {first_name}'s behalf, always frame it clearly as coming from {first_name} — not as if you are the user. For example: "{first_name} wanted me to share that…", "{first_name} is asking whether…", or "On behalf of {first_name}: …". Never write the message in first-person as if {first_name} sent it themselves."""

    try:
        pref_str = _load_prefs().get(_get_user_id(), "")
        if pref_str:
            instructions += f"\n\nUser preference: {pref_str}"
    except Exception:
        pass

    api_key = os.environ["OPENAI_API_KEY"]
    resp = requests.post(
        "https://api.openai.com/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "session": {
                "type": "realtime",
                "model": "gpt-realtime-2",
                "audio": {
                    "output": {"voice": "cedar"},
                },
                "instructions": instructions,
            }
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    data["session_id"] = session_id
    return jsonify(data)


@app.route("/execute-tool", methods=["POST"])
def execute_tool():
    body = request.get_json(force=True)
    name = body.get("name")
    args = body.get("arguments", {})
    session_id = body.get("session_id")

    fn = TOOLS.get(name)
    if fn is None:
        return jsonify({"error": f"Unknown tool: {name!r}"}), 400

    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    try:
        # For ramp_up: inject the user's last_read timestamp so only unread
        # messages are returned. Falls back to full history if unavailable.
        if name == "ramp_up" and "oldest" not in args:
            channel_id = args.get("channel_id", "")
            if channel_id:
                try:
                    user_client = WebClient(token=os.environ.get("SLACK_USER_TOKEN", ""))
                    info = user_client.conversations_info(channel=channel_id)
                    last_read = info.get("channel", {}).get("last_read")
                    if last_read and last_read != "0000000000.000000":
                        args = {**args, "oldest": last_read}
                except Exception:
                    pass

        result = fn(client, **args)

        # Enrich results with human-readable channel names for client toasts
        if isinstance(result, dict):
            id_to_name = {v: k for k, v in (_get_channel_ids() or {}).items()}
            if name == "post_message" and "channel" in result:
                ch_name = id_to_name.get(result["channel"])
                if ch_name:
                    result = {**result, "channel_name": f"#{ch_name}"}
            elif name == "create_canvas" and "canvas_id" in result:
                ch_id = args.get("channel_id", "")
                ch_name = id_to_name.get(ch_id)
                if ch_name:
                    result = {**result, "channel_name": f"#{ch_name}"}

        # Append to session log
        if session_id and session_id in session_log:
            session_log[session_id].append({
                "tool_name": name,
                "arguments": args,
                "result_summary": _result_summary(name, args, result),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return jsonify({"result": result})
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return jsonify({"error": str(e)}), 500


@app.route("/undo-message", methods=["POST"])
def undo_message():
    body = request.get_json(force=True)
    channel = body.get("channel")
    ts = body.get("ts")
    if not channel or not ts:
        return jsonify({"ok": False, "error": "channel and ts required"}), 400
    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    try:
        client.chat_delete(channel=channel, ts=ts)
        return jsonify({"ok": True})
    except Exception as e:
        logger.exception("undo_message failed")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/end-session", methods=["POST"])
def end_session():
    body = request.get_json(force=True)
    session_id = body.get("session_id")

    log = session_log.pop(session_id, []) if session_id else []
    user_id = _get_user_id()

    if not user_id:
        logger.warning("end-session: could not resolve user_id, skipping recap")
        return jsonify({"ok": False, "error": "no user_id"}), 500

    bot_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

    summary = _generate_recap_summary(log)

    # Post recap DM immediately
    try:
        bot_client.chat_postMessage(
            channel=user_id,
            text="✅ Morning huddle recap",
            blocks=_build_recap_blocks(log, summary=summary),
        )
    except Exception:
        logger.exception("Failed to post recap DM")

    # Extract and persist updated memory, then republish App Home
    memory_updated = False
    try:
        prefs = _load_prefs()
        existing_pref = prefs.get(user_id, "")
        new_pref = _extract_memory_update(log, summary, existing_pref)
        if new_pref and new_pref != existing_pref:
            prefs[user_id] = new_pref
            with open(PREFS_PATH, "w") as f:
                json.dump(prefs, f, indent=2)
            from listeners.views.app_home_builder import build_app_home_view
            bot_client.views_publish(user_id=user_id, view=build_app_home_view(pref=new_pref))
            memory_updated = True
    except Exception:
        logger.exception("Failed to update memory after session")

    # Delayed feedback prompt after 60 s
    threading.Timer(60, _post_feedback_prompt, args=[user_id]).start()

    return jsonify({"ok": True, "memory_updated": memory_updated})


if __name__ == "__main__":
    app.run(port=5050, debug=True)
