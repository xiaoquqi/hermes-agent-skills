---
name: gitlab-fetcher
description: 抓取 GitLab commits 并按 JIRA key 归类，支持与 jira-fetcher 数据合并
---

# gitlab-fetcher

抓取 GitLab 指定日期的 commits，按 JIRA key 关联，过滤无意义的自动化提交。

## 触发条件

需要抓取 GitLab 代码提交时使用。常与 `jira-fetcher` 配合做 JIRA+GitLab 联合分析。

## 输入

- `date`：日期，格式 `YYYY-MM-DD`，默认前一天（工作日）

## 输出

- `~/.hermes/gitlab-cache/gitlab-{DATE}.json`

JSON 结构：
```json
{
  "date": "2026-04-16",
  "by_key": { "REQ-6165": [commit, ...], ... },
  "by_project": { "hypermotion/newmuse": [commit, ...], ... },
  "unlinked": [commit, ...]
}
```

每条 commit：
```json
{
  "sha": "a1b2c3d4",
  "author": "zhangtianjie9761",
  "author_jira": "张天洁",
  "message": "Add metadata merge for snapshot chains",
  "project": "hypermotion/ant",
  "jira_keys": ["REQ-6118"],
  "additions": 200,
  "deletions": 50,
  "date": "2026-04-16"
}
```

## 使用方式

```bash
# 单独抓取
python3 ~/.hermes/skills/devops/gitlab-fetcher/scripts/gitlab_fetcher.py 2026-04-16

# 查看可读汇总
python3 ~/.hermes/skills/devops/gitlab-fetcher/scripts/gitlab_fetcher.py 2026-04-16 --format

# 查看 JSON
python3 ~/.hermes/skills/devops/gitlab-fetcher/scripts/gitlab_fetcher.py 2026-04-16 --json
```

## 核心设计

### GitLab API 认证

使用 `oauth/token` 获取 access token（密码模式）：
```
POST http://192.168.10.254:20080/oauth/token
{"grant_type": "password", "username": "devops", "password": "devops@HyperMotion"}
```

### JIRA key 提取

正则必须带数字，避免分支名误匹配：
```python
JIRA_KEY_RE = re.compile(r'(BUG|REQ|TASK|IMP|STORY|PRO|CLI|DOC|SEC|PE|SUB|PRJ)-(\d+)', re.IGNORECASE)
```

### 过滤规则

跳过的 commit（无功能价值）：
1. author 为 `gitlab/bot/system` 的自动化提交
2. message 以 `Merge branch` 开头的 merge commit

### GitLab → JIRA 用户名映射

内置 `GL_TO_JIRA` 映射表（与 jira-daily-summary 的 TEAM_MEMBER 保持一致）：
```python
GL_TO_JIRA = {
    'zhangjiaqi':       '张佳奇',
    'zhangtianjie9761': '张天洁',
    'wanghuixian':      '王慧仙',
    'liulixiang9312':   '刘立祥',
    'yongmengmeng8311': '雍蒙蒙',
    'lijianhai':        '李建海',
    'guozhonghua':      '郭中华',
}
```

### 与 product-progress 集成

`product_progress.py` 在入口处调用 `load_gitlab()` + `attach_commits()`：
```python
gitlab_data = load_gitlab(GL_FILE)
if gitlab_data:
    issues = attach_commits(issues, gitlab_data)
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GITLAB_URL` | `http://192.168.10.254:20080` | GitLab 地址 |
| `GITLAB_USER` | `devops` | 用户名 |
| `GITLAB_PASS` | `devops@HyperMotion` | 密码 |

## 依赖技能

- `holiday-checker`：工作日计算（用于默认日期）

## 已知坑

- **大量 merge commit 污染 unlinked**：旧版没有过滤 `Merge branch`，导致 unlinked 虚高（36条→实际9条）。已加过滤。
- **REQ/CLI 等前缀无数字时被误匹配**：如分支名 `feature/REQ-xxx` 匹配到 `REQ`（无数字）。正则必须用 `(\d+)` 捕获组确保有数字。
- **hypermotion 组下有 69 个项目**：遍历所有项目较慢，实际有 commit 的只有少数几个（newmuse、nirvana、ant、skills、porter）
- **get_commit_stats 额外 API 调用**：每条 commit 都单独调一次获取 additions/deletions，可以优化为批量或缓存
