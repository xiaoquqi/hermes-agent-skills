#!/usr/bin/env python3
"""
Jira + GitLab 数据分析助手
严格遵循数据获取 → 分析 → 输出的流程
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import argparse

# 尝试导入必要的库
try:
    from jira import JIRA
    import gitlab
except ImportError as e:
    print(f"缺少必要的Python库: {e}")
    print("请运行: pip3 install jira python-gitlab pandas")
    sys.exit(1)

class JiraGitlabAnalyzer:
    def __init__(self, jira_server: str, jira_username: str, jira_password: str,
                 gitlab_server: str, gitlab_token: str):
        """初始化分析器"""
        self.jira_server = jira_server
        self.jira_username = jira_username
        self.jira_password = jira_password
        self.gitlab_server = gitlab_server
        self.gitlab_token = gitlab_token
        
        self.jira_client = None
        self.gitlab_client = None
        
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
    
    def connect_gitlab(self) -> bool:
        """连接GitLab服务器"""
        try:
            self.gitlab_client = gitlab.Gitlab(
                self.gitlab_server,
                private_token=self.gitlab_token
            )
            self.gitlab_client.auth()
            print(f"✅ 成功连接到GitLab: {self.gitlab_server}")
            return True
        except Exception as e:
            print(f"❌ 连接GitLab失败: {e}")
            return False
    
    def get_jira_issues(self, jql: str, max_results: int = 100) -> List[Dict]:
        """获取Jira问题数据"""
        if not self.jira_client:
            print("❌ Jira客户端未连接")
            return []
        
        try:
            issues = self.jira_client.search_issues(jql, maxResults=max_results)
            result = []
            
            for issue in issues:
                # 获取基本字段
                issue_data = {
                    'key': issue.key,
                    'title': issue.fields.summary,
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else '未分配',
                    'status': issue.fields.status.name,
                    'created': issue.fields.created,
                    'updated': issue.fields.updated,
                    'resolved': issue.fields.resolved if hasattr(issue.fields, 'resolved') else None,
                    'issue_type': issue.fields.issuetype.name,
                    'priority': issue.fields.priority.name if issue.fields.priority else '未设置',
                    'reporter': issue.fields.reporter.displayName if issue.fields.reporter else '未知',
                    'project': issue.fields.project.name,
                    'description': issue.fields.description or ''
                }
                
                # 获取变更历史
                try:
                    changelog = self.jira_client.issue(issue.key, expand='changelog').changelog
                    issue_data['change_history'] = [
                        {
                            'author': history.author.displayName if history.author else '未知',
                            'created': history.created,
                            'items': [
                                {
                                    'field': item.field,
                                    'from': item.fromString,
                                    'to': item.toString
                                }
                                for item in history.items
                            ]
                        }
                        for history in changelog.histories
                    ]
                except:
                    issue_data['change_history'] = []
                
                # 获取评论
                try:
                    comments = self.jira_client.comments(issue.key)
                    issue_data['comments'] = [
                        {
                            'author': comment.author.displayName,
                            'created': comment.created,
                            'body': comment.body
                        }
                        for comment in comments
                    ]
                except:
                    issue_data['comments'] = []
                
                result.append(issue_data)
            
            print(f"✅ 成功获取 {len(result)} 个Jira问题")
            return result
            
        except Exception as e:
            print(f"❌ 获取Jira问题失败: {e}")
            return []
    
    def get_gitlab_commits(self, project_id: str, since: str = None) -> List[Dict]:
        """获取GitLab提交记录"""
        if not self.gitlab_client:
            print("❌ GitLab客户端未连接")
            return []
        
        try:
            project = self.gitlab_client.projects.get(project_id)
            commits = project.commits.list(all=True)
            
            result = []
            for commit in commits:
                commit_data = {
                    'id': commit.id,
                    'short_id': commit.short_id,
                    'title': commit.title,
                    'message': commit.message,
                    'author_name': commit.author_name,
                    'author_email': commit.author_email,
                    'created_at': commit.created_at,
                    'jira_keys': self._extract_jira_keys(commit.title + ' ' + commit.message)
                }
                result.append(commit_data)
            
            print(f"✅ 成功获取 {len(result)} 条GitLab提交记录")
            return result
            
        except Exception as e:
            print(f"❌ 获取GitLab提交失败: {e}")
            return []
    
    def get_gitlab_merge_requests(self, project_id: str) -> List[Dict]:
        """获取GitLab合并请求"""
        if not self.gitlab_client:
            print("❌ GitLab客户端未连接")
            return []
        
        try:
            project = self.gitlab_client.projects.get(project_id)
            mrs = project.mergerequests.list(all=True)
            
            result = []
            for mr in mrs:
                mr_data = {
                    'id': mr.id,
                    'title': mr.title,
                    'state': mr.state,
                    'author': mr.author['name'] if 'name' in mr.author else '未知',
                    'created_at': mr.created_at,
                    'updated_at': mr.updated_at,
                    'merged_at': mr.merged_at,
                    'jira_keys': self._extract_jira_keys(mr.title + ' ' + (mr.description or ''))
                }
                result.append(mr_data)
            
            print(f"✅ 成功获取 {len(result)} 个GitLab合并请求")
            return result
            
        except Exception as e:
            print(f"❌ 获取GitLab合并请求失败: {e}")
            return []
    
    def _extract_jira_keys(self, text: str) -> List[str]:
        """从文本中提取Jira问题键"""
        import re
        # 匹配Jira问题键格式: PROJ-123
        pattern = r'\b[A-Z]{2,10}-\d+\b'
        return list(set(re.findall(pattern, text.upper())))
    
    def analyze_current_sprint_unfinished(self, board_id: int) -> str:
        """分析当前Sprint未完成任务"""
        print("📊 分析当前Sprint未完成任务...")
        
        try:
            # 获取当前活跃的Sprint
            sprints = self.jira_client.sprints(board_id, state='active')
            if not sprints:
                return "❌ 没有找到活跃的Sprint"
            
            current_sprint = sprints[0]
            sprint_id = current_sprint.id
            sprint_name = current_sprint.name
            
            # 获取Sprint中未完成的任务
            jql = f"sprint = {sprint_id} AND status NOT IN (Done, Closed, Resolved)"
            unfinished_issues = self.get_jira_issues(jql, max_results=200)
            
            if not unfinished_issues:
                return "✅ 当前Sprint所有任务都已完成"
            
            # 生成报告
            report = f"""# 当前Sprint未完成任务报告
