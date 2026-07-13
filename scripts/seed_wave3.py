#!/usr/bin/env python3
"""Wave 3 seed: Lofty AI agent-interaction thread, research updates, QA, roadmap, links."""

import os, sys, time
from pathlib import Path
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

CAST = {
    "sue":     {"username": "Sue Chen",        "icon_url": "https://files.catbox.moe/3p3ywc.jpg"},
    "steven":  {"username": "Steven Johnson",  "icon_url": "https://files.catbox.moe/xjzh9s.jpg"},
    "tim":     {"username": "Tim Smith",       "icon_url": "https://files.catbox.moe/9zch2e.jpg"},
    "jane":    {"username": "Jane Miller",     "icon_url": "https://files.catbox.moe/osxy8i.jpg"},
    "rosario": {"username": "Rosario Bennet",  "icon_url": "https://files.catbox.moe/ei401h.jpg"},
    "eliza":   {"username": "Eliza Berry",     "icon_url": "https://files.catbox.moe/482xi6.jpg"},
    "phillip": {"username": "Phillip Lim",     "icon_url": "https://files.catbox.moe/ovu83g.jpg"},
}

MESSAGES = [
    # ── #design-review — Lofty AI agent interaction UI ───────────────────────
    {
        "ch": "design-review", "persona": "sue",
        "id": "lofty-ai-ui",
        "text": "{hazel} — can you share the latest UI for the Lofty AI agent interaction? "
                "Need it before the roadmap review Thursday. Specifically the chat/prompt surface and how we're handling streaming responses.",
    },
    {
        "ch": "design-review", "persona": "eliza",
        "thread": "lofty-ai-ui",
        "text": "Same ask from my side — I need to align the component library to whatever direction we're going on the agent UI. "
                "Here's a reference I've been looking at for conversational UI patterns: "
                "https://www.nngroup.com/articles/ai-chat-ux/ — their distinction between chat and command surfaces is useful.",
    },
    {
        "ch": "design-review", "persona": "tim",
        "thread": "lofty-ai-ui",
        "text": "From eng perspective: we need to know if the streaming text rendering is in-scope for this sprint or if we're mocking it. "
                "Big implementation difference. Also flagging this piece on motion in AI interfaces: "
                "https://design.google/library/conversation-design-best-practices",
    },
    {
        "ch": "design-review", "persona": "rosario",
        "thread": "lofty-ai-ui",
        "text": "Back-end is ready to stream tokens. The surface is on design/front-end. "
                "Whatever the UI spec says we can support it.",
    },
    {
        "ch": "design-review", "persona": "eliza",
        "text": "Dropped a first-pass AI interaction exploration in Figma — very rough, more for alignment than review. "
                "Covers: prompt input, streaming state, error/empty states. "
                "https://www.figma.com/design/lofty-ai-interaction-v0 — comments open.",
    },

    # ── #user-research — AI interaction research ─────────────────────────────
    {
        "ch": "user-research", "persona": "jane",
        "id": "ai-interaction-research",
        "text": "Sharing early findings from the Lofty AI interaction research sprint:\n\n"
                "• Users expect immediate visual feedback when the agent is 'thinking'\n"
                "• Streaming text was preferred over a loading spinner in 5/6 sessions\n"
                "• Participants wanted to be able to interrupt mid-response\n\n"
                "Full notes: https://www.notion.so/lofty-ai-ux-research-sprint1\n"
                "Also worth reading for context: https://www.uxdesign.cc/designing-for-ai-streaming-responses",
    },
    {
        "ch": "user-research", "persona": "sue",
        "thread": "ai-interaction-research",
        "text": "The interrupt pattern is important — we need to spec that before we ship. "
                "Can we get that into the Thursday review alongside the UI?",
    },
    {
        "ch": "user-research", "persona": "steven",
        "thread": "ai-interaction-research",
        "text": "Analytics from the beta: users who saw streaming responses had 34% lower drop-off on the AI feature vs. the spinner group. "
                "Aligns perfectly with Jane's sessions.",
    },
    {
        "ch": "user-research", "persona": "jane",
        "text": "Round 3 screener is live — targeting users who've tried at least one AI assistant (any app). "
                "Aiming for 8 sessions next week focused specifically on the agent interaction surface.",
    },

    # ── #product — roadmap & QA ───────────────────────────────────────────────
    {
        "ch": "product", "persona": "sue",
        "id": "ai-roadmap",
        "text": "Roadmap check-in for Lofty AI feature:\n\n"
                "• Agent interaction UI — in design, needs spec by Thursday\n"
                "• Streaming response surface — eng-ready, waiting on design\n"
                "• Interrupt/cancel pattern — TBD, needs research input\n"
                "• QA plan — not started yet\n\n"
                "We need to lock scope by end of week or this slips past the release window.",
    },
    {
        "ch": "product", "persona": "phillip",
        "thread": "ai-roadmap",
        "text": "From QA: I can't write test cases for the AI interaction flows until the spec is locked. "
                "If design shares by Thursday I can have a draft QA plan by Monday. "
                "That's the minimum runway to hit the window.",
    },
    {
        "ch": "product", "persona": "tim",
        "thread": "ai-roadmap",
        "text": "Streaming is implemented and works in local. "
                "The interrupt pattern will take 2–3 days once we have the UX spec. "
                "Thursday handoff → feature-complete by following Wednesday is realistic.",
    },
    {
        "ch": "product", "persona": "steven",
        "thread": "ai-roadmap",
        "text": "Token streaming API is stable. Rate-limiting and error handling are in place. "
                "We're unblocked on the back-end side — just need the design spec.",
    },
    {
        "ch": "product", "persona": "phillip",
        "id": "ai-qa-plan",
        "text": "Starting a QA tracking thread for Lofty AI interaction. Will update as spec comes in:\n\n"
                "• [ ] Streaming render — correct behaviour at <100ms, 100–500ms, >500ms token intervals\n"
                "• [ ] Interrupt/cancel mid-stream\n"
                "• [ ] Error state (network drop mid-stream)\n"
                "• [ ] Empty state (no response)\n"
                "• [ ] Accessibility — screen reader with streaming text\n"
                "• [ ] iOS 16/17/18 render\n"
                "• [ ] Android 13/14 render\n\n"
                "Reply to add anything missing.",
    },

    # ── #general — links and context for the canvas ──────────────────────────
    {
        "ch": "general", "persona": "eliza",
        "id": "ai-design-reads",
        "text": "Collecting good reads on AI/agent UX design ahead of Thursday — dropping them here:\n\n"
                "• NNGroup on AI chat UX: https://www.nngroup.com/articles/ai-chat-ux/\n"
                "• Google on conversation design: https://design.google/library/conversation-design-best-practices\n"
                "• UX Collective on streaming UIs: https://www.uxdesign.cc/designing-for-ai-streaming-responses\n"
                "• Figma on designing for AI: https://www.figma.com/blog/designing-for-ai-products/\n\n"
                "Add anything you've found useful.",
    },
    {
        "ch": "general", "persona": "jane",
        "thread": "ai-design-reads",
        "text": "Adding: https://www.microsoft.com/design/fluent/ai — "
                "Microsoft's Fluent AI design guidelines. Their thinking on disclosure and progressive trust is directly applicable.",
    },
    {
        "ch": "general", "persona": "steven",
        "thread": "ai-design-reads",
        "text": "Also this from Anthropic on building trustworthy AI products: "
                "https://www.anthropic.com/news/claude-character — "
                "not strictly a UX doc but the framing around honesty and predictability is useful.",
    },
    {
        "ch": "general", "persona": "sue",
        "text": "Thursday review agenda updated: (1) Lofty AI agent interaction UI, (2) interrupt pattern spec, "
                "(3) roadmap scope lock. Come with opinions.",
    },

    # ── #random — light texture ───────────────────────────────────────────────
    {
        "ch": "random", "persona": "tim",
        "text": "I've now asked three different AI assistants to help me plan a weekend trip "
                "and gotten three completely different answers. "
                "We are in the very early days of this stuff.",
    },
    {
        "ch": "random", "persona": "rosario",
        "text": "Anyone else's Figma AI suggestions getting way too confident? "
                "It keeps offering to 'clean up my design system'. Sir. Do not.",
    },
]


