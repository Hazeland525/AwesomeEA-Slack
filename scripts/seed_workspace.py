#!/usr/bin/env python3
"""
Seed the Slack workspace with realistic messages from a 7-person cast.

Personas post via chat:write.customize (username + icon_url overrides).
Avatars are permanently hosted on catbox.moe — no local server required.

Requires bot scopes: chat:write, chat:write.customize, channels:history,
                     channels:join, im:history, groups:history

Usage:
  python scripts/seed_workspace.py          # seed all messages
  python scripts/seed_workspace.py --clean  # full clean (state file + channel sweep)
"""

import argparse
import json
import os
import sys
import time
import random
from pathlib import Path

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

STATE_FILE = Path(__file__).parent / ".seed_state.json"

# ── Cast ──────────────────────────────────────────────────────────────────────
#   Avatars uploaded to catbox.moe — permanent public URLs, no server needed.
CAST = {
    "sue":     {"username": "Sue Chen",        "icon_url": "https://files.catbox.moe/3p3ywc.jpg"},
    "steven":  {"username": "Steven Johnson",  "icon_url": "https://files.catbox.moe/xjzh9s.jpg"},
    "tim":     {"username": "Tim Smith",       "icon_url": "https://files.catbox.moe/9zch2e.jpg"},
    "jane":    {"username": "Jane Miller",     "icon_url": "https://files.catbox.moe/osxy8i.jpg"},
    "rosario": {"username": "Rosario Bennet",  "icon_url": "https://files.catbox.moe/ei401h.jpg"},
    "eliza":   {"username": "Eliza Berry",     "icon_url": "https://files.catbox.moe/482xi6.jpg"},
    "phillip": {"username": "Phillip Lim",     "icon_url": "https://files.catbox.moe/ovu83g.jpg"},
}


