name: jira-gitlab-analyzer
description: Jira + GitLab 数据分析助手，严格遵循数据获取 → 分析 → 输出流程

# 环境要求
requirements:
  python: ">=3.8"
  packages:
    - jira>=3.0.0
    - python-gitlab>=3.0.0
    - pandas>=1.3.0
    - matplotlib>=3.3.0

# 配置文件路径
config_file: ~/.jira-gitlab-config.json

# 主要功能
functions:
  sprint-unfinished:
    description: 分析当前Sprint未完成任务
    parameters:
      - board_id: Jira看板ID
    output: Markdown格式的未完成任务报告
    
  long-unupdated:
    description: 分析长时间未更新的任务
    parameters:
      - days: 未更新天数阈值（默认3天）
      - project: 项目名称（可选）
    output: Markdown格式的风险任务报告
    
  prev-day-completion:
    description: 分析前一个工作日任务完成情况
    output: Markdown格式的完成情况报告
    
  monthly-summary:
    description: 前一个月整体任务汇总
    output: Markdown格式的月度汇总报告
    
  activity-analysis:
    description: 评论与改动分析
    output: Markdown格式的活跃度分析报告
    
  gitlab-correlation:
    description: GitLab关联分析
    output: Markdown格式的代码关联报告

# 数据获取规范
data_acquisition:
  jira:
    method: python-jira库
    authentication: 用户名/密码
    required_fields:
      - title (summary)
      - assignee
      - status
      - created
      - updated
      - resolved
      - issue_type
      - priority
      - change_history (changelog)
      - comments
  
  gitlab:
    method: python-gitlab库
    authentication: 私有令牌
    required_data:
      - commits (with messages)
      - merge_requests
      - branches
      - authors
      - jira_key_extraction

# 分析原则
analysis_principles:
  - 严格使用获取的数据，不推测
  - 每份报告聚焦单一分析维度
  - 先展示数据结果，再给结论
  - 提供可操作的改进建议
  - 使用Markdown表格和列表展示数据
  - 禁止生成无关内容

# 质量保证
quality_assurance:
  - 数据验证: 确保API返回有效数据
  - 错误处理: 完善的异常处理机制
  - 性能优化: 合理的数据获取批处理
  - 结果验证: 交叉验证分析结果
  - 用户反馈: 支持结果准确性验证