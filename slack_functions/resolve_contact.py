import difflib
import os

from slack_sdk import WebClient


def _score(query: str, *names: str) -> float:
    q = query.lower()
    best = 0.0
    for name in names:
        if not name:
            continue
        n = name.lower()
        if q in n or n in q:
            best = max(best, 0.9)
        ratio = difflib.SequenceMatcher(None, q, n).ratio()
        best = max(best, ratio)
    return best


def resolve_contact(client: WebClient, query: str) -> dict:
    """Fuzzy-match query against users and channels.

    Returns {"match": {...}} when there's one clear winner, or
    {"candidates": [...]} when multiple plausible matches exist.
    Each entry has: type, id, name, score.
    """
    candidates: list[dict] = []

    # --- users ---
    cursor = None
    while True:
        resp = client.users_list(limit=200, team_id=os.environ["SLACK_TEAM_ID"], **({} if cursor is None else {"cursor": cursor}))
        for member in resp["members"]:
            if member.get("deleted") or member.get("is_bot") or member.get("id") == "USLACKBOT":
                continue
            profile = member.get("profile", {})
            score = _score(
                query,
                member.get("name", ""),
                profile.get("real_name", ""),
                profile.get("display_name", ""),
                profile.get("email", ""),
            )
            if score >= 0.55:
                candidates.append({
                    "type": "user",
                    "id": member["id"],
                    "name": profile.get("real_name") or member["name"],
                    "display_name": profile.get("display_name", ""),
                    "avatar_url": profile.get("image_192") or profile.get("image_72", ""),
                    "score": score,
                })
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    # --- channels ---
    cursor = None
    while True:
        resp = client.conversations_list(
            limit=200,
            types="public_channel,private_channel",
            team_id=os.environ["SLACK_TEAM_ID"],
            **({} if cursor is None else {"cursor": cursor}),
        )
        for ch in resp["channels"]:
            ch_name = ch.get("name", "")
            score = _score(query, ch_name)
            if score >= 0.55:
                candidates.append({
                    "type": "channel",
                    "id": ch["id"],
                    "name": ch_name,
                    "score": score,
                })
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    if not candidates:
        return {"match": None, "candidates": []}

    candidates.sort(key=lambda x: x["score"], reverse=True)
    top_score = candidates[0]["score"]
    top = [c for c in candidates if c["score"] >= top_score - 0.05]

    if len(top) == 1:
        return {"match": top[0], "candidates": []}
    return {"match": None, "candidates": top[:5]}
