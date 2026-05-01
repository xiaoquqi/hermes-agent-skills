#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA 报告生成模块
职责：接收分析结果 JSON，渲染成人类可读的文本/微信格式报告
对外暴露：CLI + Python function
"""
import sys, json, argparse
from datetime import datetime


SAT_ICON = {'高': '🟢', '中': '🟡', '低': '🔴'}


def render_verdict_icon(verdict: str) -> str:
    if not verdict:
        return '⚪'
    v = verdict.lower()
    if any(kw in v for kw in ['增加', '不足', '过载', '缺少']):
        return '💡'
    if any(kw in v for kw in ['丰富', '充足', '正常', '饱满']):
        return '✅'
    if any(kw in v for kw in ['无', '0', 'empty']):
        return '⚪'
    return '💬'


def guess_area_inline(summary: str) -> str:
    """简单领域标签"""
    s = summary.lower()
    if any(k in s for k in ['linux', 'debian', 'ubuntu', 'agent']):
        return 'Linux Agent'
    if any(k in s for k in ['aws', 'amazon', 'ec2']):
        return 'AWS'
    if any(k in s for k in ['xhere']):
        return 'Xhere'
    if any(k in s for k in ['vmware', 'esxi']):
        return 'VMware'
    if any(k in s for k in ['块存储', 'volume', 'storage']):
        return '块存储'
    if any(k in s for k in ['前端', 'vue', 'react']):
        return '前端'
    if any(k in s for k in ['ci-cd', 'pipeline']):
        return 'CI-CD'
    if any(k in s for k in ['错误', 'bug', '报错']):
        return '错误优化'
    if any(k in s for k in ['阿里', 'aliyun']):
        return '阿里云'
    return '其他'


def truncate(s: str, max_len: int = 42) -> str:
    return s[:max_len] + ('...' if len(s) > max_len else '')


def render_summary(summary: dict) -> list:
    """渲染 Part 1: 总体概览"""
    lines = []
    area_dist = summary.get('area_distribution', {})
    area_str = '  '.join([f"{k}({v})" for k, v in sorted(area_dist.items(), key=lambda x: -x[1])]) or '无'

    lines.append(f"\n{'='*60}")
    lines.append(f"  JIRA 每日汇总  {summary.get('date', '')}")
    lines.append(f"{'='*60}")
    lines.append(f"\n📌 新建问题（{summary.get('created_count', 0)} 个）")
    lines.append(f"   领域分布: {area_str}")

    lines.append(f"\n✅ 已完成问题（{summary.get('done_count', 0)} 个）")
    lines.append(f"\n📊 整体统计")
    lines.append(f"   新建 {summary.get('created_count', 0)}  |  "
                 f"已完成 {summary.get('done_count', 0)}  |  "
                 f"有更新 {summary.get('updated_count', 0)}  |  "
                 f"涉及人员 {summary.get('person_count', 0)}")
    return lines


def render_person(person: dict) -> list:
    """渲染 Part 2: 单人详情"""
    lines = []
    name = person.get('name', '')
    sat = person.get('saturation', '低')
    verdict = person.get('verdict', '')
    reason = person.get('reason', '')
    concern = person.get('concern', '')

    new_c = person.get('new_count', 0)
    done_c = person.get('done_count', 0)
    my_comment_c = person.get('my_comment_count', 0)
    my_worklog_c = person.get('my_worklog_count', 0)

    lines.append(f"\n{'─'*60}")
    lines.append(f"  👤 {name}")
    lines.append(f"  📈 新建 {new_c}  |  已完成 {done_c}  |  评论 {my_comment_c}  |  工时 {my_worklog_c}")
    lines.append(f"  工作饱和度 {SAT_ICON.get(sat, '⚪')} {sat}  |  {render_verdict_icon(verdict)} {verdict}")

    if reason:
        lines.append(f"  📝 {reason}")

    if concern:
        lines.append(f"  🔍 {concern}")

    issues = person.get('issues', [])

    # 列出新建
    new_issues = [i for i in issues if i.get('_is_new_today')]
    if new_issues:
        lines.append(f"\n  🆕 新建")
        for i in new_issues[:5]:
            area = guess_area_inline(i.get('summary', ''))
            lines.append(f"     {i['key']} [{area}] {truncate(i['summary'])}")

    # 列出已完成
    done_issues = [i for i in issues if i.get('status') == 'Done']
    if done_issues:
        lines.append(f"\n  ✅ 已完成")
        for i in done_issues[:5]:
            lines.append(f"     {i['key']} | {truncate(i['summary'])}")

    # 列出有评论更新的
    active_issues = [i for i in issues
                     if i.get('comment_count', 0) > 0 and i.get('status') != 'Done']
    if active_issues:
        lines.append(f"\n  💬 有评论更新")
        for i in active_issues[:5]:
            comments = i.get('comments', [])
            preview = ' | '.join([c['body'][:25] for c in comments[:2]])
            lines.append(f"     {i['key']}({i['comment_count']}条) {truncate(preview)}")

    return lines


def render_report(analysis: dict) -> str:
    """生成完整报告"""
    lines = []

    # Part 1: 总体概览
    summary_data = {
        'date': analysis.get('date', ''),
        'created_count': analysis.get('summary', {}).get('created_count', 0),
        'done_count': analysis.get('summary', {}).get('done_count', 0),
        'updated_count': analysis.get('summary', {}).get('updated_count', 0),
        'person_count': analysis.get('summary', {}).get('person_count', 0),
        'area_distribution': analysis.get('summary', {}).get('area_distribution', {}),
    }

    # 打印新建的 issue 列表
    new_by_person = analysis.get('new_issues_by_person', {})
    if new_by_person:
        for person_name, issues in sorted(new_by_person.items(), key=lambda x: -len(x[1])):
            for i in issues:
                area = guess_area_inline(i.get('summary', ''))
                lines.append(f"   + {i['key']} | {i.get('issuetype','?')} | {person_name} | [{area}] {truncate(i['summary'])}")

    # 打印已完成的 issue 列表
    person_results = analysis.get('person_results', [])
    for person in person_results:
        done_issues = [i for i in person.get('issues', []) if i.get('status') == 'Done']
        if done_issues:
            for i in done_issues:
                lines.append(f"   ✓ {i['key']} | {person['name']} | {truncate(i['summary'])}")

    lines += render_summary(summary_data)

    # Part 2: 按人拆解
    lines.append(f"\n{'='*60}")
    lines.append(f"  按人拆解")
    lines.append(f"{'='*60}")

    for person in person_results:
        lines += render_person(person)

    lines.append(f"\n{'='*60}")
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"{'='*60}")

    return '\n'.join(lines)


def render_new_issues_list(analysis: dict) -> list:
    """渲染 Part 1 的新建 issue 明细"""
    lines = []
    summary = analysis.get('summary', {})
    area_dist = summary.get('area_distribution', {})
    area_str = '  '.join([f"{k}({v})" for k, v in sorted(area_dist.items(), key=lambda x: -x[1])]) or '无'

    lines.append(f"\n{'='*60}")
    lines.append(f"  JIRA 每日汇总  {analysis.get('date', '')}")
    lines.append(f"{'='*60}")

    lines.append(f"\n📌 新建问题（{summary.get('created_count', 0)} 个）")
    if area_dist:
        lines.append(f"   领域分布: {area_str}")

    new_by_person = analysis.get('new_issues_by_person', {})
    for person_name, issues in sorted(new_by_person.items(), key=lambda x: -len(x[1])):
        lines.append(f"   {person_name}:")
        for i in issues:
            area = guess_area_inline(i.get('summary', ''))
            lines.append(f"     + {i['key']} | {i.get('issuetype','?')} | [{area}] {truncate(i['summary'])}")

    # 已完成列表
    done_list = []
    for person in analysis.get('person_results', []):
        for i in person.get('issues', []):
            if i.get('status') == 'Done':
                done_list.append((person['name'], i))

    lines.append(f"\n✅ 已完成问题（{summary.get('done_count', 0)} 个）")
    for person_name, i in done_list[:10]:
        lines.append(f"   ✓ {i['key']} | {person_name} | {truncate(i['summary'])}")
    if len(done_list) > 10:
        lines.append(f"   ... 还有 {len(done_list)-10} 个")

    lines.append(f"\n📊 整体统计")
    lines.append(f"   新建 {summary.get('created_count', 0)}  |  "
                 f"已完成 {summary.get('done_count', 0)}  |  "
                 f"有更新 {summary.get('updated_count', 0)}  |  "
                 f"涉及人员 {summary.get('person_count', 0)}")

    return lines


def render_full_report(analysis: dict) -> str:
    """完整两段式报告"""
    lines = []

    # ── Part 1 ──
    lines += render_new_issues_list(analysis)

    # ── Part 2 ──
    lines.append(f"\n{'='*60}")
    lines.append(f"  按人拆解")
    lines.append(f"{'='*60}")

    person_results = analysis.get('person_results', [])
    for person in person_results:
        lines += render_person(person)

    lines.append(f"\n{'='*60}")
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"{'='*60}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='JIRA Report Generator')
    parser.add_argument('--json', help='分析结果 JSON 文件路径')
    parser.add_argument('--format', choices=['full', 'summary'], default='full')
    parser.add_argument('--quiet', action='store_true', help='只输出报告正文，不输出调试信息')
    args = parser.parse_args()

    if args.json:
        with open(args.json) as f:
            payload = json.load(f)
    else:
        payload = json.load(sys.stdin)

    analysis = payload.get('analysis', payload)

    if args.format == 'summary':
        report = '\n'.join(render_new_issues_list(analysis))
    else:
        report = render_full_report(analysis)

    print(report)


if __name__ == '__main__':
    main()
