def build_app_home_view(pref: str | None = None) -> dict:
    """Build the App Home Block Kit view — memory-only, no action buttons."""
    return {
        "type": "home",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🧠 What I remember about you"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": pref if pref else "Nothing yet — I'll ask after our next huddle.",
                },
            },
        ],
    }
