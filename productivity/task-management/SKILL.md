---
name: task-management
description: 文件-based 任务管理系统 — 每个任务独立 markdown 文件，状态机流转 (TODO→IN_PROGRESS→DONE/STALE)
category: productivity
---

# Task Management System

## Overview

A file-based task management workflow for tracking long-running tasks across sessions. Each task is a standalone markdown file with state machine transitions.

## Directory Structure

```
~/.hermes/tasks/
├── INDEX.md                    # All tasks overview
├── TASK-YYYY-MMDD-NNN.md      # Individual task files
└── _archive/                   # Completed/stale tasks (optional)
```

## Task File Format

```markdown
# TASK-2026-0419-001

## 基本信息
- **状态**: TODO | IN_PROGRESS | DONE | STALE
- **创建时间**: YYYY-MM-DD HH:MM
- **开始时间**: YYYY-MM-DD HH:MM  (when moved to IN_PROGRESS)
- **最后更新**: YYYY-MM-DD HH:MM
- **来源**: WeChat | Email | JIRA | ...
- **负责人**: ray | hermes

## 任务描述
[Original task description]

## 流转记录
- YYYY-MM-DD HH:MM → TODO（任务下发）
- YYYY-MM-DD HH:MM → IN_PROGRESS（开始执行）
- [如有] YYYY-MM-DD HH:MM → STALE（超时未完成）
- [如有] YYYY-MM-DD HH:MM → DONE（完成）

## 执行笔记
[Key findings, decisions, blockers, conclusions]
```

## INDEX.md Format

```markdown
# 任务总览

更新于: YYYY-MM-DD HH:MM

## 统计
- TODO: N
- IN_PROGRESS: N
- STALE: N
- DONE: N

## 任务列表

| ID | 状态 | 描述 | 最后更新 | 负责人 |
|----|------|------|----------|--------|
| TASK-2026-0419-001 | 🔄 IN_PROGRESS | ... | 10:15 | hermes |
```

## State Transitions

```
TODO ──→ IN_PROGRESS ──→ DONE
              ↓
           STALE (4h timeout without update)
```

## Workflow

### 1. Create New Task
1. Generate task ID: `TASK-{YEAR}-{MMDD}-{NNN}` (find highest NNN for today, +1)
2. Create `~/.hermes/tasks/TASK-{ID}.md` with TODO status
3. Update `~/.hermes/tasks/INDEX.md` — add row to task list
4. Log transition in 流转记录

### 2. Start Task (TODO → IN_PROGRESS)
1. Update task file: status → IN_PROGRESS, set 开始时间, update 最后更新
2. Add transition log entry
3. Update INDEX.md status column

### 3. Complete Task (IN_PROGRESS → DONE)
1. Update task file: status → DONE, update 最后更新
2. Fill in 执行笔记 with conclusions
3. Add transition log entry
4. Update INDEX.md

### 4. Mark Stale
If IN_PROGRESS task has no update for 4 hours:
1. Update status → STALE
2. Add transition log entry
3. Update INDEX.md
4. Notify user of stale task

## Trigger Conditions

**Auto-create task when:**
- User assigns a task that will take multiple steps
- Task requires research, delegation, or >2 tool calls
- User explicitly says "记得用任务管理"

## Stale Detection

Run via cron job every hour. Check all IN_PROGRESS tasks, if `最后更新` > 4 hours ago → mark STALE.

## Conventions

- Task IDs are sequential per day (001, 002, ...)
- All timestamps in CST (GMT+8)
- Use emoji in INDEX: 🔍 TODO | 🔄 IN_PROGRESS | ⏰ STALE | ✅ DONE
- Every state change updates `最后更新` immediately
- 执行笔记 should contain: what was tried, what worked, key decisions, open questions
