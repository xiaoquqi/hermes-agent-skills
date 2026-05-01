#!/usr/bin/env python3
"""
简单的Jira昨天成员更新情况分析器
"""

import sys
from datetime import datetime, timedelta

try:
    from jira import JIRA
except ImportError:
    print("❌ 请先安装jira库: pip3 install jira")
    sys.exit(1)

def main():
    # Jira连接配置
    JIRA_SERVER = "http://office.oneprocloud.com.cn:9005"
    JIRA_USERNAME = "sunqi"
    JIRA_PASSWORD = "sunqi1358"
    
    print("🔍 开始连接Jira服务器...")
    print(f"服务器: {JIRA_SERVER}")
    print(f"用户: {JIRA_USERNAME}")
    
    try:
        # 连接Jira
        jira = JIRA(
            server=JIRA_SERVER,
            basic_auth=(JIRA_USERNAME, JIRA_PASSWORD)
        )
        print("✅ 成功连接到Jira服务器")
        
        # 计算昨天的时间范围
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        yesterday_start = yesterday.strftime('%Y-%m-%d')
        yesterday_end = today.strftime('%Y-%m-%d')
        
        print(f"📅 分析日期: {yesterday_start}")
        print(f"🕐 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # 构建JQL查询 - 获取昨天更新的问题
        jql = f"updated >= '{yesterday_start}' AND updated < '{yesterday_end}' ORDER BY updated DESC"
        print(f"🔍 执行JQL: {jql}")
        
        # 获取问题（限制数量避免超时）
        issues = jira.search_issues(jql, maxResults=50, fields=['key', 'summary', 'assignee', 'reporter', 'status', 'updated', 'created', 'issuetype', 'priority', 'project'])
        
        print(f"✅ 获取到 {len(issues)} 个昨天更新的问题")
        
        if not issues:
            print("📊 昨天没有更新的问题")
            return
        
        # 分析成员活动
        member_activity = {}
        
        print("\n📊 开始分析成员更新情况...")
        
        for issue in issues:
            # 获取基本信息
            key = issue.key
            title = issue.fields.summary
            assignee = issue.fields.assignee.displayName if issue.fields.assignee else '未分配'
            reporter = issue.fields.reporter.displayName if issue.fields.reporter else '未知'
            status = issue.fields.status.name
            updated = issue.fields.updated
            issue_type = issue.fields.issuetype.name
            priority = issue.fields.priority.name if issue.fields.priority else '未设置'
            project = issue.fields.project.name
            
            # 记录负责人活动
            if assignee not in member_activity:
                member_activity[assignee] = {
                    'assigned_issues': [],
                    'participated_issues': [],
                    'issue_types': {},
                    'statuses': {},
                    'projects': {}
                }
            
            member_activity[assignee]['assigned_issues'].append(key)
            member_activity[assignee]['participated_issues'].append(key)
            member_activity[assignee]['issue_types'][issue_type] = member_activity[assignee]['issue_types'].get(issue_type, 0) + 1
            member_activity[assignee]['statuses'][status] = member_activity[assignee]['statuses'].get(status, 0) + 1
            member_activity[assignee]['projects'][project] = member_activity[assignee]['projects'].get(project, 0) + 1
            
            # 如果报告人不同，也记录报告人活动
            if reporter != assignee and reporter != '未知':
                if reporter not in member_activity:
                    member_activity[reporter] = {
                        'assigned_issues': [],
                        'participated_issues': [],
                        'issue_types': {},
                        'statuses': {},
                        'projects': {}
                    }
                member_activity[reporter]['participated_issues'].append(key)
                member_activity[reporter]['issue_types'][issue_type] = member_activity[reporter]['issue_types'].get(issue_type, 0) + 1
                member_activity[reporter]['statuses'][status] = member_activity[reporter]['statuses'].get(status, 0) + 1
                member_activity[reporter]['projects'][project] = member_activity[reporter]['projects'].get(project, 0) + 1
        
        # 生成报告
        print("\n" + "="*60)
        print("# Jira昨天成员更新情况报告")
        print(f"**分析日期**: {yesterday_start}")
        print(f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"**总更新问题数**: {len(issues)}")
        print("\n## 📊 整体统计")
        print(f"- **参与成员数**: {len(member_activity)}")
        print(f"- **平均参与度**: {sum(len(activity['participated_issues']) for activity in member_activity.values()) / len(member_activity):.1f} 个问题/人")
        print(f"- **最活跃成员**: {max(member_activity.items(), key=lambda x: len(x[1]['participated_issues']))[0]}")
        
        print("\n## 👥 成员活跃度排名")
        print("| 排名 | 成员 | 负责问题 | 参与问题 | 主要工作类型 | 涉及项目 |")
        print("|------|------|----------|----------|--------------|----------|")
        
        # 按参与度排序
        sorted_members = sorted(member_activity.items(), 
                              key=lambda x: len(x[1]['participated_issues']), 
                              reverse=True)
        
        for i, (member, activity) in enumerate(sorted_members, 1):
            assigned_count = len(set(activity['assigned_issues']))
            participated_count = len(set(activity['participated_issues']))
            
            # 主要工作类型
            main_types = sorted(activity['issue_types'].items(), key=lambda x: x[1], reverse=True)[:2]
            types_str = ", ".join([f"{t}({c})" for t, c in main_types])
            
            # 涉及项目
            projects = ", ".join(list(activity['projects'].keys())[:2])
            
            print(f"| {i} | {member} | {assigned_count} | {participated_count} | {types_str} | {projects} |")
        
        print("\n## 🏆 最活跃成员详细分析")
        
        # 详细分析前3名
        for i, (member, activity) in enumerate(sorted_members[:3], 1):
            assigned_issues = list(set(activity['assigned_issues']))
            participated_issues = list(set(activity['participated_issues']))
            
            print(f"\n### {i}. {member}")
            print(f"- **负责问题数**: {len(assigned_issues)}")
            print(f"- **总参与问题数**: {len(participated_issues)}")
            print(f"- **工作类型分布**: {', '.join([f'{t}({c})' for t, c in sorted(activity['issue_types'].items(), key=lambda x: x[1], reverse=True)])}")
            print(f"- **涉及项目**: {', '.join(activity['projects'].keys())}")
            
            if assigned_issues:
                print(f"- **负责的重要问题**:")
                for issue_key in assigned_issues[:3]:  # 显示前3个
                    issue = next((iss for iss in issues if iss.key == issue_key), None)
                    if issue:
                        print(f"  - **{issue_key}**: {issue.fields.summary[:60]}... (状态: {issue.fields.status.name})")
        
        print("\n## 📋 问题更新详情")
        print("### 按任务类型统计")
        print("| 任务类型 | 更新数量 | 占比 | 主要参与者 |")
        print("|----------|----------|------|------------|")
        
        # 按任务类型统计
        type_stats = {}
        for issue in issues:
            issue_type = issue.fields.issuetype.name
            assignee = issue.fields.assignee.displayName if issue.fields.assignee else '未分配'
            if issue_type not in type_stats:
                type_stats[issue_type] = {'count': 0, 'participants': set()}
            type_stats[issue_type]['count'] += 1
            type_stats[issue_type]['participants'].add(assignee)
        
        total_issues = len(issues)
        for issue_type, stats in sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            count = stats['count']
            percentage = f"{(count/total_issues*100):.1f}%"
            participants = ", ".join(list(stats['participants'])[:3])
            print(f"| {issue_type} | {count} | {percentage} | {participants} |")
        
        print("\n### 按状态统计")
        print("| 状态 | 数量 | 占比 |")
        print("|------|------|------|")
        
        status_stats = {}
        for issue in issues:
            status = issue.fields.status.name
            status_stats[status] = status_stats.get(status, 0) + 1
        
        for status, count in sorted(status_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = f"{(count/total_issues*100):.1f}%"
            print(f"| {status} | {count} | {percentage} |")
        
        print("\n## 📈 总结与建议")
        print(f"### 昨天工作特点")
        print(f"- **团队活跃度**: {len(member_activity)} 名成员参与工作")
        print(f"- **问题更新密度**: {len(issues)} 个问题有更新")
        print(f"- **工作类型多样**: 涵盖 {len(type_stats)} 种任务类型")
        print(f"- **状态分布**: 反映团队工作进展")
        
        print(f"\n### 团队协作评估")
        if len(member_activity) > 5:
            print("- ✅ **协作良好**: 多个成员积极参与")
        else:
            print("- ⚠️  **参与度偏低**: 需要更多成员参与")
        
        if len(type_stats) >= 3:
            print("- ✅ **工作全面**: 涵盖多种任务类型")
        else:
            print("- ⚠️  **类型单一**: 工作类型分布不够均衡")
        
        print(f"\n### 改进建议")
        print("1. **保持沟通**: 继续通过Jira更新保持团队同步")
        print("2. **及时更新**: 确保任务状态及时反映实际进展")
        print("3. **负载均衡**: 合理分配任务，避免个别成员负担过重")
        print("4. **定期回顾**: 定期检查长时间未更新的任务")
        
        print("\n" + "="*60)
        print("✅ 分析完成！")
        
        # 保存报告
        report_content = f"""# Jira昨天成员更新情况报告
**分析日期**: {yesterday_start}
**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**总更新问题数**: {len(issues)}

## 📊 整体统计
- **参与成员数**: {len(member_activity)}
- **平均参与度**: {sum(len(activity['participated_issues']) for activity in member_activity.values()) / len(member_activity):.1f} 个问题/人
- **最活跃成员**: {max(member_activity.items(), key=lambda x: len(x[1]['participated_issues']))[0]}

## 👥 成员活跃度排名
| 排名 | 成员 | 负责问题 | 参与问题 | 主要工作类型 | 涉及项目 |
|------|------|----------|----------|--------------|----------|
"""
        
        for i, (member, activity) in enumerate(sorted_members, 1):
            assigned_count = len(set(activity['assigned_issues']))
            participated_count = len(set(activity['participated_issues']))
            main_types = sorted(activity['issue_types'].items(), key=lambda x: x[1], reverse=True)[:2]
            types_str = ", ".join([f"{t}({c})" for t, c in main_types])
            projects = ", ".join(list(activity['projects'].keys())[:2])
            report_content += f"| {i} | {member} | {assigned_count} | {participated_count} | {types_str} | {projects} |\n"
        
        # 保存到文件
        report_file = f"jira_daily_report_{yesterday_start}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()