from slack_bolt import App

from .feedback_buttons import handle_feedback_button
from .greeting_buttons import handle_brainstorm, handle_morning_huddle, handle_my_tasks
from .huddle_feedback import (
    handle_feedback_concise,
    handle_feedback_detail,
    handle_feedback_just_right,
)
from .start_voice_call import handle_start_voice_call


def register(app: App):
    app.action("feedback")(handle_feedback_button)
    app.action("start_voice_call")(handle_start_voice_call)
    app.action("morning_huddle")(handle_morning_huddle)
    app.action("my_tasks")(handle_my_tasks)
    app.action("brainstorm")(handle_brainstorm)
    app.action("feedback_just_right")(handle_feedback_just_right)
    app.action("feedback_concise")(handle_feedback_concise)
    app.action("feedback_detail")(handle_feedback_detail)
