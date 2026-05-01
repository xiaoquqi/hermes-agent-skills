---
name: jira-daily-summary
description: JIRA 每日团队汇总 - 按人统计工作日 JIRA 更新，LLM 深度分析参与度，支持多模态图片识别
category: productivity
---

# JIRA Daily Team Summary

每天自动读取 JIRA 中当天（或上一个工作日以来）的更新，按人汇总研发和测试同事的工作情况。

## 环境要求

- Python 3.8+（需 `/opt/anaconda3/bin/python`，不要用系统默认 python3）
- `atlassian-python-api` (`/opt/anaconda3/bin/pip install atlassian-python-api`)
- `openai` Python 包（用于 LLM 分析）
- JIRA 凭证写入 `~/.hermes/.env`：
  ```
  JIRA_URL=http://office.oneprocloud.com.cn:9005
  JIRA_USERNAME=sunqi
  JIRA_PASSWORD=sunqi1358
  ```
- JIRA 为公司内网地址（外网可通过 `office.oneprocloud.com.cn:9005` 访问）

## 使用方式

```
/jira-summary        ← 默认取上一个工作日
/jira-summary today  ← 统计今天（不推荐，通常工作时还没结束）
/jira-summary yesterday ← 同默认
/jira-summary 2026-04-15  ← 指定某天
/jira-summary this-week  ← 本周一至今累计
```

## 输出内容

按人输出：
- 参与 issue 数量 + 深度/中层/浅层参与数量
- 工作饱和度评估（高/中/低）
- 每个 issue 的参与证据（来自 LLM 分析）
- 管理视角一句话总结

## 触发条件

- `/jira-summary` slash command
- 定时任务（每工作日下午 5 点自动推送，ID: `f87a00c63e81`）

## 深度判断标准（LLM 分析）

- **深**：主动分析/定位/修复问题、提交代码、写文档、推动验证和解决
- **中**：作为 reporter 推进了问题进展、或有参与实质性讨论/进度跟进
- **浅**：仅被提及/转派、简单回复、Jirabot 自动创建、BOT 发的无实质内容链接

## 技术注意事项（经验总结）

### LLM API 配置

**已在 `~/.hermes/.env` 配置：**
```
LLM_BASE_URL=https://zh.agione.co/hyperone/xapi/api
LLM_API_KEY=ak-29c67e1cf9f3461190ce639ab469a0c1
LLM_MODEL=minimax/minimax-m2.7/b1d92
```

**多模态/vision 模型测试结论（2026-04-16）：**

| 模型 | 多模态 | 备注 |
|------|--------|------|
| `minimax/m2.7` | ❌ | 不支持图片，传图片返回空 |
| `minimax/m2.5` | ❌ | 不支持图片 |
| `z-ai/glm-4.7/57f69` | ✅ | 支持多模态，但慢（30s+） |
| `qwen/qwen-vl-*` | ❌ | endpoint 中不存在 |
| Kimi K2 (moonshotai/moonshot-kimi-k2-instruct) | ❌ | 不支持图片 |

如需快速图片识别，需另备多模态模型 endpoint。

### atlassian-python-api 返回格式（踩坑经验）

**JQL 查询返回的是 dict，不是 list：**
```python
result = jira.jql(jql, limit=100, fields='summary,status,assignee')
# result 是 dict，issues 在 .get('issues', [])
issues = result.get('issues', []) if isinstance(result, dict) else (result or [])
```

**评论获取方法名（容易搞错）：**
```python
# ✅ 正确：issue_get_comments（不是 get_issue_comments）
raw_c = jira.issue_get_comments(issue_key)
comments = raw_c.get('comments', []) if isinstance(raw_c, dict) else []

# ✅ 工时记录
raw_w = jira.get_issue_worklog(issue_key)
worklogs = raw_w.get('worklogs', []) if isinstance(raw_w, dict) else []
```

**附件获取（两个方法配合）：**
```python
att_ids = jira.get_attachments_ids_from_issue(issue_key) or []
attachments = []
for att_id in att_ids[:10]:
    att_meta = jira.get_attachment(att_id)  # 返回 dict
    if att_meta:
        attachments.append(att_meta)
```

**JQL 日期格式（双引号必须）：**
```python
# ✅ 正确
f'updated >= "{start_date}" AND updated <= "{end_date} 23:59"'

# ❌ 错误：没有引号会报 "Expecting either 'OR' or 'AND' but got '23:59'"
f'updated >= {start_date} AND updated <= {end_date}23:59'
```

**Python 环境：** 使用 `/opt/anaconda3/bin/python`，系统默认 python3 没有 atlassian 模块。

### LLM 响应处理（踩坑经验）

**去除思考过程标签：**
Minimax 模型返回内容可能含 `<think>...` 思考标签，需提取最后一个 JSON 对象：
```python
raw = resp.choices[0].message.content.strip()
last_brace = raw.rfind('{')
if last_brace != -1:
    raw = raw[last_brace:]
result = json.loads(raw.strip())
```

