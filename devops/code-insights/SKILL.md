---
name: code-insights
description: GitLab 代码提交采集与分析 —— 基于分支规则 clone 到本地提取 patch，按天存储
---

# code-insights

GitLab 代码提交采集工具。clone 项目到本地，用 git 命令提取 commit patch，按天存储原始数据。

## 分支规则（与 clone_projects.sh 保持一致）

| 项目类型 | 分支 | 说明 |
|----------|------|------|
| `hypermotion/*` | `saas_qa` | 大部分项目的默认分支 |
| `atomy/*` | `qa` | atomy 模块固定用 qa 分支 |
| `hypermotion/CI-CD` | `master` | CI-CD 固定用 master |

## 目录结构

```
~/.hermes/code-insights/
├── commits/{date}/{group}/{project}/    ← 原始 patch（采集阶段）
│   ├── commits.json
│   └── {commit_id}.patch
└── reports/                              ← 报告输出（报告阶段）
    └── daily/{date}/{group}/{project}/
        ├── {commit_id}.summary.md        ← 产品视角：改动 + 风险
        └── {commit_id}.detailed.md      ← 代码质量视角：质量 + 效率
```

## 采集流程

1. OAuth token 获取（密码模式）
2. 遍历 PROJECT_LIST（与 clone_projects.sh 项目列表一致）
3. 根据 `resolve_branch()` 确定分支：atomy → qa, CI-CD → master, 其他 → saas_qa
4. 调用 GitLab Commits API：`?ref_name={branch}&since=&until=`（只拉指定分支，不过 all=true）
5. 过滤无效 commit（gitlab/bot/system 用户、Merge 分支）
6. Shallow clone 指定分支到本地临时目录（嵌入认证信息到 URL）
7. 用 `git show` 逐个保存 patch 文件
8. 保存 commit 元数据到 commits.json
9. 删除临时 clone 目录

## 报告阶段

每个 commit 单独生成两个报告：

| 报告 | 视角 | 内容 |
|------|------|------|
| `*.summary.md` | 产品视角 | 改动描述 + 风险/爆炸半径评估 |
| `*.detailed.md` | 代码质量视角 | 质量评分 + 效率评估（AI 加持背景） |

### Summary 报告内容

```
### 1. 产品改动
- 一句话描述（面向产品/管理层）
- 改了什么模块/功能

### 2. 风险评估（爆炸半径）
- 影响范围：小 / 中 / 大
- 理由（改了哪些模块、是否涉及核心业务、是否有回滚难度）
- 建议（如果有）
```

### Detailed 报告内容

评分哲学：AI 时代，很多事不是能不能，而是想不想。能轻松做到却没做 = 严重失分。

```
### 1. 代码质量评分（严格 AI 时代标准）
| 维度 | 评分（1-5）| 评分标准 |

### 2. 质量分析
- 主要问题（最多3个，用文件:行号引用，说明 AI 时代为什么这是不应该的）
- 改进建议（具体可操作，不要空泛）

### 3. 效率评估（展示推导过程）
- 代码行数变化：+X / -Y
- 提交粒度：合理 / 偏大（建议拆成多个 commit）/ 偏小（可合并）
- 理论开发周期推导（分项 + 汇总）
- 评估说明（推导过程，不是结论）
```

## 使用方式

### 采集阶段

```bash
# 采集指定日期
python3 ~/.hermes/skills/devops/code-insights/scripts/collector.py 2026-04-30

# 采集今日
python3 ~/.hermes/skills/devops/code-insights/scripts/collector.py today
```

### 报告阶段

```bash
# 生成指定日期的报告
python3 ~/.hermes/skills/devops/code-insights/scripts/reporter.py 2026-04-30

# 生成今日报告
python3 ~/.hermes/skills/devops/code-insights/scripts/reporter.py today
```

## 输出

