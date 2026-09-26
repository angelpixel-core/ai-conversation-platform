---
id: DIRECTORY_STRUCTURE
aliases: []
tags: []
---

```txt
ai-conversation-platform/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── Makefile
├── README.md
├── ROADMAP.md
├── STRUCTURE.md
│
├── docs/
│   ├── architecture.md
│   └── roadmap.md
│
└── .agent/
    ├── rules/
    │   ├── 00-core-philosophy.md
    │   ├── 01-workflows-and-git.md
    │   └── 02-testing-standards.md
    │
    ├── specs/
    │   ├── current/
    │   │   └── slice-01-create-conversation.md
    │   ├── completed/
    │   │   └── .gitkeep
    │   └── backlog/
    │       └── slice-02-send-message-and-streaming.md
    │
    ├── architecture/
    │   ├── decisions/
    │   │   └── 0001-use-outbox-pattern.md
    │   └── system-map.mermaid.md
    │
    └── templates/                          <-- JERARQUÍA POR CAPAS (Clean Architecture)
        ├── domain/
        │   ├── entity.tt.py
        │   └── repository_port.tt.py
        │
        ├── application/
        │   ├── command.tt.py
        │   ├── command_handler.tt.py
        │   ├── query.tt.py
        │   ├── query_handler.tt.py
        │   └── unit_of_work_port.tt.py
        │
        ├── infrastructure/
        │   ├── in_memory_repository_adapter.tt.py
        │   └── in_memory_unit_of_work_adapter.tt.py
        │
        └── interfaces/
            ├── router.tt.py
            └── schema.tt.py
```