**Sprint名称**: {sprint_name}
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**未完成任务数**: {len(unfinished_issues)}

## 📋 未完成任务列表

| 任务键 | 标题 | 负责人 | 状态 | 优先级 | 任务类型 | 最后更新 |
|--------|------|--------|------|--------|----------|----------|
"""
            
            for issue in unfinished_issues:
                updated_date = issue['updated'][:10] if issue['updated'] else '未知'
                report += f"| {issue['key']} | {issue['title'][:50]}... | {issue['assignee']} | {issue['status']} | {issue['priority']} | {issue['issue_type']} | {updated_date} |\n"
            
            # 风险分析
            old_issues = [issue for issue in unfinished_issues if self._days_since_update(issue['updated']) > 3]
            blocked_issues = [issue for issue in unfinished_issues if '阻塞' in issue['title'] or 'blocked' in issue['title'].lower()]
            
            report += f"""
## ⚠️ 风险分析

### 长时间未更新任务 ({len(old_issues)}个)
"""
            if old_issues:
                for issue in old_issues[:5]:  # 只显示前5个
                    days_old = self._days_since_update(issue['updated'])
                    report += f"- **{issue['key']}**: {issue['title'][:60]}... (未更新 {days_old} 天，负责人: {issue['assignee']})\n"
            else:
                report += "- ✅ 所有未完成任务都在3天内有更新\n"
            
            report += f"""
### 潜在阻塞任务 ({len(blocked_issues)}个)
"""
            if blocked_issues:
                for issue in blocked_issues:
                    report += f"- **{issue['key']}**: {issue['title']} (负责人: {issue['assignee']})\n"
            else:
                report += "- ✅ 未发现明显阻塞的任务\n"
            
            return report
            
        except Exception as e:
            return f"❌ 分析当前Sprint失败: {e}"
    
    def analyze_long_unupdated_tasks(self, days: int = 3, project: str = None) -> str:
        """分析长时间未更新的任务"""
        print(f"📊 分析{days}天未更新的任务...")
        
        try:
            # 构建JQL查询
            jql = f"status NOT IN (Done, Closed, Resolved) AND updated <= -{days}d"
            if project:
                jql += f" AND project = '{project}'"
            
            old_issues = self.get_jira_issues(jql, max_results=100)
            
            if not old_issues:
                return f"✅ 未找到{days}天未更新的任务"
            
            # 按未更新天数分组
            very_old = [issue for issue in old_issues if self._days_since_update(issue['updated']) >= days * 2]
            
            report = f"""# 长时间未更新任务分析报告
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**未更新天数**: ≥{days}天
**总任务数**: {len(old_issues)}
**严重超时** (≥{days*2}天): {len(very_old)}

## 📊 按未更新天数统计