- `commits/{date}/{group}/{project}/commits.json` — commit 元数据
- `commits/{date}/{group}/{project}/{commit_id}.patch` — 每个 commit 的完整 diff
- `reports/daily/{date}/{group}/{project}/{sha}.summary.md` — 产品视角报告
- `reports/daily/{date}/{group}/{project}/{sha}.detailed.md` — 代码质量报告

## 核心设计

### GitLab 认证

使用 `oauth/token`（密码模式）：
```
POST http://192.168.10.254:20080/oauth/token
{"grant_type": "password", "username": "devops", "password": "devops@HyperMotion"}
```

### 项目列表

PROJECT_LIST 硬编码，与 clone_projects.sh 保持一致，覆盖 HyperBDR/income/FC 三个项目组。

### Commits API

```
GET /projects/{id}/repository/commits?ref_name={branch}&since={after}&until={date}%2023:59:59
```
- `ref_name`：指定分支，不过 all=true（避免引入其他分支噪音）
- `since/until`：日期范围筛选

### Clone URL 重写

项目原始 URL 为 `ssh://git@office.oneprocloud.com.cn:20022/{path}.git`（DNS 解析不了），重写为 `ssh://devops:devops%40HyperMotion@192.168.10.254:20022/{path}.git`。

注意：clone 用 SSH 协议端口 20022，API 用 HTTP 端口 20080。
密码里的 `@` 要 URL 编码为 `%40`。

### Shallow Clone

- `--depth=100` 限制历史
- `--branch {branch}` 指定分支
- `--single-branch` 只拉单个分支
- clone 到 `/tmp/code-insights-{date}-{project}/`

### Git 命令

```bash
# 获取单个 commit 的 patch（完整 diff）
git show {commit_id} --format= --patch > {commit_id}.patch
```

### 过滤规则

跳过：
- author 为 `gitlab/bot/system/空` 的自动化提交
- message 以 `Merge branch` 开头的 merge commit

## 已知坑（调试记录）

### git show 的 `-- patch` 不是你想的那样
```bash
# ❌ 错误：git 把 "patch" 当文件路径，只输出那个文件的 diff（不存在就为空）
git show {sha} --format= -- patch

# ✅ 正确：用 --patch 标志，不过滤文件
git show {sha} --format= --patch
```

### 项目搜索 API 不接受 URL-encoded 斜杠
```python
# ❌ 错误：urllib.parse.quote('hypermotion/nezha') → 'hypermotion%2Fnezha'，搜不到
api(f'/projects?search={urllib.parse.quote(project_path)}')

# ✅ 正确：只搜索项目名（路径最后一段），然后用完整 path_with_namespace 匹配
proj_name = project_path.rsplit('/', 1)[-1]  # → "nezha"
result = api(f'/projects?search={proj_name}&per_page=50')
for p in result:
    if p['path_with_namespace'] == project_path:
        return p
```

### ref_name 不要加 `origin/` 前缀
```python
# ❌ 错误：ref_name=origin/saas_qa 返回 0 结果
# ✅ 正确：ref_name=saas_qa
GET /projects/{id}/repository/commits?ref_name=saas_qa&since=&until=
```

### `all=true` 会拉所有分支，引入噪音
```python
# ❌ 错误：all=true 会拉所有分支的 commits，包括不在 default branch 上的 feature 分支
GET /projects/{id}/repository/commits?all=true&since=&until=

# ✅ 正确：配合 ref_name 只拉指定分支
GET /projects/{id}/repository/commits?ref_name=saas_qa&since=&until=
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GITLAB_URL` | `http://192.168.10.254:20080` | GitLab 地址 |
| `GITLAB_USER` | `devops` | 用户名 |
| `GITLAB_PASS` | `devops@HyperMotion` | 密码 |
| `GITLAB_GROUP_ID` | `36` | hypermotion 组 ID |

## 依赖

- `git`：系统命令

## 报告阶段（Claude Code CLI）

reporter.py 使用 Claude Code CLI 进行代码审查（而非 LLM API 调用）：

```python
subprocess.run([
    "claude", "-p", "--output-format", "text",
    "--no-session-persistence", "--dangerously-skip-permissions", prompt
], ...)
```

