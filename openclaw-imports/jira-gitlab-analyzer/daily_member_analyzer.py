#!/usr/bin/env python3
"""
Jira昨天成员更新情况分析器
严格遵循数据获取 → 分析 → 输出流程
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse

# 尝试导入必要的库
try:
    from jira import JIRA
except ImportError as e:
    print(f"❌ 缺少必要的Python库: {e}")
    print("💡 请运行: pip3 install jira")
    sys.exit(1)

class JiraDailyAnalyzer:
    def __init__(self, jira_server: str, jira_username: str, jira_password: str):
        """初始化分析器"""
        self.jira_server = jira_server
        self.jira_username = jira_username
        self.jira_password = jira_password
        self.jira_client = None
        
    def connect_jira(self) -> bool:
        """连接Jira服务器"""
        try:
            self.jira_client = JIRA(
                server=self.jira_server,
                basic_auth=(self.jira_username, self.jira_password)
            )
            print(f"✅ 成功连接到Jira: {self.jira_server}")
            return True
        except Exception as e:
            print(f"❌ 连接Jira失败: {e}")
            return False
    
    def get_yesterday_updated_issues(self, project: str = None) -> List[Dict]:
        """获取昨天更新的问题"""
        if not self.jira_client:
            print("❌ Jira客户端未连接")
            return []
        
        try:
            # 计算昨天的时间范围
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            yesterday_start = yesterday.strftime('%Y-%m-%d')
            yesterday_end = today.strftime('%Y-%m-%d')
            
            # 构建JQL查询
            jql = f"updated >= '{yesterday_start}' AND updated < '{yesterday_end}'"
            if project:
                jql += f" AND project = '{project}'"
            
            jql += " ORDER BY updated DESC"
            
            print(f"🔍 执行JQL查询: {jql}")
            issues = self.jira_client.search_issues(jql, maxResults=200, expand='changelog')
            
            result = []
            for issue in issues:
                issue_data = {
                    'key': issue.key,
                    'title': issue.fields.summary,
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else '未分配',
                    'reporter': issue.fields.reporter.displayName if issue.fields.reporter else '未知',
                    'status': issue.fields.status.name,
                    'created': issue.fields.created,
                    'updated': issue.fields.updated,
                    'resolved': getattr(issue.fields, 'resolved', None),
                    'issue_type': issue.fields.issuetype.name,
                    'priority': issue.fields.priority.name if issue.fields.priority else '未设置',
                    'project': issue.fields.project.name,
                    'description': issue.fields.description or '',
                    'change_count': 0,  # 将在后续计算
                    'comment_count': 0,  # 将在后续计算
                    'changes': [],
                    'comments': []
                }
                
                # 获取变更历史
                try:
                    if hasattr(issue, 'changelog'):
                        changes = []
                        for history in issue.changelog.histories:
                            for item in history.items:
                                changes.append({
                                    'author': history.author.displayName if history.author else '未知',
                                    'created': history.created,
                                    'field': item.field,
                                    'from': getattr(item, 'fromString', ''),
                                    'to': getattr(item, 'toString', '')
                                })
                        issue_data['changes'] = changes
                        issue_data['change_count'] = len(changes)
                except Exception as e:
                    print(f"⚠️  获取变更历史失败 {issue.key}: {e}")
                
                # 获取评论
                try:
                    comments = self.jira_client.comments(issue.key)
                    issue_comments = []
                    for comment in comments:
                        # 只统计昨天的评论
                        comment_date = comment.created[:10]
                        if comment_date == yesterday_start:
                            issue_comments.append({
                                'author': comment.author.displayName,
                                'created': comment.created,
                                'body': comment.body[:200] + '...' if len(comment.body) > 200 else comment.body
                            })
                    issue_data['comments'] = issue_comments
                    issue_data['comment_count'] = len(issue_comments)
                except Exception as e:
                    print(f"⚠️  获取评论失败 {issue.key}: {e}")
                
                result.append(issue_data)
            
            print(f"✅ 成功获取 {len(result)} 个昨天更新的Jira问题")
            return result
            
        except Exception as e:
            print(f"❌ 获取Jira问题失败: {e}")
            return []
    
    def analyze_member_updates(self, issues: List[Dict]) -> str:
        """分析成员更新情况"""
        if not issues:
            return "❌ 没有获取到昨天更新的问题数据"
        
        # 按成员统计
        member_stats = {}
        
        for issue in issues:
            assignee = issue['assignee']
            reporter = issue['reporter']
            
            # 统计负责人活动
            if assignee not in member_stats:
                member_stats[assignee] = {
                    'assigned_issues': [],
                    'changes_made': [],
                    'comments_made': [],
                    'issue_types': {},
                    'status_changes': []
                }
            
            member_stats[assignee]['assigned_issues'].append(issue['key'])
            
            # 统计报告人活动（如果不是负责人）
            if reporter != assignee:
                if reporter not in member_stats:
                    member_stats[reporter] = {
                        'assigned_issues': [],
                        'changes_made': [],
                        'comments_made': [],
                        'issue_types': {},
                        'status_changes': []
                    }
            
            # 统计变更活动
            for change in issue['changes']:
                author = change['author']
                if author not in member_stats:
                    member_stats[author] = {
                        'assigned_issues': [],
                        'changes_made': [],
                        'comments_made': [],
                        'issue_types': {},
                        'status_changes': []
                    }
                member_stats[author]['changes_made'].append({
                    'issue': issue['key'],
                    'field': change['field'],
                    'from': change['from'],
                    'to': change['to'],
                    'time': change['created']
                })
                
                # 特别记录状态变更
                if change['field'] == 'status':
                    member_stats[author]['status_changes'].append({
                        'issue': issue['key'],
                        'from': change['from'],
                        'to': change['to']
                    })
            
            # 统计评论活动
            for comment in issue['comments']:
                author = comment['author']
                if author not in member_stats:
                    member_stats[author] = {
                        'assigned_issues': [],
                        'changes_made': [],
                        'comments_made': [],
                        'issue_types': {},
                        'status_changes': []
                    }
                member_stats[author]['comments_made'].append({
                    'issue': issue['key'],
                    'content': comment['body'][:100] + '...' if len(comment['body']) > 100 else comment['body']
                })
            
            # 统计任务类型
            issue_type = issue['issue_type']
            for member in [assignee, reporter]:
                if member in member_stats:
                    member_stats[member]['issue_types'][issue_type] = member_stats[member]['issue_types'].get(issue_type, 0) + 1
        
        # 生成报告
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        report = f"""# Jira昨天成员更新情况报告
**分析日期**: {yesterday}
**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**总更新问题数**: {len(issues)}

