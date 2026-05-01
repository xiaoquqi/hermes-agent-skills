#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA 分析模块 v2
基于 Markdown 缓存数据分析
核心原则：
  - GitLab 评论是正常流程，代表员工按规范提交了代码
  - 评论内容 > 评论数量，要看实际在做什么
  - 完成状态是最重要的产出
  - 评价标准从严
"""
import sys, json, re
from collections import defaultdict

GITLAB_BOT_NAMES = {'gitlab', 'girabot', 'jirabot', 'gbot', 'bot', 'system', ''}

def parse_md(path: str) -> list:
    """解析 JIRA Markdown 缓存 - 直接读取原始结构化数据"""
    with open(path) as f:
        content = f.read()

    issues = []

    # 按 ### [KEY] 切分 blocks
    parts = re.split(r'\n(?=### \[)', content)
    for part in parts:
        part = part.strip()
        if not part or part.startswith('# '):
            continue

        # 解析 key
        m = re.match(r'### \[([^\]]+)\]', part)
        if not m:
            continue
        key = m.group(1).strip()
        is_new = '🆕' in part
        is_done = '✅' in part

        # 解析摘要（### [KEY] 后的第一行非列表行）
        summary = ''
        lines = part.split('\n')
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('- '):
                continue
            if line.startswith('**评论'):
                continue
            if line.startswith('- **'):
                continue
            if line.startswith('#'):
                continue
            if line:
                summary = line
                break

        # 解析元数据行
        status = ''
        issuetype = ''
        priority = ''
        assignee = ''
        reporter = ''
        created = ''
        updated = ''
        comments = []

        meta_block = '\n'.join(lines)
        # 类型
        t = re.search(r'类型:\s*([^\s|]+)', meta_block)
        if t: issuetype = t.group(1).strip()
        # 状态
        s = re.search(r'状态:\s*([^\s|]+)', meta_block)
        if s: status = s.group(1).strip()
        # 优先级
        p = re.search(r'优先级:\s*([^\s|]+)', meta_block)
        if p: priority = p.group(1).strip()
        # 负责人
        a = re.search(r'负责人:\s*([^\s|]+)', meta_block)
        if a: assignee = a.group(1).strip()
        # 创建者
        rp = re.search(r'创建者:\s*([^\s|]+)', meta_block)
        if rp: reporter = rp.group(1).strip()
        # 创建时间
        c = re.search(r'创建时间:\s*([\d-]+)', meta_block)
        if c: created = c.group(1).strip()
        # 更新时间
        u = re.search(r'更新时间:\s*([\d-]+)', meta_block)
        if u: updated = u.group(1).strip()

        # 解析评论
        for line in lines:
            line = line.strip()
            cm = re.match(r'- \*\*([^*]+)\*\* \(([^)]+)\):(.+)', line)
            if cm:
                author = cm.group(1).strip()
                date = cm.group(2).strip()
                body = cm.group(3).strip()
                comments.append({'author': author, 'date': date, 'body': body})

        issues.append({
            'key': key,
            'summary': summary,
            'status': status,
            'issuetype': issuetype,
            'priority': priority,
            'assignee': assignee,
            'reporter': reporter,
            'created': created,
            'updated': updated,
            'is_new_today': is_new or '2026-04-15' in created,
            'is_done': is_done or status == 'Done',
            'comments': comments,
        })

    return issues




def summarize_work(issues: list) -> dict:
    """
    按人汇总工作
    评分标准（从高到低）：
      - 完成: 5分/个
      - 新建且本人是创建者: 3分/个
      - 本人有真实评论（不含图片only）: 2分/个issue
      - 本人有图片评论: 1分/个issue
      - GitLab提交记录: 1分/个issue
    阈值：≥8 高，≥3 中，<3 低
    """
    by_person = defaultdict(lambda: {
        'done': [], 'new': [], 'in_progress': [], 'commented': [],
        'gitlab': [], 'my_comments': [],
    })

    for issue in issues:
        assignee = issue.get('assignee', '').strip()
        if not assignee:
            assignee = '未分配'
        p = by_person[assignee]

        if issue.get('is_done'):
            p['done'].append(issue)
        elif issue.get('is_new_today'):
            p['new'].append(issue)
        else:
            p['in_progress'].append(issue)

        # 本人的评论
        my_cmts = [c for c in issue.get('comments', [])
                   if c.get('author', '').lower().strip() not in GITLAB_BOT_NAMES
                   and c.get('author', '') == assignee]
        if my_cmts:
            p['my_comments'].append((issue, my_cmts))

        # GitLab 的提交
        gl_cmts = [c for c in issue.get('comments', [])
                   if c.get('author', '').lower().strip() in GITLAB_BOT_NAMES
                   and 'mentioned this issue' in c.get('body', '').lower()]
        if gl_cmts:
            p['gitlab'].append((issue, gl_cmts))

    # 计算评分
    results = {}
    for name, p in by_person.items():
        done_c = len(p['done'])
        new_c = len(p['new'])
        commented_c = len(p['my_comments'])
        gitlab_c = len(p['gitlab'])

        # 评分
        score = done_c * 5 + new_c * 3 + commented_c * 2 + gitlab_c * 1

        if score >= 8:
            level = '高'
        elif score >= 3:
            level = '中'
        else:
            level = '低'

        results[name] = {
            'done': p['done'],
            'new': p['new'],
            'in_progress': p['in_progress'],
            'my_comments': p['my_comments'],
            'gitlab': p['gitlab'],
            'score': score,
            'level': level,
            'done_c': done_c,
            'new_c': new_c,
            'commented_c': commented_c,
            'gitlab_c': gitlab_c,
        }
    return results


def render_report(data: dict, date_str='2026-04-15'):
    """生成人类可读的完整报告"""
    lines = []
    all_done = []
    all_new = []
    for name, d in data.items():
        all_done.extend(d['done'])
        all_new.extend(d['new'])

    # 标题
    lines.append(f"{'='*60}")
    lines.append(f"  JIRA 每日汇总  {date_str}")
    lines.append(f"{'='*60}")

    # 新建问题
    lines.append(f"\n📌 新建问题（共 {len(all_new)} 个）")
    if all_new:
        for issue in all_new:
            lines.append(f"  + {issue['key']} | {issue.get('issuetype','?')} | {issue.get('assignee','?')} | {trunc(issue.get('summary',''))}")
    else:
        lines.append("  无新建问题")

    # 已完成问题
    lines.append(f"\n✅ 已完成问题（共 {len(all_done)} 个）")
    if all_done:
        for issue in all_done:
            lines.append(f"  ✓ {issue['key']} | {issue.get('assignee','?')} | {trunc(issue.get('summary',''))}")
    else:
        lines.append("  无已完成问题")

    # 整体统计
    total_issues = sum(len(d['done']) + len(d['new']) + len(d['in_progress']) for d in data.values())
    lines.append(f"\n📊 整体统计")
    lines.append(f"  新建 {len(all_new)}  |  已完成 {len(all_done)}  |  进行中 {total_issues - len(all_new) - len(all_done)}  |  涉及人员 {len(data)}")

    # 按人拆解
    lines.append(f"\n{'='*60}")
    lines.append(f"  按人拆解（评分标准：完成5分/个、新建3分/个、本人评论2分/issue、GitLab提交1分/issue）")
    lines.append(f"{'='*60}")

    # 按分数排序
    for name, d in sorted(data.items(), key=lambda x: -x[1]['score']):
        lines.append(render_person(name, d))

    from datetime import datetime as dt
    lines.append(f"\n{'='*60}")
    lines.append(f"  生成时间: {dt.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"{'='*60}")

    return '\n'.join(lines)


def render_person(name: str, d: dict) -> list:
    lines = []
    score = d['score']
    level = d['level']
    icon = {'高': '🟢', '中': '🟡', '低': '🔴'}.get(level, '⚪')

    lines.append(f"\n{'─'*60}")
    lines.append(f"  👤 {name}")
    lines.append(f"  📈 完成 {d['done_c']}  |  新建 {d['new_c']}  |  本人评论 {d['commented_c']}个issue  |  GitLab提交 {d['gitlab_c']}个issue")
    lines.append(f"  工作饱和度 {icon} {level}  |  综合评分 {score}")

    # 完成列表
    if d['done']:
        lines.append(f"\n  ✅ 已完成（{d['done_c']}个）")
        for issue in d['done']:
            lines.append(f"     ✓ {issue['key']} | {trunc(issue.get('summary',''))}")

    # 新建列表
    if d['new']:
        lines.append(f"\n  🆕 新建（{d['new_c']}个）")
        for issue in d['new']:
            lines.append(f"     + {issue['key']} | {trunc(issue.get('summary',''))}")

    # 进行中的列表
    if d['in_progress']:
        lines.append(f"\n  🔄 进行中（{len(d['in_progress'])}个）")
        for issue in d['in_progress'][:5]:
            lines.append(f"     ▶ {issue['key']} | {trunc(issue.get('summary',''))}")

    # 本人评论内容
    if d['my_comments']:
        lines.append(f"\n  💬 本人评论摘要")
        for issue, cmts in d['my_comments'][:5]:
            bodies = [c['body'] for c in cmts if len(c['body']) > 5]
            if bodies:
                preview = ' | '.join([trunc(b, 50) for b in bodies[:2]])
                lines.append(f"     {issue['key']}: {preview}")

    # GitLab 提交（说明有代码贡献）
    if d['gitlab']:
        lines.append(f"\n  🔧 GitLab 有代码提交（{d['gitlab_c']}个issue）")
        for issue, cmts in d['gitlab'][:5]:
            lines.append(f"     {issue['key']} | {trunc(issue.get('summary',''))}")

    return '\n'.join(lines)


def trunc(s: str, max_len=42) -> str:
    s = s.strip()
    return s[:max_len] + ('...' if len(s) > max_len else '')




def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('md_file')
    args = parser.parse_args()

    issues = parse_md(args.md_file)
    data = summarize_work(issues)
    report = render_report(data)
    print(report)


if __name__ == '__main__':
    main()
