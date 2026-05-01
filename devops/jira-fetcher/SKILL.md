---
name: jira-fetcher
description: JIRA issue 数据采集 — 按日期抓取新建/更新 issue，下载附件/图片，写入 raw JSON + attachments/，重建 daily / weekly / monthly 视图 symlinks
---

# jira-fetcher

JIRA issue 采集。数据存储在 `~/.hermes/dev-insights/`。

## 目录结构

```
~/.hermes/dev-insights/
├── raw/{KEY}.json                    # JIRA issue 数据（扁平 JSON）
├── attachments/{KEY}/{filename}      # 附件原文件 + 评论图片（本地存储）
├── daily/{date}/
│   ├── new/{KEY}.json               # symlink → raw/
│   ├── updated/{KEY}.json            # symlink → raw/
│   └── parsed/                       # jira-summarize.py 建立
├── weekly/week={YYYY-Www}/
│   ├── new/{KEY}.json               # symlink → raw/
│   └── updated/{KEY}.json           # symlink → raw/
└── monthly/{YYYY-MM}/
    ├── new/{KEY}.json               # symlink → raw/
    └── updated/{KEY}.json           # symlink → raw/
```

## 采集脚本

```bash
# 采集并重建所有视图（区分 new/updated）
python3 ~/.hermes/skills/devops/jira-fetcher/scripts/jira-fetch.py

# 指定日期
python3 ~/.hermes/skills/devops/jira-fetcher/scripts/jira-fetch.py 2026-04-23

# 仅重建视图（symlink 损坏时用）
python3 ~/.hermes/skills/devops/jira-fetcher/scripts/jira-fetch.py --rebuild
```

**幂等**：raw JSON 每次请求完整覆盖（反映最新状态）。视图 symlink 损坏时用 `--rebuild` 重建。

**JSON 字段：** key / type / status / priority / summary / description / assignee / reporter / created / updated / labels / parent_key / components / fixVersions / comments（含 author/body/images/local_path/created）/ attachments（含 filename/url/local/created）

## 稳定性保障

- **JIRA API 重试**：jira_search / jira_get_comments / jira_get_attachments 均带 `@retry` 装饰器，3 次重试，指数退避 2s→4s→8s
- **附件下载重试**：download_file 带 `@retry`，3 次重试，指数退避 2s→4s→8s
- **单 issue 失败隔离**：主循环有 try/except，单个 issue 失败不影响其他
- **symlink 原子重建**：`_ensure_symlink` 先删再建，不会出现悬空链接
- **raw JSON 完整写入**：json.dump 一次性写入，无部分写入风险
- **附件跳过已存在文件**：重复采集不会重复下载

## 已知注意

1. **`__pycache__` 旧字节码**：修改源码后必须清缓存：
   ```bash
   rm -rf ~/.hermes/skills/devops/jira-fetcher/scripts/__pycache__
   ```

## 依赖

- Python `atlassian` 库
- 环境变量：`JIRA_URL`, `JIRA_USERNAME`, `JIRA_PASSWORD`
- JIRA 地址：`http://office.oneprocloud.com.cn:9005`，用户 `sunqi`

## 与 jira-issue-summary 的关系

```
jira-fetcher（采集）→ raw/{KEY}.json + attachments/{KEY}/
jira-issue-summary（LLM分析）→ parsed/{KEY}.summary.md + {KEY}.detailed.md
```

jira-issue-summary 读取 raw/ JSON 和 attachments/ 本地文件进行 LLM 总结，两个 skill 独立。