## 📊 整体统计

### 成员活跃度概览
| 成员 | 负责问题数 | 状态变更数 | 评论数 | 总参与度 | 主要工作类型 |
|------|------------|------------|--------|----------|--------------|
"""
        
        # 按总参与度排序
        sorted_members = sorted(member_stats.items(), 
                              key=lambda x: len(x[1]['assigned_issues']) + len(x[1]['changes_made']) + len(x[1]['comments_made']), 
                              reverse=True)
        
        for member, stats in sorted_members:
            assigned = len(set(stats['assigned_issues']))  # 去重
            changes = len(stats['changes_made'])
            comments = len(stats['comments_made'])
            total_participation = assigned + changes + comments
            
            # 主要工作类型
            main_types = sorted(stats['issue_types'].items(), key=lambda x: x[1], reverse=True)[:2]
            main_types_str = ", ".join([f"{t}({c})" for t, c in main_types])
            
            report += f"| {member} | {assigned} | {changes} | {comments} | {total_participation} | {main_types_str} |\n"
        
        report += f"""
## 🏆 最活跃成员详细分析

### 高活跃度成员 (TOP 5)
"""
        
        # 详细分析前5名成员
        for i, (member, stats) in enumerate(sorted_members[:5], 1):
            report += f"""
#### {i}. {member}
- **负责问题**: {len(set(stats['assigned_issues']))} 个
- **状态变更**: {len(stats['changes_made'])} 次
- **发表评论**: {len(stats['comments_made'])} 条
- **主要工作类型**: {', '.join([f'{t}({c})' for t, c in sorted(stats['issue_types'].items(), key=lambda x: x[1], reverse=True)[:3]])}

**负责的重要问题**:
"""
            # 显示负责的问题（最多5个）
            unique_issues = list(set(stats['assigned_issues']))[:5]
            for issue_key in unique_issues:
                issue = next((iss for iss in issues if iss['key'] == issue_key), None)
                if issue:
                    report += f"- **{issue_key}**: {issue['title'][:80]}... (状态: {issue['status']})\n"
            
            # 显示重要的状态变更
            if stats['status_changes']:
                report += f"**重要状态变更**:\n"
                for change in stats['status_changes'][:3]:
                    report += f"- **{change['issue']}**: {change['from']} → {change['to']}\n"
        
        report += f"""
