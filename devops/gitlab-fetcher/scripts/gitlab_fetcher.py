#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab Commit 抓取脚本
依赖：jira-fetcher 抓的 JIRA issues（用于关联 commit → JIRA key）
缓存：~/.hermes/gitlab-cache/gitlab-{DATE}.json
"""
import urllib.request, json, re, sys, os
from datetime import datetime, timedelta
from pathlib import Path

GL_URL  = os.environ.get('GITLAB_URL',  'http://192.168.10.254:20080')
GL_USER = os.environ.get('GITLAB_USER', 'devops')
GL_PASS = os.environ.get('GITLAB_PASS', 'devops@HyperMotion')
CACHE_DIR = Path.home() / ".hermes" / "gitlab-cache"

# ── GitLab → JIRA 用户名映射（用于关联提交人）────────────────────────────
GL_TO_JIRA = {
    'zhangjiaqi':    '张佳奇',
    'zhangtianjie9761': '张天洁',
    'wanghuixian':   '王慧仙',
    'liulixiang9312': '刘立祥',
    'yongmengmeng8311': '雍蒙蒙',
    'lijianhai':     '李建海',
    'guozhonghua':   '郭中华',
}

# ── 节假日 API ───────────────────────────────────────────────────────────
_HC_PATH = Path(__file__).parent.parent / "holiday-checker" / "scripts" / "holiday_check.py"
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


# ── 日期解析 ──────────────────────────────────────────────────────────────
def parse_date(date_arg):
    today = datetime.now()
    if date_arg in (None, '', 'today'):
        return prev_workday_api(today).strftime('%Y-%m-%d')
    elif date_arg == 'yesterday':
        return prev_workday_api(today).strftime('%Y-%m-%d')
    return date_arg


# ── GitLab API ──────────────────────────────────────────────────────────────
def get_token():
    data = json.dumps({'grant_type': 'password', 'username': GL_USER, 'password': GL_PASS}).encode()
    req = urllib.request.Request(f'{GL_URL}/oauth/token', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']


def api(path, token, timeout=20):
    separator = '&' if '?' in path else '?'
    url = f'{GL_URL}/api/v4{path}{separator}per_page=100'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_hyper_motion_projects(token):
    """获取 hypermotion 组下所有项目"""
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


def get_project_commits(project_id, project_name, date_str, token):
    """获取项目在指定日期范围的所有 commit"""
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
    """获取 commit 代码行数"""
    try:
        c = api(f'/projects/{project_id}/repository/commits/{sha}', token)
        stats = c.get('stats', {})
        return stats.get('additions', 0), stats.get('deletions', 0)
    except Exception:
        return 0, 0


# ── Commit 解析 ─────────────────────────────────────────────────────────────
JIRA_KEY_RE = re.compile(r'(BUG|REQ|TASK|IMP|STORY|PRO|CLI|DOC|SEC|PE|SUB|PRJ)-(\d+)', re.IGNORECASE)

def extract_keys(commit):
    """从 commit message + ref 中提取所有 JIRA keys（必须带数字）"""
    text = (commit.get('message', '') or '') + ' ' + (commit.get('ref', '') or '')
    keys = set()
    for prefix, num in JIRA_KEY_RE.findall(text):
        keys.add(f'{prefix.upper()}-{num}')
    return list(keys)


# ── 主抓取逻辑 ──────────────────────────────────────────────────────────────
def fetch_commits(date_str, jira_keys=None):
    """
    抓取指定日期的所有 GitLab commits
    jira_keys: 可选，已知的 JIRA keys（用于优先关联）
    返回: {
        'by_key': {jira_key: [commit, ...]},
        'by_project': {project_name: [commit, ...]},
        'unlinked': [commit, ...],
    }
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"gitlab-{date_str}.json"

    # 检查缓存
    if cache_path.exists():
        print(f"[gitlab_fetcher] 使用缓存: {cache_path}", flush=True)
        with open(cache_path) as f:
            return json.load(f)

    print(f"[gitlab_fetcher] date={date_str}", flush=True)
    token = get_token()
    print("[gitlab_fetcher] token ok", flush=True)

    projects = get_hyper_motion_projects(token)
    print(f"[gitlab_fetcher] found {len(projects)} projects", flush=True)

    by_key = {}      # {JIRA_KEY: [commit]}
    by_project = {}  # {project: [commit]}
    unlinked = []    # 无 JIRA key 的 commit

    jira_keys = set(jira_keys or [])

    for proj in projects:
        pid = proj['id']
        pname = proj['path_with_namespace']
        print(f"  scanning {pname}...", flush=True, end='')

        commits = get_project_commits(pid, pname, date_str, token)
        print(f" {len(commits)} commits", flush=True)

        for c in commits:
            author = c.get('author_name', '') or ''
            if author.lower() in ('gitlab', 'bot', 'system', ''):
                continue

            msg = (c.get('message', '') or '').split('\n')[0].strip()
            # 跳过 merge branch commit（无功能价值）
            if re.match(r"Merge branch", msg):
                continue
            sha = (c.get('id', '') or '')[:8]
            committed_date = (c.get('committed_date', '') or '')[:10]

            additions, deletions = get_commit_stats(pid, sha, token)
            keys = extract_keys(c)

            entry = {
                'sha': sha,
                'author': author,
                'author_jira': GL_TO_JIRA.get(author, author),
                'message': msg[:100],
                'project': pname,
                'jira_keys': keys,
                'additions': additions,
                'deletions': deletions,
                'date': committed_date,
            }

            # 按项目归类
            if pname not in by_project:
                by_project[pname] = []
            by_project[pname].append(entry)

            # 按 JIRA key 关联
            if keys:
                for k in keys:
                    if k not in by_key:
                        by_key[k] = []
                    by_key[k].append(entry)
            else:
                unlinked.append(entry)

    result = {
        'date': date_str,
        'by_key': by_key,
        'by_project': by_project,
        'unlinked': unlinked,
    }

    # 缓存
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[gitlab_fetcher] ✅ 缓存已保存: {cache_path}", flush=True)
    return result


