---
name: gws-google-workspace-cli
description: Google Workspace CLI - 管理 Gmail、日历、Drive、Sheets 等 Google 服务
---

# Google Workspace CLI (gws) 使用指南

## 概述
`gws` 是 Google Workspace CLI，用于管理 Gmail、日历、Drive、Sheets、Docs 等 Google 服务。

## 命令位置
- 二进制：`/usr/local/bin/gws`
- 配置目录：`~/.config/gws/`
- 认证信息：`~/.config/gws/credentials.db`（keyring 管理）

## 常用命令

### Gmail
```bash
gws gmail users messages list --params '{"userId": "me", "maxResults": 3}'
gws gmail users messages get --params '{"userId": "me", "id": "..."}'
```

### Calendar
```bash
gws calendar calendarList list --params '{\"maxResults\": 5}'
gws calendar events list --params '{\"calendarId\": \"primary\", \"maxResults\": 10}'
gws calendar +agenda  # 显示近期所有事件
```

#### 创建日历事件（events insert）

**语法（容易搞错）：**
```bash
gws calendar events insert \
  --params '{"calendarId": "xiaoquqi@gmail.com"}' \
  --json '{
    "summary": "会议标题",
    "location": "地点",
    "description": "描述",
    "start": {"dateTime": "2026-04-29T15:00:00+08:00", "timeZone": "Asia/Shanghai"},
    "end": {"dateTime": "2026-04-29T16:00:00+08:00", "timeZone": "Asia/Shanghai"},
    "reminders": {"useDefault": false, "overrides": [{"method": "popup", "minutes": 15}]}
  }'
```

**要点：**
- `calendarId` 必须放 `--params`，不是 `--calendar_id` flag
- 事件完整 body 放 `--json`，两者缺一不可
- 日期格式：`2026-04-29T15:00:00+08:00`（含时区），不用 Z 表示 UTC
- **先用 `--dry-run** 验证**，避免实际触发安全扫描（URL 含非 ASCII 字符如中文/emoji 会触发 `Non-ASCII URL path` 安全扫描，需用户审批）

**查日历 ID：**
```bash
gws calendar calendarList list | python3 -c "import json,sys; d=json.load(sys.stdin); [print(i['id'], i.get('summary','')) for i in d.get('items',[])]"
```

### Drive
```bash
gws drive files list --params '{"pageSize": 10}'
```

### Sheets
```bash
gws sheets spreadsheets get --params '{"spreadsheetId": "..."}'
```

## 故障排查

**找不到命令？**
用户可能以为命令名是 `gms`，但实际是 `gws`。搜索 `~/.config/` 目录：
```bash
ls ~/.config/ | grep -i google
```
如果看到 `gws` 目录，说明就是 `gws` 命令。

**认证失败？**
检查 `~/.config/gws/credentials.db` 是否存在，用 `gws auth login` 重新认证。

## 环境变量
- `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` — 覆盖配置目录
- `GOOGLE_WORKSPACE_CLI_LOG` — 日志级别（如 `gws=debug`）
