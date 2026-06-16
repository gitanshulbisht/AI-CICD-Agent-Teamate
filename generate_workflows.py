import json

tools = [
    {
        "name": "github_get_failed_runs",
        "command": "gh run list --status failure --limit 10 --json name,headBranch,status,conclusion,databaseId"
    },
    {
        "name": "github_get_run_logs",
        "command": "gh run view {{{{ $json.run_id || '' }}}} --log-failed | tail -n 200"
    },
    {
        "name": "github_trigger_rebuild",
        "command": "gh run rerun {{{{ $json.run_id || '' }}}}"
    },
    {
        "name": "argocd_app_status",
        "command": "argocd app get {{{{ $json.app_name || '' }}}} --output json"
    },
    {
        "name": "argocd_sync_app",
        "command": "argocd app sync {{{{ $json.app_name || '' }}}}"
    },
    {
        "name": "argocd_app_history",
        "command": "argocd app history {{{{ $json.app_name || '' }}}}"
    }
]

for t in tools:
    workflow = {
        "name": t["name"],
        "nodes": [
            {
                "parameters": {},
                "id": "trigger",
                "name": "Execute Workflow Trigger",
                "type": "n8n-nodes-base.executeWorkflowTrigger",
                "typeVersion": 1,
                "position": [0, 0]
            },
            {
                "parameters": {
                    "command": t["command"]
                },
                "id": "execute",
                "name": "Execute Command",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [220, 0]
            },
            {
                "parameters": {
                    "keepOnlySet": True,
                    "values": {
                        "string": [
                            {
                                "name": "result",
                                "value": "={{ $json.stdout || $json.stderr }}"
                            }
                        ]
                    },
                    "options": {}
                },
                "id": "set",
                "name": "Set Output",
                "type": "n8n-nodes-base.set",
                "typeVersion": 3.4,
                "position": [440, 0]
            }
        ],
        "connections": {
            "Execute Workflow Trigger": {
                "main": [
                    [
                        {
                            "node": "Execute Command",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            },
            "Execute Command": {
                "main": [
                    [
                        {
                            "node": "Set Output",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            }
        },
        "settings": {}
    }
    with open(f"/Users/anshulbisht/AI-CICD-Agent-Teamate/workflows/tools/{t['name']}.json", "w") as f:
        json.dump(workflow, f, indent=2)

print("Generated all 6 sub-workflow JSONs")