# ── Message script ────────────────────────────────────────────────────────────
#   ch:     channel name (must match workspace exactly)
#   persona: key into CAST
#   text:   message body (mrkdwn); use {hazel} to mention Hazel
#   id:     names this post as a thread parent
#   thread: reply in the thread whose parent has this id
#   NOTE: Tim's standalone in #product has no id — zero replies guaranteed.
MESSAGES = [
    # ── #general — lunch thread, demo announcement, thanks, article ───────────
    {
        "ch": "general", "persona": "sue",
        "text": "Friday demo at 4 pm — same Zoom link as usual. We'll walk through the Lofty nav prototype. "
                "Agenda in the channel topic.",
    },
    {
        "ch": "general", "persona": "rosario",
        "id": "gen-lunch",
        "text": "Anyone know if the taco place on 5th is back open? Trying to plan lunch.",
    },
    {
        "ch": "general", "persona": "tim",
        "thread": "gen-lunch",
        "text": "Yes — walked past yesterday, they're open. Al pastor is back on the menu.",
    },
    {
        "ch": "general", "persona": "eliza",
        "thread": "gen-lunch",
        "text": "Adding myself to this plan. What time?",
    },
    {
        "ch": "general", "persona": "phillip",
        "thread": "gen-lunch",
        "text": "Same. 12:30?",
    },
    {
        "ch": "general", "persona": "jane",
        "text": "Big thank you to everyone who helped recruit participants for the Lofty usability sessions. "
                "Hit 6 this week — above target.",
    },
    {
        "ch": "general", "persona": "steven",
        "id": "gen-article",
        "text": "Worth reading ahead of the nova work: "
                "https://www.nngroup.com/articles/mobile-navigation-patterns/ — "
                "solid breakdown of tab-bar vs gesture nav tradeoffs.",
    },
    {
        "ch": "general", "persona": "tim",
        "thread": "gen-article",
        "text": "The section on overflow menus is directly relevant to what we're debating. Good find.",
    },
    {
        "ch": "general", "persona": "eliza",
        "text": "Component library update: all Lofty nav variants are in Figma with proper auto-layout. "
                "Tag me if you spot inconsistencies.",
    },
    {
        "ch": "general", "persona": "rosario",
        "text": "Staging is green after this morning's deploy. All the flows we care about for Lofty are passing.",
    },

    # ── #random — weekend, coffee machine, meme ───────────────────────────────
    {
        "ch": "random", "persona": "tim",
        "text": "Anyone else's weekend involve rain and a home improvement project that got out of hand? "
                "Asking for a friend.",
    },
    {
        "ch": "random", "persona": "phillip",
        "id": "rand-coffee",
        "text": "The office espresso machine has been making a grinding noise for three days. "
                "Filed a facilities ticket. Nothing. I am escalating to interpretive dance.",
    },
    {
        "ch": "random", "persona": "rosario",
        "thread": "rand-coffee",
        "text": "I stopped using it last week and started bringing my own. It's fine. I'm fine. Everything is fine.",
    },
    {
        "ch": "random", "persona": "eliza",
        "text": "Has anyone seen the Figma 'vibe coding' meme going around? "
                "That image is our entire job description.",
    },
    {
        "ch": "random", "persona": "steven",
        "text": "Weekend recovery status: 40%. Projecting 100% by standup. Maybe.",
    },
    {
        "ch": "random", "persona": "jane",
        "text": "Offsite team photos are in the shared drive if anyone hasn't grabbed theirs yet.",
    },

    # ── #user-research — Jane's finding + replies ─────────────────────────────
    {
        "ch": "user-research", "persona": "jane",
        "id": "usability-finding",
        "text": "Wrapped 6 Lofty nav usability sessions this week. "
                "*Key finding: users consistently miss the secondary nav.* "
                "None of the 6 participants discovered it without prompting.\n\n"
                "Full report: https://notion.so/nova-nav-usability-w27",
    },
    {
        "ch": "user-research", "persona": "sue",
        "thread": "usability-finding",
        "text": "This confirms the survey signal from last sprint. Secondary nav is invisible. "
                "We either surface it properly or cut it — shipping it as-is isn't an option.",
    },
    {
        "ch": "user-research", "persona": "eliza",
        "thread": "usability-finding",
        "text": "Invisible secondary nav is a design hierarchy problem I've been flagging internally. "
                "The visual treatment isn't drawing the eye there at all. "
                "Can we schedule a dedicated review session on this?",
    },
    {
        "ch": "user-research", "persona": "jane",
        "thread": "usability-finding",
        "text": "Yes — I'll set up a session for next week. "
                "I want design and research in the room together looking at the recordings.",
    },
    {
        "ch": "user-research", "persona": "steven",
        "text": "Recruiting update: 3 confirmed participants for the next round, 4 warm leads. "
                "Should hit 8 without paid recruitment.",
    },
    {
        "ch": "user-research", "persona": "jane",
        "text": "Screener for round 2 is live. Targeting active mobile users who don't use advanced features — "
                "the exact segment that exposed the secondary nav issue.",
    },

    # ── #design-review — Eliza's critique + Jane asks Hazel ──────────────────
    {
        "ch": "design-review", "persona": "eliza",
        "id": "nav-critique",
        "text": "Opening a critique thread on the Lofty nav hierarchy before Thursday.\n\n"
                "Core issue: 4 primary items + a secondary overflow that no one finds. "
                "In usability testing the overflow was invisible to every participant. "
                "Proposal: collapse to 3 primary items + a 'More' tab, "
                "or promote the highest-traffic secondary item to primary and cut the rest.\n\n"
                "Thoughts before I revise the Figma file?",
    },
    {
        "ch": "design-review", "persona": "rosario",
        "thread": "nav-critique",
        "text": "Strong agree on collapsing. Fewer states = fewer edge cases = faster QA cycle. "
                "The 3+More pattern also has cleaner platform precedent on iOS and Android.",
    },
    {
        "ch": "design-review", "persona": "jane",
        "thread": "nav-critique",
        "text": "Research backs this — overflow was invisible to 100% of usability participants. "
                "If we keep it we need to make it dramatically more discoverable. "
                "3+More is the right call.",
    },
    {
        "ch": "design-review", "persona": "phillip",
        "thread": "nav-critique",
        "text": "From QA: the current overflow adds ~40% testing overhead per release cycle. "
                "Collapsing to 3+More would meaningfully cut regression time. +1.",
    },
    {
        "ch": "design-review", "persona": "eliza",
        "thread": "nav-critique",
        "text": "Aligned on all sides. Updating Figma to reflect 3+More — revised specs before Thursday.",
    },
    {
        "ch": "design-review", "persona": "sue",
        "text": "Thursday review will cover the Lofty nav critique. "
                "Please drop async feedback in threads before 10am so the live session can focus on decisions.",
    },
    {
        "ch": "design-review", "persona": "jane",
        "id": "ux-flow",
        "text": "{hazel}, where are we on the UX flow for the nav redesign? "
                "The usability sessions surfaced some things I want to walk through before you finalize — "
                "ideally before the 21st.",
    },
    {
        "ch": "design-review", "persona": "rosario",
        "thread": "ux-flow",
        "text": "Dropping the latest nav explorations here for context: "
                "https://www.figma.com/design/rK9mNqLpXsA7dBzViWh2Ue/Lofty-Nav-UX-Flow?node-id=0-1\n\n"
                "Pages 3–5 are most recent. Empty and error state frames are on page 6 "
                "but still have annotation gaps.",
    },
    {
        "ch": "design-review", "persona": "tim",
        "thread": "ux-flow",
        "text": "Before finalizing: back-navigation behaviour needs to be spec'd. "
                "Pop the stack vs. return to home tab — these are different implementations. "
                "Happy to jump on a call to sort it.",
    },
    {
        "ch": "design-review", "persona": "sue",
        "thread": "ux-flow",
        "text": "Adding to Thursday's agenda. {hazel} — even a brief status per edge case "
                "(done / in progress / blocked) would help us know what we're reviewing vs. what's still open.",
    },
    {
        "ch": "design-review", "persona": "eliza",
        "text": "Standardized component names in the Figma file to match the new token structure from last week's sync. "
                "If you had local copies of the old components, relink them.",
    },
    {
        "ch": "design-review", "persona": "phillip",
        "text": "QA flag: 3 flows in the Figma file are still missing explicit error states. "
                "I can't write test cases for them until those are defined.",
    },

    # ── #product — launch decision, QA checklist, Tim standalone (LAST) ───────
    {
        "ch": "product", "persona": "jane",
        "text": "Lofty nav research brief is in Notion — "
                "summary of usability findings for anyone who wants context before sprint planning.",
    },
    {
        "ch": "product", "persona": "steven",
        "text": "API update: profile-context endpoint is on track for Monday deployment. No blockers.",
    },
    {
        "ch": "product", "persona": "sue",
        "id": "nova-launch",
        "text": "Scope check before we lock the sprint — what's our confidence on shipping full Lofty nav this release? "
                "Want eng, design, and QA all seeing the same picture.",
    },
    {
        "ch": "product", "persona": "phillip",
        "thread": "nova-launch",
        "text": "From QA: I need a minimum of 4 days for full regression on the nav. "
                "Dev-complete by EOD Monday at the latest. We're not tracking to that right now.",
    },
    {
        "ch": "product", "persona": "steven",
        "thread": "nova-launch",
        "text": "Worth flagging: the profile-API dependency for bottom-nav deep links lands Monday. "
                "Anything before Monday means shipping without deep links or carrying a fallback.",
    },
    {
        "ch": "product", "persona": "tim",
        "thread": "nova-launch",
        "text": "The fallback is doable but it's a sprint of debt we'd need to carry. "
                "I'd lean toward taking the extra week and doing it clean.",
    },
    {
        "ch": "product", "persona": "sue",
        "thread": "nova-launch",
        "text": "OK — locking the Lofty nav launch for the 21st. "
                "Revised sprint cut going to the board now. Please review and flag anything that shifts.",
    },
    {
        "ch": "product", "persona": "phillip",
        "id": "qa-checklist",
        "text": "QA checklist for Lofty nav — tracking here so it's visible:\n\n"
                "• [ ] Nav renders on iOS 16, 17, 18\n"
                "• [ ] Nav renders on Android 13, 14\n"
                "• [ ] Bottom-nav deep links (post API deploy)\n"
                "• [ ] Deep-link fallback state (pre API deploy)\n"
                "• [ ] Back-navigation matches UX spec\n"
                "• [ ] Empty and error states correct\n"
                "• [ ] 3+More overflow pattern regression\n"
                "• [ ] Scroll-collapse behaviour on nav bar\n"
                "• [ ] VoiceOver / TalkBack pass\n"
                "• [ ] Staging regression suite green\n\n"
                "Reply to add anything missing.",
    },
    {
        "ch": "product", "persona": "tim",
        "thread": "qa-checklist",
        "text": "Add: `• [ ] Gesture-based nav fallback on Android 13 (no swipe-back support)` — "
                "came up in the design critique thread.",
    },
    {
        "ch": "product", "persona": "eliza",
        "text": "Design handoff for Lofty nav is complete — all states annotated, tokens updated. "
                "Phillip, lmk if you need additional specs for any QA flows.",
    },
    {
        "ch": "product", "persona": "sue",
        "text": "Thursday planning priorities: (1) Lofty nav, (2) onboarding follow-up from last sprint. "
                "Everything else carries over unless explicitly flagged before 9am.",
    },
    # ── Second wave — implementation progress, approaching the 21st ──────────

    # #product — API lands, QA closes out, Sue confirms on track
    {
        "ch": "product", "persona": "rosario",
        "text": "Profile-context API is live on staging. Deep links routing correctly in initial smoke test. "
                "No issues so far.",
    },
    {
        "ch": "product", "persona": "steven",
        "thread": "nova-launch",
        "text": "Confirmed — profile-context is in production as of this morning. "
                "All deep-link routes passing. Nav integration can proceed against live API.",
    },
    {
        "ch": "product", "persona": "phillip",
        "thread": "qa-checklist",
        "text": "iOS 16/17/18 ✓, Android 13/14 ✓. "
                "One minor layout quirk on Android 13 foldable — logged, won't block. "
                "Waiting on gesture spec from Eliza to close the last test case.",
    },
    {
        "ch": "product", "persona": "sue",
        "thread": "nova-launch",
        "text": "Dev-complete as of yesterday, QA nearly wrapped. "
                "Gesture spec is the last open item. We're on track for the 21st.",
    },

    # #design-review — nav pattern finalised, handoff complete
    {
        "ch": "design-review", "persona": "eliza",
        "thread": "nav-critique",
        "text": "3+More is final. All edge cases annotated: empty More tray, single-item More tray, "
                "and the back-nav variants Tim flagged. Gesture fallback spec for Android 13 is in "
                "the Figma comment thread on page 4, Phillip.",
    },
    {
        "ch": "design-review", "persona": "phillip",
        "thread": "nav-critique",
        "text": "Got the gesture spec — Android 13 fallback is now covered in the test suite. "
                "QA checklist is effectively closed.",
    },
    {
        "ch": "design-review", "persona": "sue",
        "text": "Thursday review wrapped. 3+More approved, back-nav spec signed off. "
                "Eliza, can you export final redlines for the dev handoff doc before EOD?",
    },

    # #user-research — round 2 underway, early analytics signal
    {
        "ch": "user-research", "persona": "jane",
        "id": "round2-sessions",
        "text": "Round 2 screener closed — 7 confirmed participants. "
                "Slight overrecruit in case of no-shows. Sessions Tuesday and Wednesday next week.",
    },
    {
        "ch": "user-research", "persona": "steven",
        "text": "Side note from analytics: 12% lift in secondary-nav engagement in the beta build since "
                "we made it more visually prominent. Early signal, but consistent with what Jane's "
                "sessions predicted.",
    },

    # #general — production deploy, handoff package, pre-launch pulse
    {
        "ch": "general", "persona": "rosario",
        "text": "Production deploy for the profile-context API is done. "
                "Monitoring looks clean — error rate flat, p99 latency unchanged.",
    },
    {
        "ch": "general", "persona": "eliza",
        "text": "Final Lofty nav handoff package is in the shared drive: redlines, specs, assets, "
                "and the decision log from the critique thread. Everything you need to QA or implement.",
    },
    {
        "ch": "general", "persona": "phillip",
        "text": "QA suite is green across the board. One Android 13 foldable quirk logged — "
                "won't block launch. Everything else clean.",
    },
    {
        "ch": "general", "persona": "sue",
        "text": "Release candidate branch cuts Friday. "
                "Flag anything that needs to be in this release by EOD Thursday — after that it waits for the next cycle.",
    },

    # #random — coffee machine saga continues, office texture
    {
        "ch": "random", "persona": "tim",
        "text": "Anyone have coffee shop recs near the office? "
                "The espresso machine situation has entered a new chapter.",
    },
    {
        "ch": "random", "persona": "rosario",
        "thread": "rand-coffee",
        "text": "Heard the facilities ticket finally got escalated. ETA Thursday apparently. "
                "Only took three weeks and a threat of interpretive dance.",
    },
    {
        "ch": "random", "persona": "eliza",
        "thread": "rand-coffee",
        "text": "At this point I've become a French press evangelist. "
                "The machine situation has radicalized me.",
    },

    # ── Tim standalone — ZERO replies, MOST RECENT in #product ───────────────
    {
        "ch": "product", "persona": "tim",
        # No id field intentionally — zero replies required
        "text": "Anyone have the latest user-flow doc for the Lofty nav redesign? Not seeing it in the drive.",
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def resolve_hazel_mention(client: WebClient) -> str:
    user_token = os.environ.get("SLACK_USER_TOKEN", "")
    if not user_token:
        return "@Hazel"
    try:
        wc = WebClient(token=user_token)
        result = wc.auth_test()
        uid = result.get("user_id") or result.get("user")
        if uid:
            return f"<@{uid}>"
    except Exception:
        pass
    return "@Hazel"


def resolve_channels(client: WebClient, names: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    cursor = None
    while True:
        resp = client.conversations_list(
            limit=200,
            types="public_channel,private_channel",
            team_id=os.environ["SLACK_TEAM_ID"],
            **({"cursor": cursor} if cursor else {}),
        )
        for ch in resp["channels"]:
            if ch["name"] in names:
                found[ch["name"]] = ch["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor or len(found) == len(names):
            break

    missing = [n for n in names if n not in found]
    if missing:
        print(f"✗ Channel(s) not found: {', '.join('#' + n for n in missing)}", file=sys.stderr)
        sys.exit(1)

    # Join every channel (idempotent; private channels silently skip)
    for name, cid in found.items():
        try:
            client.conversations_join(channel=cid)
        except SlackApiError:
            pass

    return found


def post_one(client: WebClient, cast: dict, channel_id: str, persona_key: str,
             text: str, thread_ts: str | None = None) -> dict:
    persona = cast[persona_key]
    kwargs = dict(
        channel=channel_id,
        text=text,
        username=persona["username"],
        icon_url=persona["icon_url"],
    )
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    return client.chat_postMessage(**kwargs)


def verify_customize(client: WebClient, cast: dict, test_channel_id: str) -> bool:
    """Post one preflight message and confirm username + icon_url are applied."""
    test_persona = list(cast.values())[0]   # use first persona as the test
    name = test_persona["username"]
    icon = test_persona["icon_url"]
    print(f"  → Preflight: posting as '{name}' with avatar …")
    try:
        resp = client.chat_postMessage(
            channel=test_channel_id,
            text=f"🔧 Preflight test — verifying '{name}' renders with photo. Safe to delete.",
            username=name,
            icon_url=icon,
        )
    except SlackApiError as e:
        print(f"✗ Preflight post failed: {e.response['error']}", file=sys.stderr)
        return False

    applied = resp.get("message", {}).get("username", "")
    if applied != name:
        print(f"✗ Username override not applied (got '{applied}'). "
              "Check chat:write.customize scope.", file=sys.stderr)
        return False

    print(f"  ✓ Preflight OK — '{name}' posted (ts={resp['ts']})")
    print(f"  ✓ Check #random now to confirm the photo renders before continuing.")
    return True


def load_state() -> list[dict]:
    try:
        return json.loads(STATE_FILE.read_text())
    except FileNotFoundError:
        return []


def save_state(records: list[dict]) -> None:
    STATE_FILE.write_text(json.dumps(records, indent=2))


def sweep_channels(client: WebClient, channels: dict[str, str]) -> None:
    """Delete any bot posts in channels that weren't in the state file."""
    try:
        bot_id = client.auth_test().get("bot_id", "")
    except SlackApiError:
        print("⚠️  Could not resolve bot_id — skipping channel sweep.", file=sys.stderr)
        return

    if not bot_id:
        print("⚠️  bot_id empty — skipping channel sweep.", file=sys.stderr)
        return

    swept = 0
    for ch_name, ch_id in sorted(channels.items()):
        cursor = None
        while True:
            try:
                kwargs: dict = {"channel": ch_id, "limit": 200}
                if cursor:
                    kwargs["cursor"] = cursor
                resp = client.conversations_history(**kwargs)
            except SlackApiError as e:
                print(f"  ⚠️  history #{ch_name}: {e.response['error']}", file=sys.stderr)
                break

            for msg in resp.get("messages", []):
                if msg.get("bot_id") == bot_id and msg.get("subtype") != "bot_message":
                    pass  # normal bot posts have no subtype
                if msg.get("bot_id") == bot_id:
                    try:
                        client.chat_delete(channel=ch_id, ts=msg["ts"])
                        print(f"  ✓ swept #{ch_name} ts={msg['ts']}")
                        swept += 1
                        time.sleep(0.3)
                    except SlackApiError as e:
                        code = e.response.get("error", "")
                        if code not in ("message_not_found", "cant_delete_message"):
                            print(f"  ✗ #{ch_name} ts={msg['ts']}: {code}", file=sys.stderr)

            if not resp.get("has_more"):
                break
            cursor = resp.get("response_metadata", {}).get("next_cursor")

    print(f"  Swept {swept} additional bot post(s).")


def clean(client: WebClient, channels: dict[str, str]) -> None:
    # Step 1 — state file
    records = load_state()
    if records:
        print(f"Phase 1a — deleting {len(records)} state-tracked messages …")
        deleted = skipped = failed = 0
        for rec in records:
            try:
                client.chat_delete(channel=rec["channel"], ts=rec["ts"])
                deleted += 1
            except SlackApiError as e:
                code = e.response.get("error", "")
                if code in ("message_not_found", "cant_delete_message"):
                    skipped += 1
                else:
                    print(f"  ✗ ts={rec['ts']}: {code}", file=sys.stderr)
                    failed += 1
            time.sleep(0.3)
        STATE_FILE.unlink(missing_ok=True)
        print(f"  Deleted {deleted}, skipped {skipped}, failed {failed}.")
    else:
        print("Phase 1a — state file empty, nothing to delete.")

    # Step 2 — channel sweep for any remaining bot posts
    print("Phase 1b — sweeping channels for remaining bot posts …")
    sweep_channels(client, channels)


def seed(client: WebClient, cast: dict, channels: dict[str, str], hazel: str) -> None:
    thread_map: dict[str, str] = {}
    records: list[dict] = load_state()
    counts: dict[str, int] = {ch: 0 for ch in channels}
    posted = 0

    for entry in MESSAGES:
        ch_name   = entry["ch"]
        channel_id = channels[ch_name]
        persona   = entry["persona"]
        text      = entry["text"].replace("{hazel}", hazel)
        msg_id    = entry.get("id")
        thread_key = entry.get("thread")
        thread_ts = thread_map.get(thread_key) if thread_key else None

        time.sleep(random.uniform(2, 5))

        try:
            resp = post_one(client, cast, channel_id, persona, text, thread_ts)
        except SlackApiError as e:
            print(f"  ✗ [{cast[persona]['username']} → #{ch_name}] {e.response['error']}", file=sys.stderr)
            continue

        ts = resp["ts"]
        posted += 1
        counts[ch_name] += 1
        if msg_id:
            thread_map[msg_id] = ts

        records.append({"channel": channel_id, "ts": ts})
        save_state(records)

        label = f"(↳ {thread_key})" if thread_key else ""
        print(f"  ✓ [{cast[persona]['username']:18s} → #{ch_name}] {label}")

    print(f"\nDone — posted {posted}/{len(MESSAGES)} messages.")
    print("\nPer-channel counts:")
    for ch, n in sorted(counts.items()):
        print(f"  #{ch}: {n}")
    print(f"\nState saved to {STATE_FILE}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true",
                        help="Full clean: delete state-tracked + sweep remaining bot posts.")
    args = parser.parse_args()

    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

    # Resolve channels upfront (needed for both clean and seed)
    channel_names = list({m["ch"] for m in MESSAGES})
    print(f"Resolving channels: {', '.join('#' + n for n in sorted(channel_names))} …")
    channels = resolve_channels(client, channel_names)
    for name, cid in sorted(channels.items()):
        print(f"  #{name} → {cid}")

    if args.clean:
        clean(client, channels)
        return

    # Resolve Hazel's mention
    hazel = resolve_hazel_mention(client)
    print(f"\nHazel mention: {hazel}")

    # Preflight — find #random and verify name + icon render
    random_id = channels.get("random")
    if not random_id:
        try:
            resp = client.conversations_list(limit=200, types="public_channel",
                                             team_id=os.environ["SLACK_TEAM_ID"])
            for ch in resp["channels"]:
                if ch["name"] == "random":
                    random_id = ch["id"]
                    break
        except SlackApiError:
            pass

    if random_id:
        print(f"\nPreflight → #random ({random_id}) …")
        if not verify_customize(client, CAST, random_id):
            print("\nAborting — fix scope issue before seeding.", file=sys.stderr)
            sys.exit(1)
    else:
        print("⚠️  #random not found — skipping preflight.", file=sys.stderr)

    print(f"\nSeeding {len(MESSAGES)} messages across {len(channels)} channels (2–5s delays) …\n")
    seed(client, CAST, channels, hazel)


if __name__ == "__main__":
    main()
