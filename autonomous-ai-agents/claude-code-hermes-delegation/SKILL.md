---
name: claude-code-hermes-delegation
description: Correct way to delegate tasks to Claude Code from Hermes Agent — via terminal tool with `-p` print mode. Do NOT use `--acp --stdio` (that's GitHub Copilot CLI, not Claude Code).
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [Coding-Agent, Claude, Hermes, Delegation]
related_skills: [claude-code]
---

# Claude Code Delegation from Hermes (CORRECT approach)

## ⚠️ Critical: Do NOT use `--acp --stdio`

The `delegate_task` tool's `acp_command='claude'` with `['--acp', '--stdio']` is **wrong for Claude Code**. This parameter is for **GitHub Copilot CLI**, not Claude Code.

Claude Code 2.x does NOT support `--acp`. The `--acp` flag only exists in the GitHub Copilot CLI (`copilot --acp`).

## Correct Approach: Terminal Tool with `claude -p`

From Hermes, spawn Claude Code as a **subprocess via the terminal tool**:

```python
# Basic pattern
terminal(
    command=f"claude -p '{goal}' --max-turns 10 --dangerously-skip-permissions",
    workdir="/path/to/project",
    timeout=120
)

# With custom model (e.g., proxy endpoints like Agione/HyperOne)
terminal(
    command=f"claude -p '{goal}' --model minimax/minimax-m2.7/b1d92 --max-turns 10",
    workdir="/path/to/project",
    timeout=120
)

# With structured JSON output
terminal(
    command=f"claude -p '{goal}' --output-format json --json-schema '{schema}' --max-turns 10",
    workdir="/path/to/project",
    timeout=120
)

# Bare mode (fastest startup, requires ANTHROPIC_API_KEY env var)
terminal(
    command=f"claude --bare -p '{goal}' --max-turns 10",
    workdir="/path/to/project",
    timeout=120
)
```

## Why `claude -p` Works

- `-p` / `--print` = print mode = non-interactive one-shot
- Claude Code runs the task, returns result, exits immediately
- No PTY/TUI needed, no dialog handling
- Output can be JSON (via `--output-format json`)
- Exit code indicates success/failure

## Common Use Cases

### One-shot coding task
```python
terminal(
    command="claude -p 'Add input validation to the login function in auth.py' --allowedTools 'Read,Edit,Bash' --max-turns 5",
    workdir="/Users/ray/project",
    timeout=60
)
```

### Multi-file refactoring
```python
terminal(
    command="claude -p 'Refactor the database layer to use connection pooling. Files: src/db/*.py' --dangerously-skip-permissions --max-turns 15",
    workdir="/Users/ray/project",
    timeout=180
)
```

### Code review with JSON output
```python
terminal(
    command="claude -p 'Review auth.py for security issues. Output JSON with fields: issues[], severity, recommendations[]' --output-format json --json-schema '{\"type\":\"object\",\"properties\":{\"issues\":{\"type\":\"array\"}},\"required\":[\"issues\"]}' --max-turns 5",
    workdir="/Users/ray/project",
    timeout=60
)
```

## Key Flags for Hermes Integration

| Flag | Purpose |
|------|---------|
| `-p 'task'` | Non-interactive print mode (required) |
| `--model <alias>` | Override default model |
| `--max-turns N` | Prevent runaway loops (always set) |
| `--dangerously-skip-permissions` | Auto-approve tools (Hermes can't handle dialogs) |
| `--output-format json` | Structured output for parsing |
| `--bare` | Fastest startup, skips MCP/hooks discovery |
| `--allowedTools 'Read,Edit'` | Restrict capabilities |
| `--working-dir` | Override cwd (alternative to workdir param) |

## Claude Code Version Check

```bash
claude --version  # Should be 2.x+
claude --help    # Check available flags (no --acp should exist)
```

## History

- **2026-04-17**: Created — discovered that `--acp --stdio` approach in older docs is wrong; correct approach is `claude -p` via terminal tool
