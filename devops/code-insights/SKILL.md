---
name: code-insights
description: GitLab 代码提交采集与分析 —— clone 到本地后用 git 命令提取 patch，按天存储，支持 daily/weekly/monthly 汇总
---

# code-insights

GitLab 代码提交采集工具。clone 项目到本地，用 git 命令提取 commit patch，按天存储原始数据。

## 目录结构

```
~/.hermes/code-insights/
└── commits/
    └── {date}/                    # 例：2026-04-30
        └── {group}/{project}/    # 例：hypermotion/nezha
            ├── commits.json       # commit 元数据列表
            └── {commit_id}.patch # 每个 commit 的完整 diff
```

## 采集流程

1. OAuth token 获取（密码模式）
2. 获取 hypermotion 组下所有项目（分页）
3. 对每个项目，调用 commits API 获取当日 commits（`/projects/{id}/repository/commits?all=true&since=&until=`）
4. 过滤无效 commit（gitlab/bot/system 用户、Merge 分支）
5. Shallow clone 项目到本地临时目录（嵌入认证信息到 URL）
6. 用 `git show` 逐个保存 patch 文件
7. 保存 commit 元数据到 commits.json
8. 删除临时 clone 目录

## 使用方式

```bash
# 采集指定日期
python3 ~/.hermes/skills/devops/code-insights/scripts/collector.py 2026-04-30

# 采集今日
python3 ~/.hermes/skills/devops/code-insights/scripts/collector.py today
```

## 输出

- `commits/{date}/{group}/{project}/commits.json` — commit 元数据
- `commits/{date}/{group}/{project}/{commit_id}.patch` — 每个 commit 的完整 diff

## 核心设计

### GitLab 认证

使用 `oauth/token`（密码模式）：
```
POST http://192.168.10.254:20080/oauth/token
{"grant_type": "password", "username": "devops", "password": "devops@HyperMotion"}
```

### 项目列表获取

通过 `GET /groups/36/projects?page=N` 分页获取 hypermotion 组下所有项目。

### Commits API

```
GET /projects/{id}/repository/commits?all=true&since={after}&until={date}%2023:59:59
```
- `all=true`：包含所有分支的 commits
- `since/until`：日期范围筛选
- 分页获取所有结果

### Clone URL 重写

项目原始 URL 为 `http://office.oneprocloud.com:20080/{path}.git`（内网不可达），需要重写为 `http://192.168.10.254:20080/{path}.git`，并嵌入认证信息。

### Shallow Clone

- `--depth=100` 限制历史，节省带宽
- clone 到 `/tmp/code-insights-{date}-{project}/`

### Git 命令

```bash
# 获取单个 commit 的 patch（完整 diff，不过滤文件）
git show {commit_id} --format= --patch > {commit_id}.patch
```

### 过滤规则

跳过：
- author 为 `gitlab/bot/system/空` 的自动化提交
- message 以 `Merge branch` 开头的 merge commit

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GITLAB_URL` | `http://192.168.10.254:20080` | GitLab 地址 |
| `GITLAB_USER` | `devops` | 用户名 |
| `GITLAB_PASS` | `devops@HyperMotion` | 密码 |
| `GITLAB_GROUP_ID` | `36` | hypermotion 组 ID |

## 依赖

- `git`：系统命令
