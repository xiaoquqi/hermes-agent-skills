---
name: jira-report
description: JIRA parsed 数据 → 管理汇报报告（Summary + Detailed 双文件）
---

# jira-report

JIRA parsed 数据 → 管理汇报报告（Summary + Detailed 双文件）

## 目录结构

```
dev-insights/
├── daily/{date}/parsed/          ← 扁平：KEY.summary.md / KEY.detailed.md
├── weekly/week={year-Www}/parsed/
├── monthly/{year-mm}/parsed/
└── reports/                      ← 输出目录
    ├── DailyReport-20260501.summary.md
    ├── DailyReport-20260501.detailed.md
    ├── WeeklyReport-2025-W18-20260505-20250511.summary.md
    ├── WeeklyReport-2025-W18-20260505-20250511.detailed.md
    └── MonthlyReport-202505.summary.md
        └── MonthlyReport-202505.detailed.md
```

## 使用方式

```
/jira-report daily 2026-05-01
/jira-report weekly 2026-W18
/jira-report monthly 2026-05
```

## 输入

- 日报：`dev-insights/daily/{date}/parsed/*.summary.md` + `*.detailed.md`
- 周报：`dev-insights/weekly/week={year-Www}/parsed/*.summary.md` + `*.detailed.md`
- 月报：`dev-insights/monthly/{year-mm}/parsed/*.summary.md` + `*.detailed.md`

## 输出

1. `summary` 报告 — 产品模块视角
2. `detailed` 报告 — 按人维度 + 饱和度评估

两个文件并行生成，写入 `dev-insights/reports/`。

## LLM Prompt

### Summary Prompt（整体情况 + 风险）

```
将一组工作事项汇总成管理层汇报材料。

---

【输出结构】

## 1. 整体情况
- 将输入中每个事项的一句话描述，合并 → 轻量去重（同模块同类型合并）→ 润色整理
- 保持原始信息不丢失，但更通顺
- 按模块/类型自然分组，不需要重度抽象

## 2. 风险
- 提炼关键风险（最多3-5条）
- 格式：风险点 + 影响范围

---

【约束】

- 禁止逐条罗列输入内容（必须合并同模块同类项）
- 禁止重度抽象或重新编造
- 面向管理层
```

### Detailed Prompt（按人汇总）

```
将一组工作事项汇总为按人员维度的贡献清单。

---

【输出结构】

## 第一部分：汇总表

| 人员 | 新建 | Done | In Progress | To Do |
|------|------|------|-------------|-------|

- 新建 = 周期内该人员新建/领用/报告的事项数量
- Done = 已完成的事项数量
- In Progress = 进行中的事项数量
- To Do = 待处理的事项数量
- 严格按指定周期筛选，只统计该周期内的贡献

## 第二部分：详细进展 + 饱和度评估

### 【人员姓名】

#### 核心贡献
- 每条注明：事项描述 + 完成度（Done / In Progress / To Do）
- 不合并，不遗漏

#### 工作饱和度
- **等级**：高 / 中 / 低
- **判断依据**：
  - 涉及事项范围（是否跨模块/多问题）：
  - 工作复杂度（是否涉及系统性问题）：
  - 是否承担关键路径任务（是/否）：
  - 综合评定：（简述）

---

【约束】

- 严格按指定周期筛选
- 每人的具体事项必须逐条列出，不省略完成度
- 禁止输出"核心开发者"、"能力强/弱"、"表现优秀"等主观评价
- 当信息不足时，使用"主要集中在…"、"参与有限"等保守表达
```

## 读取文件技巧（重要）

parsed 目录可能有 80+ 个文件，用 execute_code 逐个 read_file 会触发 50 次 tool call 上限。

**正确做法**：用 terminal 拼接文件后一次性读取：
```bash
cd {parsed_dir} && cat *.summary.md > /tmp/summary_all.txt && cat *.detailed.md > /tmp/detailed_all.txt
```
然后读 `/tmp/summary_all.txt` 和 `/tmp/detailed_all.txt` 两个文件即可。

## 注意事项

- 周报日期范围自动推导（周一→周日），文件名前缀用 `YYYYMMDD-YYYYMMDD` 格式
- 月报直接用 `YYYYMM` 格式
- 输出前自动创建 `dev-insights/reports/` 目录
- skill 变更后自动 push 到 git@github.com:xiaoquqi/hermes-agent-skills.git
