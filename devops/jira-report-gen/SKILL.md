---
name: jira-report-gen
description: JIRA parsed 数据生成管理汇报报告（日报/周报/月报），支持 summary + detailed 双视角输出
---

# JIRA Report Generation Skill

Generate management-level reports (daily/weekly/monthly) from parsed JIRA data.

## Directory Structure

```
~/.hermes/dev-insights/
├── daily/{date}/parsed/           # e.g. daily/2026-04-29/parsed/
│   └── {KEY}.summary.md          # 扁平文件，无子目录
│   └── {KEY}.detailed.md
├── weekly/week={year-Www}/parsed/ # e.g. weekly/week=2026-W18/parsed/
│   └── {KEY}.summary.md
│   └── {KEY}.detailed.md
├── monthly/{year-mm}/parsed/      # e.g. monthly/2026-04/parsed/
│   └── {KEY}.summary.md
│   └── {KEY}.detailed.md
├── attachments/
└── reports/                       # 输出目录，需创建
```

## Report Output Naming

| 类型 | 文件名格式 |
|------|-----------|
| 日报 | `DailyReport-20260501.summary.md` / `detailed.md` |
| 周报 | `WeeklyReport-2025-W18-20260505-20260511.summary.md` / `detailed.md` |
| 月报 | `MonthlyReport-202505.summary.md` / `detailed.md` |

## Summary Prompt (产品模块视角)

```
你是产品负责人，需要将一组"需求与问题描述"汇总成管理层汇报材料。

输入内容已是整理后的需求（功能）与问题（Bug），无需关心其来源。

请按"功能模块"进行归类总结，而不是逐条罗列。

特别要求：
- 必须覆盖全部信息
- 必须合并同类项（避免重复表达）
- 所有"已完成事项"和"已解决问题"，必须说明其对项目推进或交付的价值

【输出结构】

1. 产品整体情况
- 产品整体进展（1-2句话）
- 产品稳定性判断：稳定 / 波动 / 风险（必须明确）
- 判断依据（1句话）

2. 功能进展（按模块分类）
【模块名】
- 新需求（新增/进行中）
- 已完成（+ 带来的改进 + 对项目推进的价值）

3. 问题情况（按模块分类）
【模块名】
- 新发现问题
- 已解决问题（+ 修复效果 + 对项目推进的价值）

4. 风险（关键风险识别，最多3-5条）
- 风险点 + 影响范围

【全局约束】
- 禁止逐条罗列输入内容
- 禁止输出过程细节
- 必须进行抽象归纳（按模块 + 能力点/问题类型）
- 输出应面向管理层，强调"整体情况 + 推进价值 + 风险"
```

## Detailed Prompt (按人维度 + 饱和度评估)

```
你是产品负责人，需要将一组"需求与问题进展信息"汇总为"按人员维度的贡献与工作饱和度评估报告"。

输入包含多个事项，每条信息包含负责人。

请按"人员"进行归类总结，并在此基础上对每个人的工作饱和度进行评估。

【输出结构】

【人员姓名】
1. 核心贡献
2. 价值体现（解除阻塞/支撑上线/提升稳定性/提升效率）
3. 贡献侧重点（功能开发/稳定性修复/架构优化/问题处理/支持交付）
4. 工作饱和度评估（高/中/低）
   - 判断依据：参与事项数量、工作复杂度、是否关键路径任务
5. 风险提示（可选）

【全局约束】
- 禁止用"提交次数/操作次数"作为主要评估依据
- 必须结合"复杂度 + 影响 + 类型"进行判断
- 输出应客观，不做情绪化评价
- 强调"结构性判断"
```

## Implementation Logic

1. **读取 parsed 文件**：根据报告类型（daily/weekly/monthly），找到对应目录，读所有 `*.summary.md` 和 `*.detailed.md`
2. **合并内容**：
   - daily：直接读一天的文件
   - weekly：合并一周7天所有 parsed 文件
   - monthly：合并整月所有 parsed 文件
3. **两次 LLM 调用**：
   - 调用1：summary prompt → `reports/DailyReport-{date}.summary.md`
   - 调用2：detailed prompt → `reports/DailyReport-{date}.detailed.md`
4. **写入 reports 目录**：如果目录不存在需先创建

## Usage

```
/jira-report daily 2026-05-01
/jira-report weekly 2026-W18
/jira-report monthly 2026-05
```
