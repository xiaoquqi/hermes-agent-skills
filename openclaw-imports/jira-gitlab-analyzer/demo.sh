#!/bin/bash
# Jira + GitLab 数据分析助手演示脚本
# 展示各种分析功能的使用方法

set -e

echo "🚀 Jira + GitLab 数据分析助手演示"
echo "=============================================="
echo ""

# 检查Python环境
echo "📋 检查Python环境..."
python3 --version
echo ""

# 检查依赖库
echo "📦 检查依赖库..."
python3 -c "import jira; import gitlab; import pandas; print('✅ 所有依赖库已安装')" || {
    echo "❌ 缺少依赖库，正在安装..."
    pip3 install jira python-gitlab pandas
}
echo ""

# 显示帮助信息
echo "📖 可用分析类型："
echo "  1. sprint-unfinished    - 当前Sprint未完成任务分析"
echo "  2. long-unupdated       - 长时间未更新任务分析"
echo "  3. prev-day-completion  - 前一个工作日任务完成情况"
echo ""

# 示例配置（用户需要根据实际情况修改）
echo "⚙️  示例配置参数："
echo "Jira服务器: http://office.oneprocloud.com.cn:9005"
echo "GitLab服务器: https://gitlab.example.com"
echo ""

# 显示使用示例
echo "🔧 使用示例："
echo ""
echo "示例1: 分析当前Sprint未完成任务"
echo "python3 analyzer.py \\"
echo "  --jira-server \"http://office.oneprocloud.com.cn:9005\" \\"
echo "  --jira-username \"your-username\" \\"
echo "  --jira-password \"your-password\" \\"
echo "  --gitlab-server \"https://gitlab.example.com\" \\"
echo "  --gitlab-token \"your-token\" \\"
echo "  --analysis-type sprint-unfinished \\"
echo "  --board-id 123"
echo ""
echo "示例2: 分析3天未更新的任务"
echo "python3 analyzer.py \\"
echo "  --jira-server \"http://office.oneprocloud.com.cn:9005\" \\"
echo "  --jira-username \"your-username\" \\"
echo "  --jira-password \"your-password\" \\"
echo "  --analysis-type long-unupdated \\"
echo "  --days 3 \\"
echo "  --project \"YOUR-PROJECT\""
echo ""
echo "示例3: 分析前一个工作日完成情况"
echo "python3 analyzer.py \\"
echo "  --jira-server \"http://office.oneprocloud.com.cn:9005\" \\"
echo "  --jira-username \"your-username\" \\"
echo "  --jira-password \"your-password\" \\"
echo "  --analysis-type prev-day-completion"
echo ""

# 创建配置文件模板
echo "📝 创建配置文件模板..."
cat > config_template.json << 'EOF'
{
    "jira": {
        "server": "http://your-jira-server.com",
        "username": "your-username",
        "password": "your-password"
    },
    "gitlab": {
        "server": "http://your-gitlab-server.com",
        "token": "your-private-token"
    },
    "settings": {
        "default_board_id": 123,
        "default_project": "YOUR-PROJECT",
        "unupdated_days_threshold": 3,
        "max_results": 100
    }
}
EOF
echo "✅ 配置文件模板已创建: config_template.json"
echo ""

# 显示分析器功能
echo "🎯 分析器功能特点："
echo "  ✅ 严格使用Python jira库获取Jira数据"
echo "  ✅ 严格使用python-gitlab库获取GitLab数据"
echo "  ✅ 不生成、不推测、不模拟任何数据"
echo "  ✅ 每份报告只聚焦单一分析维度"
echo "  ✅ 使用Markdown表格清晰展示数据"
echo "  ✅ 提供基于数据的客观分析和建议"
echo ""

echo "🔍 数据获取范围："
echo "  • Jira: 任务标题、负责人、状态、时间、变更历史、评论"
echo "  • GitLab: 提交记录、合并请求、分支、作者、Jira关联"
echo ""

echo "⚠️  重要提醒："
echo "  1. 请确保有正确的Jira和GitLab访问权限"
echo "  2. 用户名/密码和访问令牌需要妥善保管"
echo "  3. 分析前请确认服务器地址正确无误"
echo "  4. 大数据量分析可能需要较长时间"
echo ""

echo "📞 技术支持："
echo "  如遇到问题，请检查："
echo "  • 网络连接是否正常"
echo "  • 登录凭据是否有效"
echo "  • 项目权限是否足够"
echo "  • API访问是否被防火墙阻止"
echo ""

echo "🎉 演示完成！现在您可以开始使用Jira + GitLab数据分析助手了。"
echo "请根据您的实际环境修改配置参数，然后运行相应的分析命令。"