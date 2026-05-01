#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA 数据获取模块
职责：连接 JIRA API，按日期拉取原始数据，清洗干净后输出结构化 JSON
对外暴露：CLI + Python function
"""
import os, sys, json, argparse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

JIRA_URL  = os.environ.get('JIRA_URL',      'http://office.oneprocloud.com.cn:9005')
JIRA_USER = os.environ.get('JIRA_USERNAME', 'sunqi')
JIRA_PASS = os.environ.get('JIRA_PASSWORD',  'sunqi1358')


def prev_workday(d: datetime) -> datetime:
    d = d - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def parse_date(date_arg: Optional[str]) -> tuple[str, str]:
    """返回 (query_date, display_date)"""
    today = datetime.now()
    if date_arg in (None, '', 'today', 'yesterday'):
        pw = prev_workday(today)
        return pw.strftime('%Y-%m-%d'), pw.strftime('%Y-%m-%d')
    elif date_arg == 'this-week':
        start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        return start, today.strftime('%Y-%m-%d')
    else:
        return date_arg, date_arg


def get_jira_client():
    from atlassian import Jira
    return Jira(url=JIRA_URL, username=JIRA_USER, password=JIRA_PASS, cloud=False, timeout=30)


def strip_html(text: str) -> str:
    import re
    return re.sub(r'<[^>]+>', '', text).strip()


BOT_NAMES = {'girabot', 'girabot ', 'jirabot', 'gbot', 'bot', 'system', ''}


def jql_search(client, jql: str, fields: str, limit=200) -> List[Dict]:
    """通用 JQL 查询"""
    result = client.jql(jql, limit=limit, fields=fields)
    if isinstance(result, dict):
        return result.get('issues', [])
    return result or []


def fetch_by_date(date_str: str):
    """拉取指定日期的原始数据"""
    client = get_jira_client()

    # 查询该日期新建的 issue
    jql_created = (
        f'created >= "{date_str}" AND created <= "{date_str} 23:59" '
        'ORDER BY created DESC'
    )
    created_issues = jql_search(client, jql_created, 'summary,status,assignee,reporter,created,updated,issuetype,priority,resolution', limit=200)

    # 查询该日期更新的 issue
    jql_updated = (
        f'updated >= "{date_str}" AND updated <= "{date_str} 23:59" '
        'ORDER BY updated DESC'
    )
    updated_issues = jql_search(client, jql_updated, 'summary,status,assignee,reporter,created,updated,issuetype,priority,resolution', limit=200)

    return {
        'created': created_issues,
        'updated': updated_issues,
    }


def get_comments(client, issue_key: str) -> List[Dict]:
    """获取某 issue 的评论"""
    try:
        raw = client.issue_get_comments(issue_key)
        if isinstance(raw, dict):
            return raw.get('comments', []) or []
        elif isinstance(raw, list):
            return raw
    except Exception:
        pass
    return []


def get_worklogs(client, issue_key: str) -> List[Dict]:
    """获取某 issue 的工时"""
    try:
        raw = client.get_issue_worklog(issue_key)
        if isinstance(raw, dict):
            return raw.get('worklogs', []) or []
        elif isinstance(raw, list):
            return raw
    except Exception:
        pass
    return []


def enrich_issue(issue: Dict, client) -> Dict:
    """为单个 issue 补充评论和工时"""
    key = issue.get('key', '')
    fields = issue.get('fields', {})

    comments = get_comments(client, key)
    worklogs = get_worklogs(client, key)

    # 过滤 Bot 评论
    real_comments = [
        {
            'author': c.get('author', {}).get('displayName', ''),
            'body': strip_html(str(c.get('body', ''))),
            'created': c.get('created', '')[:19],
        }
        for c in comments
        if c.get('author', {}).get('displayName', '').lower().strip() not in BOT_NAMES
        and len(strip_html(str(c.get('body', '')))) > 5
    ]

    real_worklogs = [
        {
            'author': w.get('author', {}).get('displayName', ''),
            'timeSpent': w.get('timeSpent', ''),
            'comment': strip_html(w.get('comment', '')),
            'started': w.get('started', '')[:10],
        }
        for w in worklogs
        if w.get('author', {}).get('displayName', '').lower().strip() not in BOT_NAMES
    ]

    return {
        'key': key,
        'summary': fields.get('summary', ''),
        'status': fields.get('status', {}).get('name', ''),
        'issuetype': fields.get('issuetype', {}).get('name', ''),
        'priority': fields.get('priority', {}).get('name', ''),
        'resolution': (fields.get('resolution') or {}).get('name', ''),
        'assignee': (fields.get('assignee') or {}).get('displayName', ''),
        'reporter': (fields.get('reporter') or {}).get('displayName', ''),
        'created': fields.get('created', '')[:10],
        'updated': fields.get('updated', '')[:10],
        'comments': real_comments,
        'worklogs': real_worklogs,
        'comment_count': len(real_comments),
        'worklog_count': len(real_worklogs),
    }


def enrich_all(raw_data: Dict) -> Dict:
    """对拉取的原始数据做 enrichment"""
    client = get_jira_client()

    # 过滤掉 Bot 创建的 issue
    created = [
        i for i in raw_data.get('created', [])
        if (i.get('fields', {}).get('assignee') or {}).get('displayName', '').lower().strip() not in BOT_NAMES
        and (i.get('fields', {}).get('reporter') or {}).get('displayName', '').lower().strip() not in BOT_NAMES
    ]
    updated = [
        i for i in raw_data.get('updated', [])
        if (i.get('fields', {}).get('assignee') or {}).get('displayName', '').lower().strip() not in BOT_NAMES
    ]

    # 去重：以 updated 为准（updated 范围更广）
    seen = set()
    dedup_updated = []
    for i in updated:
        k = i['key']
        if k not in seen:
            seen.add(k)
            dedup_updated.append(i)

    # enrichment
    created_enr = [enrich_issue(i, client) for i in created]
    updated_enr = [enrich_issue(i, client) for i in dedup_updated]

    return {
        'created': created_enr,
        'updated': updated_enr,
        'stats': {
            'created_count': len(created_enr),
            'updated_count': len(updated_enr),
        }
    }


def main():
    parser = argparse.ArgumentParser(description='JIRA Data Fetcher')
    parser.add_argument('date', nargs='?', default=None, help='日期 (YYYY-MM-DD), 默认为上一个工作日')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    parser.add_argument('--enriched', action='store_true', help='是否补充评论和工时')
    args = parser.parse_args()

    query_date, display_date = parse_date(args.date)
    print(f"[jira_fetch] date={query_date}", file=sys.stderr, flush=True)

    raw = fetch_by_date(query_date)

    if args.enriched:
        data = enrich_all(raw)
    else:
        # 简单过滤
        data = {
            'created': [
                i for i in raw.get('created', [])
                if (i.get('fields', {}).get('assignee') or {}).get('displayName', '').lower().strip() not in BOT_NAMES
            ],
            'updated': [
                i for i in raw.get('updated', [])
                if (i.get('fields', {}).get('assignee') or {}).get('displayName', '').lower().strip() not in BOT_NAMES
            ],
            'stats': {
                'created_count': len(raw.get('created', [])),
                'updated_count': len(raw.get('updated', [])),
            }
        }

    if args.json:
        output = {
            'query_date': query_date,
            'display_date': display_date,
            'data': data,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"[jira_fetch] created={data['stats']['created_count']}, updated={data['stats']['updated_count']}", file=sys.stderr, flush=True)
        # 非 JSON 模式：直接输出 data 供管道使用
        print(json.dumps({'query_date': query_date, 'display_date': display_date, 'data': data}, ensure_ascii=False))


if __name__ == '__main__':
    main()