Claude Code 直接读取本地代码仓库（通过 `clone_and_prepare_repo` 切到指定 SHA 的 detached HEAD），可以引用本地文件进行更精准的分析。

### Detailed 报告评分标准（AI 时代严格版）

**评分哲学**：AI 时代，很多事不是能不能，而是想不想。能轻松做到却没做 = 严重失分。

| 维度 | 评分标准 |
|------|----------|
| 可读性 | 1分=难以阅读 3分=基本规范 5分=命名清晰+注释充分+结构合理 |
| 可维护性 | 1分=高耦合低内聚 3分=基本分层合理 5分=职责单一+依赖清晰+扩展性强 |
| 安全性 | 1分=有严重安全风险 3分=无明显漏洞 5分=有安全意识+防御性编程 |
| 测试覆盖推断 | 1分=零测试变更 3分=有基本测试 5分=测试充分+边界覆盖 |

### 效率评估推导要求（犀利实锤版）

**核心逻辑**：效率评估的不是"开发周期"，而是**这次提交暴露的研发能力短板**。如果代码质量差需要返工，说明研发考虑欠佳，能力有差距 — 不要给找借口，直接说。

**Prompt 指令**（写在 DETAILED_PROMPT_TPL 里）：
```
理论开发周期：（估算这次提交如果一次性写好需要多久，然后指出提交暴露的问题导致的额外消耗，充分暴露研发人员的能力短板。用数字说话，不要客气）
```

**表格可以有**，但内容要犀利：
```markdown
| 阶段 | 理论耗时 | 问题暴露耗时 | 额外消耗 |
|------|----------|--------------|----------|
| 功能开发 | X 小时 | - | - |
| Bug 修复（具体问题） | - | Y 小时 | 未考虑XXX |
| **总计** | **Z 小时** | **W 小时** | **额外 N%** |
```

**示例输出**：
```
nezha/d760e414 — Add trialed for tenant

代码行数：+102 / -7
提交粒度：偏大（把trialed筛选和批量更新API混在一个commit里）

理论开发周期：

一次性写好约 3 小时。但提交暴露了：类型转换 bug（"true" in (True,) 返回 False）、UUID join 崩溃（N+1 查询）、事务缺失。靠 review 发现和修复这些问题额外消耗 3.5 小时，效率约 57%。

一个人写代码的习惯好不好，从提交里就能看出来。这个提交反映出来的是：写的时候考虑不够周全，比较毛糙。
```

**两种输出形式都可以**：
- 纯自然段落（如上）
- 表格 + 段落结合（如 nezha/d760e414 的效率评估有表格也有总结段落）

关键是：**不要给返工找借口**，数字要实。

### 质量分析要求

- 主要问题：最多3个，用文件:行号引用，说明"AI 时代为什么这是不应该的"
- **不再输出"优点"部分**（对研发评价无实质价值）
- 改进建议：具体可操作，不要空泛

### 验证方式

**先跑单个 commit 验证 prompt 效果，再跑全量：**

```bash
# ❌ 全量跑可能超时（7 commits × 2 报告 × 180s timeout = 可能超过 5 分钟限制）
python reporter.py 2026-04-30

# ✅ 先测单个 commit
# 编辑 reporter.py 的 main()，只处理一个 commit
# 或用 python -c "..." 单独调用 process_commit()
```

## 报告阶段已知坑

### patch 过长时自动分块
`split_patch()` 会按文件拆分 patch，超大文件按 `@@` hunk 段落二次拆分，每个 chunk 单独调用 Claude Code，结果用 `---` 分隔拼接。

### patch 截断保留上下文
`_split_by_hunes()` 对超大段落截断时保留头尾各 1/3，确保关键逻辑不丢失。

### clone 复用
`clone_and_prepare_repo()` 只在项目级别执行一次（不是每个 commit 重新 clone），后续 commit 只需 `git checkout` 到对应 SHA。