| 未更新天数 | 任务数量 | 占比 |
|------------|----------|------|
"""
            
            # 统计分布
            distribution = {}
            for issue in old_issues:
                days_old = self._days_since_update(issue['updated'])
                range_key = f"{days_old//5*5}-{(days_old//5+1)*5-1}天"
                distribution[range_key] = distribution.get(range_key, 0) + 1
            
            total = len(old_issues)
            for range_key in sorted(distribution.keys(), key=lambda x: int(x.split('-')[0])):
                count = distribution[range_key]
                percentage = f"{(count/total*100):.1f}%"
                report += f"| {range_key} | {count} | {percentage} |\n"
            
            report += f"""
## 📋 最长时间未更新任务 (TOP 10)

| 任务键 | 标题 | 负责人 | 状态 | 未更新天数 | 风险等级 |
|--------|------|--------|------|------------|----------|
"""
            
            # 按未更新天数排序
            sorted_issues = sorted(old_issues, key=lambda x: self._days_since_update(x['updated']), reverse=True)
            
            for issue in sorted_issues[:10]:
                days_old = self._days_since_update(issue['updated'])
                risk_level = "🔴 高风险" if days_old >= days * 2 else "🟡 中风险"
                report += f"| {issue['key']} | {issue['title'][:50]}... | {issue['assignee']} | {issue['status']} | {days_old}天 | {risk_level} |\n"
            
            report += f"""
## ⚠️ 潜在风险分析

### 主要风险点
1. **任务遗忘**: 长时间未更新可能表明任务被遗忘或优先级降低
2. **阻塞未解决**: 可能存在技术或资源阻塞未及时处理
3. **资源分配问题**: 负责人可能工作负载过重或任务分配不合理

### 建议措施
1. **立即检查**: 对高风险任务进行人工检查，确认是否需要更新状态
2. **重新分配**: 如负责人工作负载过重，考虑重新分配任务
3. **优先级调整**: 对不再重要的任务降低优先级或关闭
4. **定期回顾**: 建立定期检查机制，避免任务长期停滞
"""
            
            return report
            
        except Exception as e:
            return f"❌ 分析长时间未更新任务失败: {e}"
    
    def analyze_previous_day_completion(self) -> str:
        """分析前一个工作日任务完成情况"""
        print("📊 分析前一个工作日任务完成情况...")
        
        try:
            # 计算前一个工作日（跳过周末）
            today = datetime.now()
            prev_workday = today - timedelta(days=1)
            if prev_workday.weekday() >= 5:  # 周六或周日
                prev_workday = prev_workday - timedelta(days=prev_workday.weekday() - 4)  # 回到周五
            
            start_date = prev_workday.strftime('%Y-%m-%d')
            end_date = (prev_workday + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 获取前一天完成的任务
            jql = f"status CHANGED TO (Done, Closed, Resolved) DURING ('{start_date}', '{end_date}')"
            completed_issues = self.get_jira_issues(jql, max_results=100)
            
            # 获取前一天更新的任务（包括新创建和状态变更）
            jql_updated = f"updated >= '{start_date}' AND updated < '{end_date}'"
            updated_issues = self.get_jira_issues(jql_updated, max_results=100)
            
            report = f"""# 前一个工作日任务完成情况报告
**分析日期**: {prev_workday.strftime('%Y-%m-%d')} ({self._get_weekday_name(prev_workday.weekday())})
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**完成任务数**: {len(completed_issues)}
**总更新任务数**: {len(updated_issues)}

## 📊 整体完成情况

### 任务完成统计
- ✅ **完成任务**: {len(completed_issues)} 个
- 🔄 **任务更新**: {len(updated_issues)} 个
- 📈 **完成率**: {(len(completed_issues)/len(updated_issues)*100):.1f}% (相对于更新任务)

## 👥 按成员统计完成情况

| 成员 | 完成任务数 | 负责总任务数 | 完成率 | 主要任务类型 |
|------|------------|--------------|--------|--------------|
"""
            
            # 按成员统计
            member_stats = {}
            for issue in completed_issues:
                assignee = issue['assignee']
                if assignee not in member_stats:
                    member_stats[assignee] = {'completed': 0, 'total': 0, 'types': {}}
                member_stats[assignee]['completed'] += 1
                issue_type = issue['issue_type']
                member_stats[assignee]['types'][issue_type] = member_stats[assignee]['types'].get(issue_type, 0) + 1
            
            # 统计总任务数
            for issue in updated_issues:
                assignee = issue['assignee']
                if assignee not in member_stats:
                    member_stats[assignee] = {'completed': 0, 'total': 0, 'types': {}}
                member_stats[assignee]['total'] += 1
            
            # 生成表格
            for member, stats in sorted(member_stats.items(), key=lambda x: x[1]['completed'], reverse=True):
                if stats['total'] > 0:
                    completion_rate = f"{(stats['completed']/stats['total']*100):.1f}%"
                else:
                    completion_rate = "0%"
                
                main_types = ", ".join([f"{t}({c})" for t, c in stats['types'].items()][:2])
                report += f"| {member} | {stats['completed']} | {stats['total']} | {completion_rate} | {main_types} |\n"
            
            report += f"""
