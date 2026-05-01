#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA 数据抓取 → Markdown 缓存
阶段1：只负责把数据拉下来，存成结构化 Markdown
"""
import os, sys, json, argparse
from datetime import datetime, timedelta

JIRA_URL  = os.environ.get('JIRA_URL',      'http://office.oneprocloud.com.cn:9005')
JIRA_USER = os.environ.get('JIRA_USERNAME', 'sunqi')
JIRA_PASS = os.environ.get('JIRA_PASSWORD',  'sunqi1358')
CACHE_DIR = os.path.expanduser('~/.hermes/jira-cache/')


def prev_workday(d: datetime) -> datetime:
    d = d - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def parse_date(date_arg):
    today = datetime.now()
    if date_arg in (None, '', 'today'):
        return prev_workday(today).strftime('%Y-%m-%d')
    elif date_arg == 'yesterday':
        return prev_workday(today).strftime('%Y-%m-%d')
    return date_arg


def get_jira_client():
    from atlassian import Jira
    return Jira(url=JIRA_URL, username=JIRA_USER, password=JIRA_PASS, cloud=False, timeout=30)


def strip_html(text: str) -> str:
    import re
    return re.sub(r'<[^>]+>', '', text).strip()


BOT_NAMES = {'girabot', 'girabot ', 'jirabot', 'gbot', 'bot', 'system', ''}


def get_comments(client, issue_key: str) -> list:
    try:
        raw = client.issue_get_comments(issue_key)
        if isinstance(raw, dict):
            return raw.get('comments', []) or []
        elif isinstance(raw, list):
            return raw
    except Exception:
        pass
    return []


def get_worklogs(client, issue_key: str) -> list:
    try:
        raw = client.get_issue_worklog(issue_key)
        if isinstance(raw, dict):
            return raw.get('worklogs', []) or []
        elif isinstance(raw, list):
            return raw
    except Exception:
        pass
    return []


def fetch_and_cache(date_str: str, output_path: str):
    client = get_jira_client()

    # 查询该日期新建的 issue
    jql_created = (
        f'created >= "{date_str}" AND created <= "{date_str} 23:59" '
        'ORDER BY created DESC'
    )
    created_raw = client.jql(jql_created, limit=200,
        fields='summary,status,assignee,reporter,created,updated,issuetype,priority,resolution')
    created_issues = created_raw.get('issues', []) if isinstance(created_raw, dict) else []

    # 查询该日期更新的 issue
    jql_updated = (
        f'updated >= "{date_str}" AND updated <= "{date_str} 23:59" '
        'ORDER BY updated DESC'
    )
    updated_raw = client.jql(jql_updated, limit=200,
        fields='summary,status,assignee,reporter,created,updated,issuetype,priority,resolution')
    updated_issues = updated_raw.get('issues', []) if isinstance(updated_raw, dict) else []

    # 过滤 Bot
    def not_bot(issue):
        fields = issue.get('fields', {})
        assignee = (fields.get('assignee') or {}).get('displayName', '').lower().strip()
        reporter = (fields.get('reporter') or {}).get('displayName', '').lower().strip()
        return assignee not in BOT_NAMES and reporter not in BOT_NAMES

    # 去重：以 key 为唯一标识，created 和 updated 合并去重
    all_keys = set()
    merged_raw = []
    for i in created_issues + updated_issues:
        if i['key'] not in all_keys and not_bot(i):
            all_keys.add(i['key'])
            merged_raw.append(i)

    # 分类：按 created 和 updated 是否在目标日期
    created_today = [i for i in merged_raw if i['fields'].get('created', '')[:10] == date_str]
    updated_today = [i for i in merged_raw if i['fields'].get('updated', '')[:10] == date_str]

    # enrichment：补充评论和工时
    def enrich(issue):
        key = issue['key']
        fields = issue['fields']
        comments = get_comments(client, key)
        worklogs = get_worklogs(client, key)

        # strip_html 也处理 summary 里的 HTML 残留
        raw_summary = fields.get('summary', '')
        summary = strip_html(raw_summary) if isinstance(raw_summary, str) else str(raw_summary)

        real_comments = [
            {'author': c.get('author', {}).get('displayName', ''),
             'body': strip_html(str(c.get('body', ''))),
             'created': c.get('created', '')[:19]}
            for c in comments
            if c.get('author', {}).get('displayName', '').lower().strip() not in BOT_NAMES
            and len(strip_html(str(c.get('body', '')))) > 5
        ]
        real_worklogs = [
            {'author': w.get('author', {}).get('displayName', ''),
             'timeSpent': w.get('timeSpent', ''),
             'comment': strip_html(w.get('comment', '')),
             'started': w.get('started', '')[:10]}
            for w in worklogs
            if w.get('author', {}).get('displayName', '').lower().strip() not in BOT_NAMES
        ]
        return {
            'key': key,
            'summary': summary,
            'status': fields.get('status', {}).get('name', ''),
            'issuetype': (fields.get('issuetype') or {}).get('name', ''),
            'priority': (fields.get('priority') or {}).get('name', ''),
            'resolution': (fields.get('resolution') or {}).get('name', ''),
            'assignee': (fields.get('assignee') or {}).get('displayName', ''),
            'reporter': (fields.get('reporter') or {}).get('displayName', ''),
            'created': fields.get('created', '')[:10],
            'updated': fields.get('updated', '')[:10],
            'comments': real_comments,
            'worklogs': real_worklogs,
        }

    print(f"  enrichment: {len(created_today)} created, {len(updated_today)} updated (merged from {len(merged_raw)} unique)...", flush=True)
    # 只对需要 enrichment 的 issue 发起 API 调用
    created_enr = [enrich(i) for i in created_today]
    updated_enr = [enrich(i) for i in updated_today if i['key'] not in {c['key'] for c in created_today}]
    # 更新列表中排除已 enriched 的 created_today
    updated_enr_deduped = []
    created_keys = {i['key'] for i in created_enr}
    for i in updated_today:
        if i['key'] not in created_keys:
            updated_enr_deduped.append(enrich(i))

    # 写入 Markdown
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# JIRA 数据缓存 {date_str}\n\n")
        f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # ── 新建的问题 ──
        f.write(f"## 新建问题（共 {len(created_enr)} 个）\n\n")
        if created_enr:
            for i in sorted(created_enr, key=lambda x: x['key']):
                f.write(f"### [{i['key']}] {i['summary']}\n\n")
                f.write(f"- 类型: {i['issuetype']} | 状态: {i['status']} | 优先级: {i['priority']}\n")
                f.write(f"- 创建者: {i['reporter']} | 负责人: {i['assignee']}\n")
                f.write(f"- 创建时间: {i['created']} | 更新时间: {i['updated']}\n")
                if i['comments']:
                    f.write(f"- **评论（共 {len(i['comments'])} 条）**\n")
                    for c in i['comments']:
                        f.write(f"  - **{c['author']}** ({c['created'][:10]}): {c['body'][:100]}\n")
                else:
                    f.write(f"- 评论: 无\n")
                f.write(f"\n")
        else:
            f.write(f"_无新建问题_\n\n")

        # ── 更新的问题 ──
        f.write(f"## 更新问题（共 {len(updated_enr_deduped)} 个）\n\n")
        for i in sorted(updated_enr_deduped, key=lambda x: x['assignee'] + x['key']):
            is_done = i['status'] == 'Done'
            is_new = i['created'] == date_str
            flag = " ✅" if is_done else (" 🆕" if is_new else "")
            f.write(f"### [{i['key']}]{flag} {i['summary']}\n\n")
            f.write(f"- 类型: {i['issuetype']} | 状态: {i['status']} | 优先级: {i['priority']}\n")
            f.write(f"- 负责人: {i['assignee']} | 创建者: {i['reporter']}\n")
            f.write(f"- 创建时间: {i['created']} | 更新时间: {i['updated']}\n")
            if i['comments']:
                f.write(f"- **评论（共 {len(i['comments'])} 条）**\n")
                for c in i['comments']:
                    f.write(f"  - **{c['author']}** ({c['created'][:10]}): {c['body'][:120]}\n")
            else:
                f.write(f"- 评论: 无\n")
            if i['worklogs']:
                f.write(f"- **工时记录（共 {len(i['worklogs'])} 条）**\n")
                for w in i['worklogs']:
                    f.write(f"  - **{w['author']}** ({w['started']}): {w['timeSpent']} - {w['comment'][:80]}\n")
            f.write(f"\n")

        # ── 汇总表（包含今日新建 + 今日更新的所有 issues）──
        # 合并去重
        all_for_summary = {i['key']: i for i in created_enr}
        for i in updated_enr_deduped:
            all_for_summary.setdefault(i['key'], i)
        f.write(f"## 汇总\n\n")
        f.write(f"| Key | 摘要 | 类型 | 状态 | 负责人 | 创建时间 | 评论数 | 工时数 |\n")
        f.write(f"|-----|------|------|------|--------|----------|--------|--------|\n")
        for i in sorted(all_for_summary.values(), key=lambda x: x['key']):
            is_new = " 🆕" if i['created'] == date_str else ""
            summary_text = i['summary'][:50] if len(i['summary']) > 50 else i['summary']
            f.write(f"| {i['key']}{is_new} | {summary_text} | {i['issuetype']} | {i['status']} | {i['assignee']} | {i['created']} | {len(i['comments'])} | {len(i['worklogs'])} |\n")
        f.write(f"\n")

    print(f"  写入完成: {output_path}", flush=True)
    return output_path


def main():
    parser = argparse.ArgumentParser(description='JIRA → Markdown 缓存')
    parser.add_argument('date', nargs='?', default=None)
    parser.add_argument('--output', '-o', help='输出 Markdown 路径')
    args = parser.parse_args()

    date_str = parse_date(args.date)
    print(f"[jira_to_md] date={date_str}", flush=True)

    if args.output:
        output_path = args.output
    else:
        os.makedirs(CACHE_DIR, exist_ok=True)
        output_path = os.path.join(CACHE_DIR, f"jira-{date_str}.md")

    fetch_and_cache(date_str, output_path)
    print(f"\n✅ 数据已缓存到: {output_path}")


if __name__ == '__main__':
    main()
