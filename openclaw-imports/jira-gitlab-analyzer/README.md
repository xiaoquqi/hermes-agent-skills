# Jira + GitLab 数据分析助手

严格遵循数据获取 → 分析 → 输出流程的Jira和GitLab数据分析工具。

## 功能特性

### 🔍 数据获取
- **Jira数据**: 使用Python `jira`插件获取，包括任务标题、负责人、状态、时间信息、变更历史、评论等
- **GitLab数据**: 使用Python `python-gitlab`库获取，包括提交记录、合并请求、分支信息等
- **严格数据验证**: 所有数据必须通过API获取，不允许自行生成或推测

### 📊 分析维度
1. **当前Sprint未完成任务分析**
   - 未完成任务列表
   - 风险点和阻塞分析
   - 按优先级和负责人统计

2. **长时间未更新任务分析**
   - 按天数统计未更新任务
   - 风险等级评估
   - 潜在阻塞原因分析

3. **前一个工作日任务完成情况**
   - 每个成员完成任务列表
   - 完成效率统计
   - 延迟任务分析

4. **前一个月整体任务汇总**
   - 总完成任务数、未完成任务数
   - 按负责人统计完成任务数量
   - 任务类型和优先级分布

5. **评论与改动分析**
   - 任务改动次数、评论活跃度
   - 潜在阻塞或异常任务识别

6. **GitLab关联分析**
   - 任务关联提交/合并请求情况
   - 提交活跃度与任务完成关系
   - 未关联Jira的提交/合并请求统计

## 安装要求

```bash
pip3 install jira python-gitlab pandas matplotlib
```

## 使用方法

### 基本用法

```bash
# 分析当前Sprint未完成任务
python3 analyzer.py \
  --jira-server "http://your-jira-server.com" \
  --jira-username "your-username" \
  --jira-password "your-password" \
  --gitlab-server "http://your-gitlab-server.com" \
  --gitlab-token "your-token" \
  --analysis-type sprint-unfinished \
  --board-id 123

# 分析长时间未更新任务
python3 analyzer.py \
  --jira-server "http://your-jira-server.com" \
  --jira-username "your-username" \
  --jira-password "your-password" \
  --gitlab-server "http://your-gitlab-server.com" \
  --gitlab-token "your-token" \
  --analysis-type long-unupdated \
  --days 3 \
  --project "YOUR-PROJECT"

# 分析前一个工作日任务完成情况
python3 analyzer.py \
  --jira-server "http://your-jira-server.com" \
  --jira-username "your-username" \
  --jira-password "your-password" \
  --gitlab-server "http://your-gitlab-server.com" \
  --gitlab-token "your-token" \
  --analysis-type prev-day-completion
```

### 参数说明

- `--jira-server`: Jira服务器地址
- `--jira-username`: Jira用户名
- `--jira-password`: Jira密码
- `--gitlab-server`: GitLab服务器地址
- `--gitlab-token`: GitLab访问令牌
- `--analysis-type`: 分析类型
  - `sprint-unfinished`: 当前Sprint未完成任务
  - `long-unupdated`: 长时间未更新任务
  - `prev-day-completion`: 前一个工作日任务完成情况
- `--board-id`: Jira看板ID（分析Sprint时需要）
- `--days`: 未更新天数阈值（默认3天）
- `--project`: 项目名称（可选）

## 输出格式

所有报告都以Markdown格式输出，包含：

1. **数据结果**: 表格或列表形式展示统计数据
2. **分析结论**: 基于数据的客观分析
3. **可操作建议**: 针对发现问题的改进建议

## 数据字段

### Jira数据字段
- 任务标题 (title)
- 负责人 (assignee)
- 状态 (status)
- 创建时间 (created)
- 最近更新时间 (updated)
- 完成时间 (resolved)
- 任务类型 (issue_type: Story/Bug/Task)
- 优先级 (priority)
- 每一次状态改动 (change history)
- 每条评论记录 (comments)

### GitLab数据字段
- 提交记录 (commits)
- 合并请求 (merge requests)
- 分支信息
- 作者及关联Jira任务号

## 重点约束

✅ **严格遵守的原则**:
- 所有数据必须通过Python插件获取
- 不允许自行生成、猜测或模拟数据
- 每份报告只聚焦对应分析需求
- 先列出结果，再给结论和建议

❌ **禁止的行为**:
- 使用模拟数据或推测数据
- 合并多个分析维度到一份报告
- 生成与Jira/GitLab无关的内容
- 跳过数据获取直接给出结论

## 示例输出

### Sprint未完成任务报告
```markdown
# 当前Sprint未完成任务报告
**Sprint名称**: Sprint 23
**分析时间**: 2026-02-06 09:30
**未完成任务数**: 15

## 📋 未完成任务列表

| 任务键 | 标题 | 负责人 | 状态 | 优先级 | 任务类型 | 最后更新 |
|--------|------|--------|------|--------|----------|----------|
| PROJ-123 | 用户登录功能开发 | 张三 | 进行中 | 高 | Story | 2026-02-05 |
| PROJ-124 | 修复支付bug | 李四 | 待办 | 紧急 | Bug | 2026-02-03 |

## ⚠️ 风险分析
...
```

## 故障排除

### 连接问题
- 确保Jira/GitLab服务器地址正确
- 检查用户名/密码或访问令牌的有效性
- 验证网络连接和防火墙设置

### 数据获取问题
- 检查项目权限和访问范围
- 确认JQL查询语句的正确性
- 验证时间范围和过滤条件的合理性

### 性能问题
- 对于大量数据，适当调整max_results参数
- 考虑分批获取数据避免超时
- 优化查询条件减少数据量