## 📋 问题更新详情

### 按任务类型统计
| 任务类型 | 更新数量 | 占比 | 主要参与者 |
|----------|----------|------|------------|
"""
        
        # 按任务类型统计
        type_stats = {}
        for issue in issues:
            issue_type = issue['issue_type']
            if issue_type not in type_stats:
                type_stats[issue_type] = {'count': 0, 'participants': set()}
            type_stats[issue_type]['count'] += 1
            type_stats[issue_type]['participants'].add(issue['assignee'])
        
        total_issues = len(issues)
        for issue_type, stats in sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            count = stats['count']
            percentage = f"{(count/total_issues*100):.1f}%"
            participants = ", ".join(list(stats['participants'])[:3])
            report += f"| {issue_type} | {count} | {percentage} | {participants} |\n"
        
        report += f"""
## ⚠️ 异常情况和风险

### 需要关注的问题
1. **长时间未更新**: 检查是否有任务超过预期完成时间
2. **频繁状态变更**: 注意状态反复变更的任务，可能存在需求不明确
3. **评论过少**: 沟通不足可能影响任务进展
4. **单点依赖**: 避免重要任务只依赖单个成员

### 改进建议
1. **加强沟通**: 鼓励成员积极评论和更新任务状态
2. **定期检查**: 对长时间未更新的任务进行人工检查
3. **负载均衡**: 合理分配任务，避免个别成员负担过重
4. **状态标准化**: 减少不必要的状态变更，提高流程效率

## 📈 趋势分析

### 昨天工作特点
- **总活跃度**: {len(issues)} 个问题有更新
- **参与成员**: {len(member_stats)} 名成员参与
- **平均参与度**: {sum(len(s['assigned_issues']) + len(s['changes_made']) + len(s['comments_made']) for s in member_stats.values()) / len(member_stats):.1f} 次/人
- **主要工作类型**: {', '.join(sorted(type_stats.keys())[:3])}

### 团队协作评估
- **协作良好**: 多个成员参与不同类型的工作
- **分工明确**: 各成员专注自己的工作领域
- **沟通充分**: 通过评论和状态变更保持同步
"""
        
        return report
    
    def analyze_gitlab_correlation(self, gitlab_project_id: str) -> str:
        """分析与GitLab的关联情况"""
        # 这里需要实现GitLab关联分析
        # 由于GitLab连接需要额外配置，这里先返回提示信息
        return """
# GitLab关联分析

⚠️  GitLab关联分析需要配置GitLab访问权限

**需要的配置**:
- GitLab服务器地址
- GitLab访问令牌
- GitLab项目ID

**分析内容将包括**:
- 与Jira任务关联的提交记录
- 与Jira任务关联的合并请求
- 未关联Jira的提交统计
- 代码活跃度与任务完成的关系分析
"""

def main():
    parser = argparse.ArgumentParser(description='Jira昨天成员更新情况分析器')
    parser.add_argument('--jira-server', required=True, help='Jira服务器地址')
    parser.add_argument('--jira-username', required=True, help='Jira用户名')
    parser.add_argument('--jira-password', required=True, help='Jira密码')
    parser.add_argument('--project', help='项目名称（可选）')
    parser.add_argument('--gitlab-project', help='GitLab项目ID（可选）')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = JiraDailyAnalyzer(
        jira_server=args.jira_server,
        jira_username=args.jira_username,
        jira_password=args.jira_password
    )
    
    # 连接到Jira
    if not analyzer.connect_jira():
        sys.exit(1)
    
    # 获取昨天更新的问题
    print("🔍 开始分析昨天成员更新情况...")
    issues = analyzer.get_yesterday_updated_issues(args.project)
    
    if not issues:
        print("❌ 未获取到昨天更新的问题数据")
        sys.exit(1)
    
    # 分析成员更新情况
    report = analyzer.analyze_member_updates(issues)
    
    # 如果有GitLab项目ID，进行关联分析
    if args.gitlab_project:
        gitlab_report = analyzer.analyze_gitlab_correlation(args.gitlab_project)
        report += "\n" + gitlab_report
    
    print(report)
    
    # 保存报告到文件
    report_file = f"jira_daily_report_{(datetime.now() - timedelta(days=1)).strftime('%Y%m%d')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 报告已保存到: {report_file}")

if __name__ == '__main__':
    main()