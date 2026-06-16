import json

system_prompt = """You are a Principal DevOps and Release Engineer AI Agent.
You interact with users via Telegram to diagnose CI/CD failures and deploy applications.

# Available Tools
| Tool Name | Description |
|---|---|
| github_get_failed_runs | Lists recent failed GitHub Action runs |
| github_get_run_logs | Fetches the logs for a specific failed run ID |
| github_trigger_rebuild | Triggers a rebuild of a GitHub Action run |
| argocd_app_status | Gets the current status of an ArgoCD application |
| argocd_sync_app | Syncs/deploys an ArgoCD application |
| argocd_app_history | Fetches deployment history of an ArgoCD app |

**CRITICAL SAFETY RULE:**
For any WRITE operation (specifically `github_trigger_rebuild` and `argocd_sync_app`), you MUST explain the exact impact of the action to the user and ask for their explicit confirmation before executing the tool. Do NOT execute these tools without the user saying "Yes" or "Proceed".
"""

js_code = """
// Telegram MarkdownV2 Sanitizer and Truncator
let text = $input.item.json.output || "";

// Split text if it's too long for Telegram (limit is ~4096, keeping safe at 3900)
if (text.length > 3900) {
    text = text.substring(0, 3900) + "\\n...[TRUNCATED]";
}

// Escape rogue markdown characters that could crash Telegram MarkdownV2
// Telegram MarkdownV2 requires escaping: _ * [ ] ( ) ~ ` > # + - = | { } . !
// But since we want to keep some markdown, we might just use basic escaping or switch to HTML/Markdown.
// If the agent outputs complex markdown, Telegram might reject it.
// We will escape unclosed or erratic entities if needed, or simply let n8n handle it if we use standard Markdown mode.
// For safety, we escape `<` and `>` which often break things if not in code blocks.
text = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");

return { json: { text: text } };
"""

nodes = [
    {
        "parameters": {},
        "id": "telegram-trigger",
        "name": "Telegram Trigger",
        "type": "n8n-nodes-base.telegramTrigger",
        "typeVersion": 1.1,
        "position": [0, 200]
    },
    {
        "parameters": {
            "options": {
                "systemMessage": system_prompt
            }
        },
        "id": "ai-agent",
        "name": "AI Agent",
        "type": "@n8n/n8n-nodes-langchain.agent",
        "typeVersion": 1.6,
        "position": [250, 200]
    },
    {
        "parameters": {
            "jsCode": js_code
        },
        "id": "code-sanitizer",
        "name": "Markdown Sanitizer",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [550, 200]
    },
    {
        "parameters": {
            "chatId": "={{ $json.message.chat.id }}",
            "text": "={{ $json.text }}",
            "parseMode": "Markdown"
        },
        "id": "telegram-reply",
        "name": "Telegram Reply",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.1,
        "position": [750, 200]
    },
    {
        "parameters": {
            "modelName": "models/chat-bison",
            "options": {
                "baseURL": "https://openrouter.ai/api",
            }
        },
        "id": "llm",
        "name": "OpenRouter LLM",
        "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
        "typeVersion": 1,
        "position": [250, 400]
    },
    {
        "parameters": {
            "windowSize": 10
        },
        "id": "memory",
        "name": "Window Buffer Memory",
        "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
        "typeVersion": 1.2,
        "position": [350, 450]
    }
]

tools = [
    ("github_get_failed_runs", "Lists failed runs"),
    ("github_get_run_logs", "Gets logs. Needs run_id"),
    ("github_trigger_rebuild", "Rebuilds run. Needs run_id"),
    ("argocd_app_status", "Gets app status. Needs app_name"),
    ("argocd_sync_app", "Syncs app. Needs app_name"),
    ("argocd_app_history", "Gets app history. Needs app_name")
]

x_offset = 50
for idx, (tname, tdesc) in enumerate(tools):
    tool_node = {
        "parameters": {
            "workflowId": {"__rl": True, "value": "", "mode": "id"},
            "name": tname,
            "description": tdesc,
            "workflowInputs": {
                "mappingMode": "defineBelow",
                "value": {
                    "run_id": "={{ $fromAI('run_id') }}",
                    "app_name": "={{ $fromAI('app_name') }}"
                }
            }
        },
        "id": f"tool-{tname}",
        "name": f"Tool: {tname}",
        "type": "@n8n/n8n-nodes-langchain.toolWorkflow",
        "typeVersion": 1.2,
        "position": [500 + x_offset, 450]
    }
    x_offset += 150
    nodes.append(tool_node)

connections = {
    "Telegram Trigger": {
        "main": [
            [{"node": "AI Agent", "type": "main", "index": 0}]
        ]
    },
    "AI Agent": {
        "main": [
            [{"node": "Markdown Sanitizer", "type": "main", "index": 0}]
        ]
    },
    "Markdown Sanitizer": {
        "main": [
            [{"node": "Telegram Reply", "type": "main", "index": 0}]
        ]
    },
    "OpenRouter LLM": {
        "ai_languageModel": [
            [{"node": "AI Agent", "type": "ai_languageModel", "index": 0}]
        ]
    },
    "Window Buffer Memory": {
        "ai_memory": [
            [{"node": "AI Agent", "type": "ai_memory", "index": 0}]
        ]
    }
}

for tname, _ in tools:
    if "ai_tool" not in connections:
        connections[f"Tool: {tname}"] = {"ai_tool": [[{"node": "AI Agent", "type": "ai_tool", "index": 0}]]}
    else:
        connections[f"Tool: {tname}"] = {"ai_tool": [[{"node": "AI Agent", "type": "ai_tool", "index": 0}]]}

workflow = {
    "name": "CI/CD Agent Main Workflow",
    "nodes": nodes,
    "connections": connections,
    "settings": {}
}

with open("/Users/anshulbisht/AI-CICD-Agent-Teamate/workflows/agent-workflow.json", "w") as f:
    json.dump(workflow, f, indent=2)

print("Generated agent-workflow.json")
