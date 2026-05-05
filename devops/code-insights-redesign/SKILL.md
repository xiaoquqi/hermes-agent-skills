---
name: code-insights-redesign
description: Code review skill redesign notes — full clone + Claude Code real review
---

# code-insights Skill Redesign Notes

## Architecture (2026-05-05)

### Three-layer directory structure
```
~/.hermes/code-insights/
├── repos/                              # 持久化的代码仓库（全量 clone，一次 clone 持续更新）
│   └── {group}/{project}/.git/         # git pull 增量同步
├── commits/{date}/                     # 按天归档 commit 数据
│   └── {group}/{project}/
│       ├── commits.json               # commit 元数据列表
│       └── {sha}.patch                # patch 文件（备用）
└── reports/daily/{date}/              # 报告输出
    └── {group}/{project}/
        ├── {sha}.summary.md          # 产品维度
        └── {sha}.detailed.md         # 个人维度（代码质量 + 效率评估）
```

### collector.py (采集层)
- 全量 clone 项目分支到 repos/，持久保存
- 每日 `git pull` 增量同步，不重复 clone
- 支持天/周/月时间范围，本质都是按天归档
- 输出 commits.json + patch 到 commits/{date}/

### reporter.py (报告层)
- 读取 commit 元数据
- `git checkout sha` 切换到指定 commit
- 启动 Claude Code 做真实代码审查（不是纯 prompt 生成）
- 输出 Summary（产品视角）+ Detailed（个人视角）

## Efficiency Evaluation (已确认犀利版)
- 理论开发周期：基于提交内容估算
- 返工/Bug修复：能力差距的实锤，不给返工找借口
- 一次性写好 vs 额外消耗对比，用数字充分暴露能力短板
- 示例：理论3小时，额外3.5小时（+117%），暴露类型转换/N+1/事务缺失等问题

## Current Implementation Status
- skill 已存在但架构需重构：~/.hermes/skills/devops/code-insights/
- 当前 collector.py 是 shallow clone（每次只拉当天 commits），需改为全量 clone + 持久化
- 当前 reporter.py 是 `claude -p` 调 prompt，需改为让 Claude Code 真正 checkout + 读代码做审查
- 效率评估 prompt 已更新到犀利版，需在 reporter.py 重构后验证

## Next Steps
1. 重构 collector.py：全量 clone 到 repos/，git pull 增量更新
2. 重构 reporter.py：checkout sha → Claude Code review
3. 验证效率评估逻辑在真实 Claude Code 审查下是否仍然犀利