**工时判断注意：** 很多 JIRA issue 评论数为 0（只有 reporter 自创建），此时 LLM 会判断为"浅"。这是真实情况，不是 bug。

### .env 加载
- subprocess 运行时需手动从 `~/.hermes/.env` 读取并传入 env，防止父进程没有环境变量

## GitLab 集成（2026-04-16 新增）

### 关键发现：JIRA Key 在 Commit Message 第二行

Commit 消息格式通常如下：
```
第一行：简短描述
第二行（空行后）："Resolved REQ-5972" 或 "See REQ-1234"
```

`msg.split('\n')[0]` 只取第一行 → JIRA key 提取失败。

**修复**：搜索完整消息 + parent_ids 字段：
```python
full_text = msg + ' ' + c.get('ref', '') + ' ' + ' '.join(c.get('parent_ids', []))
found_keys = re.findall(r'(BUG|REQ|TASK|IMP|STORY|PRO|CLI|DOC|SEC|PE|SUB)-(\d+)', full_text, re.IGNORECASE)
```

**正则必须包含 `(\d+)`**，否则只返回 `['REQ']` 而不是 `['REQ-5972']`。

### GitLab API Details
- Base URL: `http://192.168.10.254:20080`
- Auth: OAuth password grant → `POST /oauth/token` with `{"grant_type":"password","username":"devops","password":"devops@HyperMotion"}`
- Search commits: `GET /projects/:id/repository/commits?all=true&since=<date>&until=<date>&per_page=100`
- Commit diff stats: `GET /projects/:id/repository/commits/:sha`
- Author name deduplication: GitLab usernames may vary in case (e.g., `Guozhonghua` vs `guozhonghua`) → normalize to lowercase

### GitLab → JIRA Author Mapping
```python
GL_TO_JIRA = {
    'zhangjiaqi': '张佳奇',
    'zhangtianjie9761': '张天洁',
    '张天洁': '张天洁',
    'wanghuixian': '王慧仙',
    '刘立祥': '刘立祥',
    'liulixiang9312': '刘立祥',
    'yongmengmeng8311': '雍蒙蒙',
    'lijianhai': '李建海',
    'guozhonghua': '郭中华',
}
```

### 评分系统（修订版 2026-04-16）
| 类别 | 分值 | 说明 |
|------|------|------|
| JIRA 完成 | 5/个 | 状态为 Done |
| JIRA 新建 | 3/个 | 当天创建 |
| GitLab 代码 | 5/100行 | 上限15分 |
| 真实评论 | 2/issue | 排除 GitLab bot |

阈值：≥20 高 / ≥8 中 / <8 低

**重要**：GitLab webhook 评论在 JIRA 上 = 正常现象（说明员工正确关联了 commit）。不要过滤掉。

### 测试人员 vs 研发人员（已废弃 — 2026-04-16 确认）

**统一标准，所有人同一评分体系，不区分角色。**

- 无 GitLab 提交 → ⚠️ 无GitLab提交（直接警告，不解释）
- 不再说"测试人员不考核GitLab"，全部按 JIRA Done×5 + JIRA New×3 + GitLab/100×5(上限15) + 评论×2(上限6)

### 代码质量分析工作流（2026-04-16 新增）

当需要评估代码质量时，按以下步骤抽样分析 diff：

**Step 1: 拉取 commit diff**
```python
# 获取某个 commit 的文件改动
diff = api(f'/projects/{pid}/repository/commits/{sha}/diff', token)
# diff 是 list，每个元素包含：new_path, diff(完整内容), stats{additions, deletions}
```

**Step 2: 评估维度**
| 维度 | 良好信号 | 警示信号 |
|------|----------|----------|
| 错误处理 | 有兜底逻辑、详细错误信息 | bare try/pass、忽略异常 |
| 代码复用 | 抽象公共函数 | 重复代码片段（copy-paste） |
| 提交习惯 | 单次 commit 单一功能 | 重复 message 多次 commit |
| 命名规范 | 清晰、一致 | 随意命名或无注释 |
| 代码复用 | import 后不使用 | |
| 测试覆盖 | 有单元测试 | 无测试文件 |

**Step 3: Go 代码关注点**
- 是否有 `c.Logger.With()` 结构化日志
- 是否有 `errs.go` 错误码定义
- 是否有兜底路径（fallback）
- 是否有新增文件（新功能）

**Step 4: Vue/前端代码关注点**
- i18n 多语言文件是否同步更新
- import 是否正确清理
- API 接口是否正确（getWorkflowDefinitionDetail vs getWorkflowDefinitions）
- 是否有格式化问题（注释行尾多字符）

**Step 5: 通用问题**
- 重复 commit（相同 message 2-3次）→ 没有 rebase 习惯
- 代码行数多但无测试文件 → 质量风险

### DEVS 配置（2026-04-16 更新）

