#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab Daily Fetcher - 按人聚合存储
输出：~/.hermes/product-data/raw/{DATE}/gitlab/{author}.json

不再依赖 JIRA key 来索引，直接按 author 聚合当天所有 commits。
每条 commit 仍然保留 jira_keys 字段供后续分析用。
"""
import urllib.request
import json
import re
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

GL_URL  = os.environ.get('GITLAB_URL',  'http://192.168.10.254:20080')
GL_USER = os.environ.get('GITLAB_USER', 'devops')
GL_PASS = os.environ.get('GITLAB_PASS', 'devops@HyperMotion')

# ── 节假日 API ───────────────────────────────────────────────────────────
_HC_PATH = Path(__file__).parent.parent.parent / "holiday-checker" / "scripts" / "holiday_check.py"
if _HC_PATH.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("holiday_checker", _HC_PATH)
    _hc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_hc)
    prev_workday_api = _hc.prev_workday_fast
else:
    def prev_workday_api(dt):
        d = dt - timedelta(days=1)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        return d


def parse_date(date_arg):
    today = datetime.now()
    if date_arg in (None, '', 'today'):
        return prev_workday_api(today).strftime('%Y-%m-%d')
    elif date_arg == 'yesterday':
        return prev_workday_api(today).strftime('%Y-%m-%d')
    return date_arg


# ── GitLab API ────────────────────────────────────────────────────────────
def get_token():
    data = json.dumps({'grant_type': 'password', 'username': GL_USER, 'password': GL_PASS}).encode()
    req = urllib.request.Request(
        f'{GL_URL}/oauth/token',
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']


def api(path, token, timeout=20):
    separator = '&' if '?' in path else '?'
    url = f'{GL_URL}/api/v4{path}{separator}per_page=100'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_hyper_motion_projects(token):
    projects = []
    for page in range(1, 20):
        try:
            result = api(f'/groups/36/projects?page={page}', token)
            if not result:
                break
            projects.extend([p for p in result if p['path_with_namespace'].startswith('hypermotion/')])
            if len(result) < 100:
                break
        except Exception as e:
            print(f'  [WARN] group projects page {page}: {e}', flush=True)
            break
    return projects


def get_project_commits(project_id, date_str, token):
    """获取项目在指定日期的所有 commits"""
    after = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    commits = []
    for page in range(1, 50):
        try:
            url = f'/projects/{project_id}/repository/commits?all=true&since={after}&until={date_str}%2023:59:59&page={page}'
            result = api(url, token)
            if not result:
                break
            if isinstance(result, dict):
                result = result.get('list', []) or []
            commits.extend(result)
            if len(result) < 100:
                break
        except Exception:
            break
    return commits


def get_commit_stats(project_id, sha, token):
    try:
        c = api(f'/projects/{project_id}/repository/commits/{sha}', token)
        stats = c.get('stats', {})
        return stats.get('additions', 0), stats.get('deletions', 0)
    except Exception:
        return 0, 0


# ── Commit 解析 ─────────────────────────────────────────────────────────
JIRA_KEY_RE = re.compile(r'(BUG|REQ|TASK|IMP|STORY|PRO|CLI|DOC|SEC|PE|SUB|PRJ)-(\d+)', re.IGNORECASE)

def extract_keys(commit):
    """从 commit message + ref 中提取所有 JIRA keys（必须带数字）"""
    text = (commit.get('message', '') or '') + ' ' + (commit.get('ref', '') or '')
    keys = set()
    for prefix, num in JIRA_KEY_RE.findall(text):
        keys.add(f'{prefix.upper()}-{num}')
    return list(keys)


# ── 按 author 聚合 ────────────────────────────────────────────────────────
def group_by_author(commits_with_stats):
    """
    按 author 聚合 commits
    commits_with_stats: list of dict with sha, author, message, project, additions, deletions, jira_keys, date
    """
    by_author = {}
    for c in commits_with_stats:
        author = c['author']
        if author not in by_author:
            by_author[author] = {
                'author': author,
                'commits': [],
                'total_additions': 0,
                'total_deletions': 0,
                'commit_count': 0,
                'projects': set(),
                'all_jira_keys': set(),
                'has_jira_key': False,
            }
        entry = by_author[author]
        entry['commits'].append({
            'sha': c['sha'],
            'message': c['message'],
            'project': c['project'],
            'additions': c['additions'],
            'deletions': c['deletions'],
            'jira_keys': c['jira_keys'],
            'date': c['date'],
        })
        entry['total_additions'] += c['additions']
        entry['total_deletions'] += c['deletions']
        entry['commit_count'] += 1
        entry['projects'].add(c['project'])
        if c['jira_keys']:
            entry['has_jira_key'] = True
            entry['all_jira_keys'].update(c['jira_keys'])

    # set → list
    for author, data in by_author.items():
        data['projects'] = sorted(data['projects'])
        data['all_jira_keys'] = sorted(data['all_jira_keys'])
        # 合并同类 commit（同 message 的多条 commit 合并展示）
        data['commit_groups'] = _group_similar_commits(data['commits'])
    return by_author


def _group_similar_commits(commits):
    """
    将 message 相同的 commits 合并成一个 group（这些大概率是重复提交或 squash 后残留）
    返回 list of {message, projects, total_add, total_del, count, shas}
    """
    groups = {}
    for c in commits:
        msg = c['message']
        if msg not in groups:
            groups[msg] = {
                'message': msg,
                'projects': set(),
                'total_add': 0,
                'total_del': 0,
                'count': 0,
                'shas': [],
            }
        g = groups[msg]
        g['projects'].add(c['project'])
        g['total_add'] += c['additions']
        g['total_del'] += c['deletions']
        g['count'] += 1
        g['shas'].append(c['sha'])

    result = []
    for msg, g in groups.items():
        g['projects'] = sorted(g['projects'])
        g['shas'] = g['shas']  # 保持原顺序
        result.append(g)
    # 按 count * total_add 排序，多的在前
    result.sort(key=lambda x: -(x['count'] * x['total_add'] + x['total_add']))
    return result


# ── 主抓取逻辑 ────────────────────────────────────────────────────────────
def fetch_daily(date_str):
    """抓取指定日期所有 commits，按 author 聚合存储"""
    # 输出路径
    base_dir = Path.home() / ".hermes" / "product-data" / "raw" / date_str / "gitlab"
    cache_path = base_dir / "_meta.json"

    # 检查缓存
    if cache_path.exists():
        print(f"[gl_daily] 使用缓存: {cache_path}", flush=True)
        # 返回所有 author 文件
        result = {}
        for f in base_dir.glob("*.json"):
            if f.name == "_meta.json":
                continue
            with open(f) as fp:
                result[f.stem] = json.load(fp)
        return result

    print(f"[gl_daily] date={date_str}", flush=True)
    token = get_token()
    print("[gl_daily] token ok", flush=True)

    projects = get_hyper_motion_projects(token)
    print(f"[gl_daily] found {len(projects)} projects", flush=True)

    all_commits = []

    for proj in projects:
        pid = proj['id']
        pname = proj['path_with_namespace']
        print(f"  scanning {pname}...", flush=True, end='')

        commits = get_project_commits(pid, date_str, token)
        print(f" {len(commits)} commits", flush=True)

        for c in commits:
            author = c.get('author_name', '') or ''
            if author.lower() in ('gitlab', 'bot', 'system', ''):
                continue

            msg = (c.get('message', '') or '').split('\n')[0].strip()
            # 跳过 merge branch commit
            if re.match(r"Merge branch", msg):
                continue

            sha = (c.get('id', '') or '')[:8]
            committed_date = (c.get('committed_date', '') or '')[:10]
            additions, deletions = get_commit_stats(pid, sha, token)
            keys = extract_keys(c)

            all_commits.append({
                'sha': sha,
                'author': author,
                'message': msg,
                'project': pname,
                'additions': additions,
                'deletions': deletions,
                'jira_keys': keys,
                'date': committed_date,
            })

    # 按 author 聚合
    by_author = group_by_author(all_commits)
    print(f"[gl_daily] 按 author 聚合完成：{len(by_author)} 人", flush=True)

    # 写入文件
    base_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        'date': date_str,
        'total_commits': len(all_commits),
        'total_authors': len(by_author),
        'authors': sorted(by_author.keys()),
    }

    for author, data in by_author.items():
        author_path = base_dir / f"{author}.json"
        with open(author_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 写入 meta
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[gl_daily] ✅ 缓存已保存: {base_dir}/", flush=True)
    print(f"  作者数: {len(by_author)}", flush=True)
    for author, data in by_author.items():
        print(f"  - {author}: {data['commit_count']} commits, +{data['total_additions']}/-{data['total_deletions']}")

    return by_author


# ── 入口 ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="GitLab Daily Fetcher（按人聚合）")
    parser.add_argument('date', nargs='?', default=None, help='日期 yyyy-MM-dd')
    parser.add_argument('--json', '-j', action='store_true', help='打印 JSON')
    args = parser.parse_args()

    date_str = parse_date(args.date)
    result = fetch_daily(date_str)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n[gl_daily] ✅ 完成：{len(result)} 人")
