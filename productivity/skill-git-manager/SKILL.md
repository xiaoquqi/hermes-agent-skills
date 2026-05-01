---
name: skill-git-manager
description: Skills 目录结构规范与 git 版本管理 — 厘清 skills/ 是唯一真相，区分自建 vs 预装技能
triggers:
  - 厘清 skills 目录结构
  - 分辨自建技能和预装技能
  - 提交技能改动
  - 查看技能 git 历史
  - 恢复技能到某个版本
  - 技能改坏了想回退
---

# Skill Git Manager

## ⚠️ 重要原则：单一真相来源

**`~/.hermes/skills/` 是 Hermes 加载 skills 的唯一路径。**

```
~/.hermes/
└── skills/          ← Hermes 实际加载这里（config.yaml skills.external_dirs 为空）
    ├── devops/
    │   ├── jira-fetcher/       ← 自建 + 预装混合
    │   ├── gitlab-fetcher/     ← 自建
    │   ├── holiday-checker/     ← 自建
    │   └── ...
    ├── orchestration/
    │   ├── jira-final-report/  ← 自建
    │   └── youtube-to-obsidian/ ← 自建
    └── [其他预装技能...]

~/.hermes/skills-mine/  ← ❌ 不在 Hermes 加载路径里，从未生效过
    └── [改在这里永远不会生效]
```

**config.yaml 中 `skills.external_dirs: []` 是空的**，所以 Hermes 只从 `~/.hermes/skills/` 加载。所有改动必须直接改 `skills/` 下的文件。

> 如果发现 `skills/` 里有个 skill 但 `skills_list` 找不到，先检查 `skills/` 下的 `.disabled` 文件或 skill 的 `readiness_status`。

## 技能分类

用中文含量判断（grep 检测 SKILL.md 中的中文字符）：

| 分类 | 特征 | 示例 |
|------|------|------|
| **自建** | 中文 SKILL.md，内容是中文描述和流程 | jira-fetcher、gitlab-fetcher、jira-final-report、youtube-to-obsidian、holiday-checker |
| **预装（未改）** | 英文 SKILL.md，英文 description | webhook-subscriptions |
| **预装（未改但有用）** | 英文描述，但我们经常用 | bilibili-hot、yt-download、task-management |

## 自建 Skills 全列表（2026-04-29 盘点）

**devops/**
- `jira-fetcher/` — JIRA 数据采集，含 per-issue 文字总结
- `gitlab-fetcher/` — GitLab commits 按 JIRA key 归类
- `holiday-checker/` — 中国节假日/工作日查询
- `jira-insights-pipeline/` — Dev Insights 三步流水线（fetch→summarize→report）
- `jira-issue-summary/` — per-issue LLM 双文件总结
- `product-progress/` — 产品维度进展汇报

**orchestration/**
- `jira-final-report/` — JIRA Dev Insights 汇总报告
- `youtube-to-obsidian/` — YouTube→Obsidian 端到端

## Git 版本控制

`~/.hermes/skills/` 本身是有 git 的，每个 skill 目录各自有独立 git 仓库。

### 查看改动

```bash
# 查看某 skill 的未提交改动
cd ~/.hermes/skills/<category>/<skill> && git diff HEAD

# 示例
cd ~/.hermes/skills/devops/jira-fetcher && git diff HEAD
```

### 提交改动

```bash
cd ~/.hermes/skills/<category>/<skill>

git add -A
git commit -m "[skill] <技能名> — <改动描述>"
# 示例
git commit -m "[skill] jira-fetcher — 修复 summarize 输出单文件改为双文件"
```

### 查看历史

```bash
git log --oneline -10
git show <commit-hash>
```

### 回滚

```bash
# 回滚到上一个版本
git checkout HEAD~1 -- .

# 回滚某个文件
git checkout HEAD~1 -- SKILL.md
```

## .gitignore 规范

`skills/` 根目录已有 `.gitignore`，包含以下必须排除的临时文件类型：

```
# Python
__pycache__/
*.py[cod]
*.egg-info/

# Node.js
node_modules/
*.log

# Environment (secrets)
.env

# OS
.DS_Store
*.swp
```

**每次 commit 前确认没有误提交**：Python bytecode（`.pyc`）、node_modules、日志文件不要入库。

## 经验教训（踩过的坑）

- **skills-mine 从来不在加载路径**：之前错误地在 `~/.hermes/skills-mine/` 下开发，那里的文件从未被 Hermes 加载过。所有开发必须在 `~/.hermes/skills/` 里做。
- **不要在 skills-mine 开发**：如果用它做 git 仓库，必须记住每次改完要同步回 `skills/` 才能生效。
- **scripts 路径要写对**：SKILL.md 里引用的脚本路径要用 `~/.hermes/skills/<category>/<skill>/scripts/...`，不要写 `skills-mine/` 的路径。
- **JIRA pipeline 多版本冲突**：同一功能有多个脚本版本（连字符 vs 下划线、不同的输出路径），改之前先确认正在改的是哪个文件。
- **commit 前先扩 .gitignore**：引入新类型文件（Python/Node.js）时，先补 `.gitignore` 再 commit，避免临时文件入库。