```python
DEVS = {'张佳奇', '张天洁', '刘立祥', '雍蒙蒙', '王慧仙', '李建海', '郭中华', '赵江波', '王嘉旺', '赵铭'}
```
**统一标准，无角色区分。** GitLab 零提交 = ⚠️ 无GitLab提交，直接警告。

### GitLab Commit 抓取脚本
- `~/.hermes/skills/jira-daily-summary/scripts/gitlab_commits.py` - v2 版本，正确处理多行 commit message
- 输出：`/tmp/gitlab-commits-<YYYY-MM-DD>.json`

### GitLab 项目列表（hypertron/hypermotion 组）
- newmuse (140): 主要产品代码，commit 最多
- nirvana (105): 元数据相关
- porter (138): 分支 2
- ant (135): 分支 1
- linux-agent (148): 分支 1
- CI-CD: 分支 3

### 报告结构（2026-04-16 确认版）

**第一部分【产品层面进展】** — 整体视角，看昨天团队在产品层面的产出
- JIRA 完成汇总（按 issue 类型分组）
- GitLab 代码产出（按 JIRA issue 聚合，含作者、人数、行数）
- JIRA 新建汇总（按 issue 类型分组）
- 整体数据一行汇总

**第二部分【每人评估】** — 统一标准，不区分角色
- 汇总表：每人 JIRA完成/新建、GL行数、commit数、评分、问题
- 详细工作内容：每人 JIRA完成/新建 + GitLab代码 + JIRA评论 + 代码质量
- 共性质量问题：重复commit、无测试文件、极低产出、无GitLab提交

**统一标准（2026-04-16 确认）：**
- 所有人同一评分标准，无角色区分
- 无 GitLab 提交 → ⚠️ 无GitLab提交（直接警告，不解释）
- 不再说"测试人员不考核GitLab"，直接报问题

def api(path, token):
    url = 'http://192.168.10.254:20080/api/v4' + path
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

token = get_token()
# 获取某个 commit 的 diff
diff = api(f'/projects/{pid}/repository/commits/{sha}/diff', token)
# diff 是 list，每个元素含 new_path, diff(完整内容), stats{additions, deletions}
```

**审查维度（深度）：**
- 错误处理：是否有兜底逻辑、详细错误信息 vs bare try/pass
- 代码复用：是否抽象公共函数 vs 重复代码片段
- import 清理：新增 import 后是否有未使用的残留
- 格式化：注释行尾是否有多余字符
- 提交习惯：message 是否重复、commit 是否拆分合理

### GitLab Commit 抓取脚本
- `~/.hermes/skills/jira-daily-summary/scripts/gitlab_commits.py` - v2 版本，正确处理多行 commit message
- 输出：`/tmp/gitlab-commits-<YYYY-MM-DD>.json`

### GitLab 项目列表（hypertron/hypermotion 组）
- newmuse (140): 主要产品代码，commit 最多
- nirvana (105): 元数据相关
- porter (138): 分支 2
- ant (135): 分支 1
- linux-agent (148): 分支 1
- CI-CD: 分支 3

### 已知问题（2026-04-16 已修复）

1. ✅ **JIRA 新建重复解析**：已修复。`jira_to_md.py` 中 `created` 和 `updated` 两个 JQL 查询结果现在按 key 合并去重后再 enrichment，不再重复。
2. ✅ **HTML 表格被当作 summary**：已修复。`enrich()` 中对 `summary` 字段也调用 `strip_html()`，HTML 标签被清除。

## 文件清单
| 文件 | 用途 |
|------|------|
| `jira_to_md.py` | JIRA 数据拉取 → Markdown 缓存 |
| `gitlab_commits.py` | GitLab commit 抓取 → JSON 缓存（v2）|
| `integrated_report.py` | **整合报告生成（JIRA + GitLab + 代码质量三合一）** |
| `jira_report_final.py` | 旧版报告脚本（已被 integrated_report.py 替代）|
| `jira_analyze_md.py` | 旧分析脚本（有 bug） |
| `jira_summary.py` | 原始汇总脚本 |

### 完整报告生成（当前使用）
```bash
# 1. JIRA → Markdown
~/.hermes/skills/jira-daily-summary/scripts/jira_to_md.py 2026-04-16 -o /tmp/jira-2026-04-16.md

# 2. GitLab commits → JSON
~/.hermes/skills/jira-daily-summary/scripts/gitlab_commits.py 2026-04-16

# 3. 生成整合报告（JIRA + GitLab + 代码质量三合一）
/opt/anaconda3/bin/python3 ~/.hermes/skills/jira-daily-summary/scripts/integrated_report.py 2026-04-16
# 输出：/tmp/integrated-report-2026-04-16.txt
```

**审查原则（严格，不说好话）：**
- 只说风险和质量，不说亮点
- 不评价整体可读性/架构（未见全量代码）
- 不代表代码质量全貌（抽样有限）
- 测试覆盖评估基于 commit 文件名推断，无法读取实际 diff 内容
