// ── Tool definitions sent to the OpenAI Realtime model ──────────────────────
// Add, remove, or edit tools here. Each entry is passed verbatim inside
// session.update → session.tools. The matching server handler lives in
// voice/server.py (TOOLS dict) and slack_functions/.

const TOOLS = [
  {
    type: "function",
    name: "search_workspace",
    description:
      "Search the entire Slack workspace with a natural-language query. Use this for open-ended discovery — 'catch me up', 'what's happening with the campaign?', 'find anything about the Q3 launch' — when the channel isn't known yet. For pulling full history of a channel whose ID you already have, use ramp_up instead.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Natural-language search query" },
      },
      required: ["query"],
    },
  },
  {
    type: "function",
    name: "ramp_up",
    description:
      "Pull recent message history from a Slack channel to catch up on what happened. Use this once you already know the channel ID. For discovering which channel is relevant first, use search_workspace instead.",
    parameters: {
      type: "object",
      properties: {
        channel_id: { type: "string", description: "Slack channel ID, e.g. C1234567890" },
        limit:      { type: "integer", description: "Max messages to fetch (default 50)" },
      },
      required: ["channel_id"],
    },
  },
  {
    type: "function",
    name: "resolve_contact",
    description:
      "Fuzzy-match a name against Slack users and channels. Returns the best match or a list of candidates.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Name, display name, or partial match to search for" },
      },
      required: ["query"],
    },
  },
  {
    type: "function",
    name: "post_message",
    description: "Post a message to a Slack channel or user by ID.",
    parameters: {
      type: "object",
      properties: {
        target: { type: "string", description: "Channel ID (C...) or user ID (U...) to send to" },
        text:   { type: "string", description: "Message text to post" },
      },
      required: ["target", "text"],
    },
  },
  {
    type: "function",
    name: "set_reminder",
    description:
      "Create a Slack reminder. Accepts natural-language time like 'in 10 minutes' or 'tomorrow at noon'.",
    parameters: {
      type: "object",
      properties: {
        text: { type: "string", description: "Reminder message" },
        when: { type: "string", description: "When to trigger (natural language or Unix timestamp)" },
      },
      required: ["text", "when"],
    },
  },
  {
    type: "function",
    name: "create_canvas",
    description:
      "Create a titled Slack canvas attached to a channel. The canvas appears in the channel's Canvas tab with the given title.",
    parameters: {
      type: "object",
      properties: {
        channel_id: { type: "string", description: "Channel ID to attach the canvas to" },
        title:      { type: "string", description: "Canvas title (default: 'Materials for review')" },
        items: {
          type: "array",
          description: "Items to list in the canvas",
          items: {
            type: "object",
            properties: {
              title: { type: "string" },
              link:  { type: "string" },
            },
            required: ["title"],
          },
        },
      },
      required: ["channel_id", "items"],
    },
  },
  {
    type: "function",
    name: "edit_canvas",
    description:
      "Append new items to an existing Slack canvas by its canvas ID. Call list_canvases first if you only have a title, not an ID.",
    parameters: {
      type: "object",
      properties: {
        canvas_id: { type: "string", description: "Canvas ID (starts with F0B...)" },
        items: {
          type: "array",
          description: "Items to append",
          items: {
            type: "object",
            properties: {
              title: { type: "string" },
              link:  { type: "string" },
            },
            required: ["title"],
          },
        },
      },
      required: ["canvas_id", "items"],
    },
  },
  {
    type: "function",
    name: "list_canvases",
    description:
      "List canvases the user can access, optionally filtered to a channel. Returns id, title, permalink, and channels for each canvas.",
    parameters: {
      type: "object",
      properties: {
        channel_id: { type: "string", description: "Channel ID to filter by (optional — omit to search all)" },
      },
      required: [],
    },
  },
  {
    type: "function",
    name: "read_canvas",
    description:
      "Read a canvas by ID — returns its title and permalink. Call list_canvases first if you only have a title.",
    parameters: {
      type: "object",
      properties: {
        canvas_id: { type: "string", description: "Canvas ID (starts with F0B...)" },
      },
      required: ["canvas_id"],
    },
  },
  {
    type: "function",
    name: "save_memory",
    description:
      "Persist something the user wants you to remember for future sessions — a preference, communication style, recurring pattern, or explicit 'next time do X' instruction. Call this immediately when the user expresses such a preference, before responding verbally.",
    parameters: {
      type: "object",
      properties: {
        note: { type: "string", description: "What to remember about the user" },
      },
      required: ["note"],
    },
  },
  {
    type: "function",
    name: "delete_canvas",
    description:
      "Permanently delete a canvas and remove it from all channel tabs. Call list_canvases first if you only have a title. Cannot be undone.",
    parameters: {
      type: "object",
      properties: {
        canvas_id: { type: "string", description: "Canvas ID to delete (starts with F0B...)" },
      },
      required: ["canvas_id"],
    },
  },
];