## 📋 完成的任务详情 (TOP 10)

| 任务键 | 标题 | 负责人 | 任务类型 | 优先级 | 完成时间 |
|--------|------|--------|----------|--------|----------|
"""
            
            # 显示完成的任务详情
            for issue in completed_issues[:10]:
                resolved_time = issue.get('resolved', issue['updated'])[:16] if issue.get('resolved') or issue['updated'] else '未知'
                report += f"| {issue['key']} | {issue['title'][:50]}... | {issue['assignee']} | {issue['issue_type']} | {issue['priority']} | {resolved_time} |\n"
            
            # 延迟任务分析
            delayed_issues = [issue for issue in updated_issues if issue['status'] not in ['Done', 'Closed', 'Resolved']]
            
            report += f"""
## ⏰ 延迟任务分析

### 未完成任务
- **延迟任务数**: {len(delayed_issues)} 个
- **主要状态**: {', '.join(set([issue['status'] for issue in delayed_issues[:10]]))}

### 效率分析
- **平均完成时间**: 需进一步分析任务创建到完成的时间
- **最高效成员**: {max(member_stats.items(), key=lambda x: x[1]['completed'])[0] if member_stats else '无'}
- **任务类型分布**: {', '.join(set([issue['issue_type'] for issue in completed_issues]))}

### 改进建议
1. **资源分配**: 对完成率低的成员提供额外支持
2. **优先级管理**: 确保高优先级任务优先完成
3. **阻塞处理**: 及时识别和解决任务阻塞
4. **经验分享**: 让高完成率成员分享工作经验
"""
            
            return report
            
        except Exception as e:
            return f"❌ 分析前一个工作日完成情况失败: {e}"
    
    def _days_since_update(self, updated_date: str) -> int:
        """计算自更新以来的天数"""
        if not updated_date:
            return 0
        try:
            updated = datetime.strptime(updated_date[:19], '%Y-%m-%dT%H:%M:%S')
            return (datetime.now() - updated).days
        except:
            return 0
    
    def _get_weekday_name(self, weekday: int) -> str:
        """获取星期几的中文名称"""
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return weekdays[weekday]

def main():
    parser = argparse.ArgumentParser(description='Jira + GitLab 数据分析助手')
    parser.add_argument('--jira-server', required=True, help='Jira服务器地址')
    parser.add_argument('--jira-username', required=True, help='Jira用户名')
    parser.add_argument('--jira-password', required=True, help='Jira密码')
    parser.add_argument('--gitlab-server', required=True, help='GitLab服务器地址')
    parser.add_argument('--gitlab-token', required=True, help='GitLab访问令牌')
    parser.add_argument('--analysis-type', required=True, 
                       choices=['sprint-unfinished', 'long-unupdated', 'prev-day-completion'],
                       help='分析类型')
    parser.add_argument('--board-id', type=int, help='Jira看板ID（分析Sprint时需要）')
    parser.add_argument('--days', type=int, default=3, help='未更新天数阈值')
    parser.add_argument('--project', help='项目名称')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = JiraGitlabAnalyzer(
        jira_server=args.jira_server,
        jira_username=args.jira_username,
        jira_password=args.jira_password,
        gitlab_server=args.gitlab_server,
        gitlab_token=args.gitlab_token
    )
    
    # 连接到服务
    if not analyzer.connect_jira():
        sys.exit(1)
    
    if not analyzer.connect_gitlab():
        print("⚠️ GitLab连接失败，继续仅使用Jira数据进行分析")
    
    # 执行分析
    if args.analysis_type == 'sprint-unfinished':
        if not args.board_id:
            print("❌ 分析Sprint需要指定--board-id")
            sys.exit(1)
        result = analyzer.analyze_current_sprint_unfinished(args.board_id)
    elif args.analysis_type == 'long-unupdated':
        result = analyzer.analyze_long_unupdated_tasks(args.days, args.project)
    elif args.analysis_type == 'prev-day-completion':
        result = analyzer.analyze_previous_day_completion()
    else:
        print(f"❌ 未知的分析类型: {args.analysis_type}")
        sys.exit(1)
    
    print(result)

if __name__ == '__main__':
    main()