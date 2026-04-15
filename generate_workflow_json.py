import json

workflow = {
    "name": "AutoCV Pipeline",
    "nodes": [
        {
            "parameters": {
                "rule": {
                    "interval": [{"field": "minutes", "minutesInterval": 1}]
                }
            },
            "id": "schedule-trigger",
            "name": "Schedule Trigger",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [240, 400]
        },
        {
            "parameters": {
                "jsCode": "const fs = require('fs');\nconst path = require('path');\n\nconst jdDir = 'C:\\\\Users\\\\Acer\\\\Desktop\\\\Code\\\\AutoCV\\\\autocv-script\\\\JDs';\nconst stateFile = path.join(jdDir, '.processed.json');\n\nlet processed = [];\nif (fs.existsSync(stateFile)) {\n  processed = JSON.parse(fs.readFileSync(stateFile, 'utf8'));\n}\n\nconst files = fs.readdirSync(jdDir).filter(f => f.endsWith('.txt'));\nconst newFiles = files.filter(f => !processed.includes(f));\n\nif (newFiles.length === 0) {\n  return { json: { hasNew: false } };\n}\n\nconst item = newFiles[0];\nconst filename = item.replace('.txt', '').replace('jd_', '');\nconst parts = filename.split('_');\nconst company = parts.pop() || 'Unknown';\nconst jobRole = parts.join('_') || 'Unknown';\n\nreturn {\n  json: {\n    hasNew: true,\n    filename: item,\n    jdPath: path.join(jdDir, item),\n    jobRole: jobRole,\n    company: company\n  }\n};"
            },
            "id": "check-new-files",
            "name": "Check New JDs",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [460, 400]
        },
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2
                    },
                    "conditions": [
                        {
                            "id": "cond1",
                            "leftValue": "={{ $json.hasNew }}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "true"}
                        }
                    ],
                    "combinator": "and"
                }
            },
            "id": "filter-new",
            "name": "Has New JD?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [680, 400]
        },
        {
            "parameters": {
                "command": "=cd C:\\\\Users\\\\Acer\\\\Desktop\\\\Code\\\\AutoCV\\\\autocv-script && .\\\\venv\\\\Scripts\\\\python pipeline\\\\graph.py --jd \"{{ $json.jdPath }}\" --job-role \"{{ $json.jobRole }}\" --company \"{{ $json.company }}\""
            },
            "id": "run-pipeline",
            "name": "Run AutoCV Pipeline",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [900, 300]
        },
        {
            "parameters": {
                "jsCode": "const fs = require('fs');\nconst path = require('path');\n\nconst jdDir = 'C:\\\\Users\\\\Acer\\\\Desktop\\\\Code\\\\AutoCV\\\\autocv-script\\\\JDs';\nconst stateFile = path.join(jdDir, '.processed.json');\n\nlet processed = [];\nif (fs.existsSync(stateFile)) {\n  processed = JSON.parse(fs.readFileSync(stateFile, 'utf8'));\n}\n\nconst filename = $input.first().json.filename;\nprocessed.push(filename);\nfs.writeFileSync(stateFile, JSON.stringify(processed, null, 2));\n\nreturn [{ json: { processed: filename, jobRole: $input.first().json.jobRole, company: $input.first().json.company } }];"
            },
            "id": "mark-processed",
            "name": "Mark as Processed",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1120, 300]
        },
        {
            "parameters": {
                "content": "=✅ AutoCV Complete!\n\nJD: {{ $json.jobRole }} at {{ $json.company }}\nFile: {{ $json.filename }}\n\nCheck CVs/ folder for the output PDF and report."
            },
            "id": "notification",
            "name": "Success Notification",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [1340, 300]
        },
        {
            "parameters": {
                "content": "=No new JDs found. Waiting for next check..."
            },
            "id": "no-new",
            "name": "No New JDs",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [900, 500]
        }
    ],
    "connections": {
        "Schedule Trigger": {"main": [[{"node": "Check New JDs", "type": "main", "index": 0}]]},
        "Check New JDs": {"main": [[{"node": "Has New JD?", "type": "main", "index": 0}]]},
        "Has New JD?": {"main": [
            [{"node": "Run AutoCV Pipeline", "type": "main", "index": 0}],
            [{"node": "No New JDs", "type": "main", "index": 0}]
        ]},
        "Run AutoCV Pipeline": {"main": [[{"node": "Mark as Processed", "type": "main", "index": 0}]]},
        "Mark as Processed": {"main": [[{"node": "Success Notification", "type": "main", "index": 0}]]}
    },
    "pinData": {},
    "settings": {
        "executionOrder": "v1",
        "saveManualExecutions": True,
        "callerPolicy": "workflowsFromSameOwner"
    },
    "staticData": None,
    "tags": [],
    "triggerCount": 1,
    "versionId": "1"
}

# Write and validate
with open(r'C:\Users\Acer\Desktop\Code\AutoCV\autocv-script\n8n-workflow.json', 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)

print('JSON written successfully')
print(f'Nodes: {len(workflow["nodes"])}')
for node in workflow['nodes']:
    print(f'  - {node["name"]} ({node["type"]})')

# Validate
with open(r'C:\Users\Acer\Desktop\Code\AutoCV\autocv-script\n8n-workflow.json', 'r', encoding='utf-8') as f:
    loaded = json.load(f)
print(f'\nValidation: OK - {len(loaded["nodes"])} nodes, {len(loaded["connections"])} connections')
