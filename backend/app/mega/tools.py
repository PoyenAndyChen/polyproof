"""OpenAI function-calling tool definitions for the mega agent."""

MEGA_AGENT_TOOLS: list[dict] = [
    {
        "type": "function",
        "name": "verify_lean",
        "description": (
            "Test Lean code privately. Nothing stored. Sorry IS allowed "
            "(for exploration). Use to check tactic ideas before submitting a fill."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sorry_id": {
                    "type": "string",
                    "description": (
                        "UUID of the sorry to test against. Wraps tactics with the sorry's context."
                    ),
                },
                "tactics": {
                    "type": "string",
                    "description": "Lean tactic code to test.",
                },
            },
            "required": ["sorry_id", "tactics"],
        },
    },
    {
        "type": "function",
        "name": "verify_freeform",
        "description": (
            "Test arbitrary Lean code in the project context. "
            "Use for exploration (#check, #print, exact?, etc)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID of the project.",
                },
                "code": {
                    "type": "string",
                    "description": "Lean code to compile.",
                },
            },
            "required": ["project_id", "code"],
        },
    },
    {
        "type": "function",
        "name": "fill_sorry",
        "description": (
            "Submit a fill for a sorry. This goes through the async job queue. "
            "Complete fills (no sorry's) are auto-committed. "
            "Fills with new sorry's create a decomposition."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sorry_id": {
                    "type": "string",
                    "description": "UUID of the sorry to fill.",
                },
                "tactics": {
                    "type": "string",
                    "description": "Lean tactic code.",
                },
                "description": {
                    "type": "string",
                    "description": "1-3 sentence description of the proof approach.",
                },
            },
            "required": ["sorry_id", "tactics", "description"],
        },
    },
    {
        "type": "function",
        "name": "set_priority",
        "description": "Set the priority of a sorry (critical, high, normal, low).",
        "parameters": {
            "type": "object",
            "properties": {
                "sorry_id": {
                    "type": "string",
                    "description": "UUID of the sorry.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "normal", "low"],
                },
            },
            "required": ["sorry_id", "priority"],
        },
    },
    {
        "type": "function",
        "name": "post_comment",
        "description": (
            "Post a comment on a sorry or the project. Use is_summary=true for synthesis summaries."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "string",
                    "description": "UUID of the sorry or project.",
                },
                "body": {
                    "type": "string",
                    "description": "Comment body (markdown).",
                },
                "is_summary": {
                    "type": "boolean",
                    "description": "True for synthesis summaries.",
                },
                "is_project_comment": {
                    "type": "boolean",
                    "description": "True if commenting on the project, false for sorry.",
                },
            },
            "required": ["target_id", "body"],
        },
    },
    # Built-in OpenAI tools
    {"type": "web_search_preview"},
    # Custom function: fetch a URL's content
    {
        "type": "function",
        "name": "fetch_url",
        "description": (
            "Fetch content from a URL. Useful for reading source files, documentation, papers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch.",
                },
            },
            "required": ["url"],
        },
    },
]

# code_interpreter is enabled as a separate tool type on the API call,
# not as part of the tools list. It is added in runner.py.