def resolve_hazel(client):
    try:
        wc = WebClient(token=os.environ.get("SLACK_USER_TOKEN", ""))
        uid = wc.auth_test().get("user_id") or wc.auth_test().get("user")
        return f"<@{uid}>" if uid else "@Hazel"
    except Exception:
        return "@Hazel"


def resolve_channels(client, names):
    found = {}
    cursor = None
    while True:
        resp = client.conversations_list(
            limit=200, types="public_channel,private_channel",
            team_id=os.environ["SLACK_TEAM_ID"],
            **({"cursor": cursor} if cursor else {}),
        )
        for ch in resp["channels"]:
            if ch["name"] in names:
                found[ch["name"]] = ch["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor or len(found) == len(names):
            break
    for cid in found.values():
        try:
            client.conversations_join(channel=cid)
        except SlackApiError:
            pass
    return found


def post_one(client, channel_id, persona_key, text, thread_ts=None):
    p = CAST[persona_key]
    kwargs = dict(channel=channel_id, text=text, username=p["username"], icon_url=p["icon_url"])
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    return client.chat_postMessage(**kwargs)


def main():
    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    hazel = resolve_hazel(client)

    ch_names = list({m["ch"] for m in MESSAGES})
    channels = resolve_channels(client, ch_names)

    thread_ts_map = {}
    posted = 0

    for msg in MESSAGES:
        ch_id = channels[msg["ch"]]
        text = msg["text"].replace("{hazel}", hazel)
        parent_id = msg.get("id")
        thread_id = msg.get("thread")
        thread_ts = thread_ts_map.get(thread_id) if thread_id else None

        try:
            resp = post_one(client, ch_id, msg["persona"], text, thread_ts)
            ts = resp["ts"]
            if parent_id:
                thread_ts_map[parent_id] = ts
            posted += 1
            print(f"  ✓ #{msg['ch']} [{msg['persona']}]: {text[:60].strip()}…")
            time.sleep(0.4)
        except SlackApiError as e:
            print(f"  ✗ #{msg['ch']} [{msg['persona']}]: {e.response['error']}", file=sys.stderr)

    print(f"\nDone — {posted}/{len(MESSAGES)} messages posted.")


if __name__ == "__main__":
    main()
