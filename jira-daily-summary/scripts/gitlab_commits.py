#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab Commit 抓取脚本 v2
按 JIRA key 搜 commit，统计代码行数
"""
import urllib.request, json, re, sys
from datetime import datetime, timedelta

GL_URL  = 'http://192.168.10.254:20080'
GL_USER = 'devops'
GL_PASS = 'devops@HyperMotion'

# 昨日数据相关的 JIRA keys
JIRA_KEYS = [
    'BUG-6477', 'BUG-6470', 'BUG-6471', 'BUG-6476', 'BUG-6451',
    'BUG-6472', 'REQ-6107', 'REQ-5767', 'REQ-6160', 'REQ-5716',
    'REQ-6118', 'REQ-5972', 'REQ-6084', 'REQ-5182',
]


def get_token():
    data = json.dumps({'grant_type': 'password', 'username': GL_USER, 'password': GL_PASS}).encode()
    req = urllib.request.Request(f'{GL_URL}/oauth/token', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']


def api(path, token, timeout=20):
    url = f'{GL_URL}/api/v4{path}' if '?' in path else f'{GL_URL}/api/v4{path}?per_page=100'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_hyper_motion_projects(token):
    """获取 hypermotion 组下的所有项目"""
    projects = []
    page = 1
    while True:
        try:
            result = api(f'/groups/36/projects?per_page=100&page={page}', token)
            if not result:
                break
            projects.extend(result)
            if len(result) < 100:
                break
            page += 1
        except Exception as e:
            print(f'  [WARN] group projects page {page}: {e}', flush=True)
            break
    return projects


def get_project_commits(project_id, project_name, date_str, token):
    """获取项目在指定日期的所有 commit"""
    after = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    commits = []
    page = 1
    while True:
        try:
            url = f'/projects/{project_id}/repository/commits?all=true&since={after}&until={date_str}%2023:59:59&per_page=100&page={page}'
            result = api(url, token)
            if not result:
                break
            if isinstance(result, dict):
                result = result.get('list', []) or []
            commits.extend(result)
            if len(result) < 100:
                break
            page += 1
        except Exception as e:
            break
    return commits


def get_commit_diff_stats(project_id, sha, token):
    """获取 commit 的统计信息"""
    try:
        c = api(f'/projects/{project_id}/repository/commits/{sha}', token)
        stats = c.get('stats', {})
        return {
            'additions': stats.get('additions', 0),
            'deletions': stats.get('deletions', 0),
            'total': stats.get('total', 0),
        }
    except Exception:
        return {'additions': 0, 'deletions': 0, 'total': 0}


def search_commits_by_key(project_id, project_name, date_str, token):
    """在项目中搜索包含特定 JIRA key 的 commit"""
    all_commits = get_project_commits(project_id, project_name, date_str, token)
    results = []

    for c in all_commits:
        msg = c.get('message', '') or ''
        # 提取 commit 中的 JIRA key
        found_keys = re.findall(r'(BUG|REQ|TASK|IMP|STORY|PRO|CLI|DOC|SEC|PE|SUB)-\d+', msg, re.IGNORECASE)
        for key in set(found_keys):
            key_upper = key.upper()
            author = c.get('author_name', '')
            if not author or author.lower() in ('gitlab', 'bot', 'system', ''):
                continue
            sha = c.get('id', '')
            diff_stats = get_commit_diff_stats(project_id, sha, token)
            # 搜索 full message（含第二行及以后）+ ref 字段
            full_text = msg + ' ' + c.get('ref', '') + ' ' + ' '.join(c.get('parent_ids', []))
            found_keys = re.findall(r'(BUG|REQ|TASK|IMP|STORY|PRO|CLI|DOC|SEC|PE|SUB)-(\d+)', full_text, re.IGNORECASE)
            for key_prefix, key_num in set(found_keys):
                key_upper = f'{key_prefix.upper()}-{key_num}'
                results.append({
                    'key': key_upper,
                    'project': project_name,
                    'author': author,
                    'message': msg.split('\n')[0].strip()[:100],
                    'sha': sha[:8],
                    'date': c.get('committed_date', '')[:10],
                    'additions': diff_stats['additions'],
                    'deletions': diff_stats['deletions'],
                })
    return results


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else '2026-04-15'
    print(f"[gitlab] date={date_str}", flush=True)

    token = get_token()
    print("[gitlab] token ok", flush=True)

    projects = get_hyper_motion_projects(token)
    print(f"[gitlab] found {len(projects)} projects in hypermotion group", flush=True)

    all_commits = []
    for proj in projects:
        pid = proj['id']
        pname = proj['path_with_namespace']
        # 跳过非 hypermotion 主线项目
        if not pname.startswith('hypermotion/'):
            continue
        print(f"\n[gitlab] scanning {pname}...", flush=True, end='')
        hits = search_commits_by_key(pid, pname, date_str, token)
        print(f" → {len(hits)} commits", flush=True)
        all_commits.extend(hits)

    # 按人聚合
    by_person = {}
    for c in all_commits:
        author = c['author']
        if author not in by_person:
            by_person[author] = {'commits': [], 'by_key': {}}
        by_person[author]['commits'].append(c)
        key = c['key']
        if key not in by_person[author]['by_key']:
            by_person[author]['by_key'][key] = []
        by_person[author]['by_key'][key].append(c)

    # 输出
    print(f"\n\n{'='*70}")
    print(f"  GitLab Commit 统计 {date_str}  （按代码行数排序）")
    print(f"{'='*70}")

    for author, data in sorted(by_person.items(), key=lambda x: -sum(c['additions'] for c in x[1]['commits'])):
        total_add = sum(c['additions'] for c in data['commits'])
        total_del = sum(c['deletions'] for c in data['commits'])
        print(f"\n  👤 {author}")
        print(f"  📊 {len(data['commits'])} commits | +{total_add} / -{total_del} 行 | {len(data['by_key'])} 个 JIRA issue")

        for key, commits in sorted(data['by_key'].items(), key=lambda x: -sum(c['additions'] for c in x[1])):
            c_add = sum(c['additions'] for c in commits)
            c_del = sum(c['deletions'] for c in commits)
            msgs = ' | '.join([c['message'][:40] for c in commits[:2]])
            print(f"     {key}: {len(commits)} commits (+{c_add}/-{c_del})")
            print(f"       {msgs}")

    # 保存 JSON 缓存
    cache_path = f'/tmp/gitlab-commits-{date_str}.json'
    with open(cache_path, 'w') as f:
        json.dump({'date': date_str, 'commits': all_commits, 'by_person': {k: {
            'commits': v['commits'],
            'by_key': v['by_key'],
            'total_add': sum(c['additions'] for c in v['commits']),
            'total_del': sum(c['deletions'] for c in v['commits']),
        } for k, v in by_person.items()}}, f, ensure_ascii=False, indent=2)
    print(f"\n✅ commit 数据已缓存: {cache_path}")


if __name__ == '__main__':
    main()