# ── 格式化输出（JSON → 可读）───────────────────────────────────────────────
def format_summary(data):
    """生成 GitLab commit 可读汇总（按项目分组）"""
    lines = []
    lines.append("## GitLab Commit 汇总")

    by_project = data.get('by_project', {})
    by_key = data.get('by_key', {})
    unlinked = data.get('unlinked', [])

    total_commits = sum(len(v) for v in by_project.values())
    total_keys = len(by_key)
    total_unlinked = len(unlinked)

    lines.append(f"\n📊 共 {total_commits} 条 commit，关联 {total_keys} 个 JIRA issue，{total_unlinked} 条无关联")

    if by_key:
        lines.append("\n### 按 JIRA Issue 关联")
        for key in sorted(by_key.keys()):
            commits = by_key[key]
            total_add = sum(c['additions'] for c in commits)
            total_del = sum(c['deletions'] for c in commits)
            projects = list(dict.fromkeys(c['project'] for c in commits))
            authors = list(dict.fromkeys(c['author'] for c in commits))
            msgs = commits[0]['message'][:60]
            lines.append(f"- **{key}**：`{msgs}`")
            lines.append(f"  · {len(commits)} commits | +{total_add}/-{total_del} | {', '.join(authors[:3])}")

    if by_project:
        lines.append("\n### 按项目分组")
        for pname, commits in sorted(by_project.items(), key=lambda x: -len(x[1]))[:10]:
            total_add = sum(c['additions'] for c in commits)
            authors = list(dict.fromkeys(c['author'] for c in commits))
            lines.append(f"- **{pname}**：{len(commits)} commits | +{total_add} | {', '.join(authors[:3])}")

    if unlinked:
        lines.append(f"\n### 无 JIRA 关联的 Commit（{len(unlinked)} 条）")
        for c in unlinked[:5]:
            lines.append(f"- `{c['sha']}` {c['author']}：{c['message'][:60]}")

    return '\n'.join(lines)


# ── 入口 ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="GitLab Commit 抓取")
    parser.add_argument('date', nargs='?', default=None, help='日期 yyyy-MM-dd')
    parser.add_argument('--format', '-f', action='store_true', help='打印可读汇总')
    parser.add_argument('--json', '-j', action='store_true', help='打印 JSON')
    args = parser.parse_args()

    date_str = parse_date(args.date)

    data = fetch_commits(date_str)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif args.format:
        print(format_summary(data))
    else:
        print(f"[gitlab_fetcher] ✅ 抓取完成: {CACHE_DIR / f'gitlab-{date_str}.json'}")
        print(f"  关联 commit: {sum(len(v) for v in data['by_key'].values())} 条")
        print(f"  涉及 JIRA: {len(data['by_key'])} 个")
        print(f"  无关联: {len(data['unlinked'])} 条")
