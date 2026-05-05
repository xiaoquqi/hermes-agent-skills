#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab Commit Patch 采集脚本

基于 clone_projects.sh 的分支规则，采集指定项目/分支的 commit patch，按天存储。

输出结构：
  ~/.hermes/code-insights/commits/{date}/{project}/
  ├── commits.json       # commit 元数据
  └── {commit_id}.patch # 每个 commit 的完整 diff
"""
import urllib.request
import urllib.error
import urllib.parse
import json
import re
import sys
import os
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ────────────────────────────────────────────────────────────────────
GL_URL     = os.environ.get('GITLAB_URL',     'http://192.168.10.254:20080')
GL_USER    = os.environ.get('GITLAB_USER',    'devops')
GL_PASS    = os.environ.get('GITLAB_PASS',    'devops@HyperMotion')
GL_GROUP_ID = os.environ.get('GITLAB_GROUP_ID', '36')

BASE_DIR = Path.home() / ".hermes" / "code-insights"
# 共享本地持久 clone 目录（与 reporter.py 共用）
REPOS_DIR = BASE_DIR / "repos"

# ── 分支规则（与 clone_projects.sh 保持一致）────────────────────────────────
# atomy/* 模块固定用 qa 分支
# hypermotion/CI-CD 固定用 master 分支
# 其他 hypermotion/* 默认用 saas_qa 分支
DEFAULT_BRANCH = 'saas_qa'

def resolve_branch(project_path):
    """根据项目路径返回正确的分支名（与 clone_projects.sh 逻辑一致）"""
    if project_path.startswith('atomy/'):
        return 'qa'
    if project_path == 'hypermotion/CI-CD':
        return 'master'
    return DEFAULT_BRANCH


# ── 项目列表（与 clone_projects.sh 保持一致）─────────────────────────────────
# 格式：(path_with_namespace, branch_override_or_None)
# branch_override 为 None 时使用 resolve_branch() 自动判断
PROJECT_LIST = [
    # HyperBDR 组 - 大部分用 saas_qa，atomy 用 qa
    ('hypermotion/deploy',            None),
    ('hypermotion/CI-CD',             None),   # -> master
    ('hypermotion/linux-agent',       None),
    ('hypermotion/partclone',         None),
    ('hypermotion/windows-agent',     None),
    ('hypermotion/WinDsync',          None),
    ('hypermotion/exporter',          None),
    ('hypermotion/ant',               None),
    ('hypermotion/crab',              None),
    ('hypermotion/hamal',             None),
    ('hypermotion/mass',              None),
    ('hypermotion/minitgt',           None),
    ('hypermotion/nezha',            None),
    ('hypermotion/oneway',            None),
    ('hypermotion/owl',               None),
    ('hypermotion/porter',           None),
    ('hypermotion/proxy',             None),
    ('hypermotion/revenue',           None),
    ('hypermotion/storplus',          None),
    ('hypermotion/unicloud',         None),
    ('hypermotion/linux-agent-syncer',None),
    ('hypermotion/nirvana',          None),
    ('hypermotion/supervisor-dashboard', None),
    ('hypermotion/newmuse',          None),
    ('hypermotion/ci-cd-config',     None),
    ('hypermotion/images',           None),
    ('hypermotion/httpd-coding-builder', None),
    ('hypermotion/SwiftS3Block',     None),
    ('atomy/atomy',                   None),    # -> qa
    ('atomy/atomy-api',              None),    # -> qa
    ('atomy/atomy-mistral',          None),    # -> qa
    ('atomy/atomy-mistral-lib',      None),    # -> qa
    ('atomy/atomy-mistral-plugins',  None),    # -> qa
    ('atomy/atomy-obstor',           None),    # -> qa
    ('atomy/atomy-unicloud',        None),    # -> qa
    ('atomy/atomy-s3block',         None),    # -> qa
    ('atomy/HyperUp',               None),    # -> qa
    ('atomy/hamalv3',               None),     # -> qa

    # income 组
    ('hypermotion/income',           None),
    ('hypermotion/income_dashboard',  None),

    # FC 组
    ('hypermotion/prophet',         None),
    ('hypermotion/calculator',       None),
]


# ── 日期解析 ────────────────────────────────────────────────────────────────
def parse_date(date_arg):
    today = datetime.now()
    if date_arg in (None, '', 'today'):
        return today.strftime('%Y-%m-%d')
    elif date_arg == 'yesterday':
        return (today - timedelta(days=1)).strftime('%Y-%m-%d')
    return date_arg


# ── GitLab API ───────────────────────────────────────────────────────────────
def get_token():
    """OAuth 密码模式获取 access token"""
    data = json.dumps({
        'grant_type': 'password',
        'username': GL_USER,
        'password': GL_PASS
    }).encode()
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


def find_project_by_path(token, project_path):
    """通过 path_with_namespace 查找项目信息。

    用项目名（path 最后一段）搜索，然后匹配完整 path_with_namespace。
    避免 URL-encoding 斜杠导致搜索失败。
    """
    proj_name = project_path.rsplit('/', 1)[-1]  # e.g. "nezha"
    try:
        result = api(f'/projects?search={urllib.parse.quote(proj_name)}&per_page=50', token)
        for p in result:
            if p.get('path_with_namespace') == project_path:
                return p
    except Exception:
        pass
    return None


def get_project_commits_for_date(token, project_id, branch, date_str):
    """
    获取项目指定分支在指定日期的 commits。
    使用 ref_name 过滤分支，不再用 all=true 拉所有分支。
    """
    from urllib.parse import quote
    after = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    until_encoded = quote(f"{date_str} 23:59:59", safe='')
    commits = []
    for page in range(1, 30):
        try:
            url = (f'/projects/{project_id}/repository/commits'
                   f'?ref_name={branch}'
                   f'&since={after}&until={until_encoded}'
                   f'&page={page}')
            result = api(url, token)
            if not result:
                break
            if isinstance(result, dict):
                result = result.get('list', []) or []
            # ref_name + since/until 组合已经能精确过滤，不需要再次按日期筛选
            for c in result:
                committed_date = (c.get('committed_date', '') or '')[:10]
                if committed_date == date_str:
                    commits.append(c)
            if len(result) < 100:
                break
        except Exception:
            break
    return commits


# ── Git 操作 ─────────────────────────────────────────────────────────────────
def clone_project(project_url, clone_dir, branch, depth=100):
    """Shallow clone 指定分支的项目到持久化本地目录"""
    from urllib.parse import urlparse, urlunparse, quote
    # 修正 clone URL：替换不可达的 host，并嵌入认证信息
    gl_netloc = urlparse(GL_URL).netloc  # e.g. "192.168.10.254:20080"
    parsed = urlparse(project_url)
    auth_netloc = f"{quote(GL_USER, safe='')}:{quote(GL_PASS, safe='')}@{gl_netloc}"
    project_url = urlunparse(('http', auth_netloc, parsed.path, parsed.params, parsed.query, ''))

    # 如果已存在持久 clone，直接复用（不做删除）
    if clone_dir.exists() and (clone_dir / '.git').exists():
        # 可选：git fetch 更新到最新
        fetch_cmd = ['git', '-C', str(clone_dir), 'fetch', '--depth', str(depth), 'origin', branch]
        subprocess.run(fetch_cmd, capture_output=True, text=True, timeout=60)
        return clone_dir

    clone_dir.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        'git', 'clone',
        '--depth', str(depth),
        '--branch', branch,
        '--single-branch',
        project_url,
        str(clone_dir)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"clone 失败: {result.stderr.strip()}")
    return clone_dir


def save_commit_patch(clone_dir, sha, output_patch_path):
    """保存单个 commit 的 patch 文件"""
    # git show 输出完整的 diff（不过滤文件）
    cmd = ['git', '-C', str(clone_dir), 'show', sha, '--format=', '--patch']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    output_patch_path.write_text(result.stdout or '')


# ── 过滤无效 commit ──────────────────────────────────────────────────────────
SKIP_AUTHORS = {'gitlab', 'bot', 'system', ''}

def filter_commit(commit):
    """过滤无效 commit，返回 None 或过滤后的 dict"""
    author = (commit.get('author_name', '') or '').lower()
    if author in SKIP_AUTHORS:
        return None
    msg = (commit.get('message', '') or '').split('\n')[0].strip()
    if re.match(r"^Merge branch", msg):
        return None
    return {
        'sha': commit.get('id', '') or '',
        'author_name': commit.get('author_name', '') or '',
        'author_email': commit.get('author_email', '') or '',
        'committed_date': (commit.get('committed_date', '') or '')[:19],
        'message': msg[:200],
    }


# ── 主采集逻辑 ───────────────────────────────────────────────────────────────
def collect_commits(date_str, dry_run=False):
    """
    采集指定日期的所有 GitLab commit patch 和元数据。
    分支规则：atomy/* -> qa, CI-CD -> master, 其他 -> saas_qa
    """
    print(f"[code-insights] date={date_str}", flush=True)

    token = get_token()
    print("[code-insights] token ok", flush=True)

    commits_dir = BASE_DIR / "commits" / date_str
    commits_dir.mkdir(parents=True, exist_ok=True)

    total_commits = 0
    processed_projects = 0
    skipped_projects = 0

    for project_path, branch_override in PROJECT_LIST:
        branch = branch_override if branch_override else resolve_branch(project_path)

        # 1. 查找项目 ID
        proj_info = find_project_by_path(token, project_path)
        if not proj_info:
            print(f"\n  [{project_path}] 项目不存在，跳过", flush=True)
            skipped_projects += 1
            continue

        pid = proj_info['id']
        web_url = proj_info['http_url_to_repo']

        print(f"\n  [{project_path}] (branch={branch})", flush=True)

        # 2. 获取当日 commits（指定分支）
        commits_data = get_project_commits_for_date(token, pid, branch, date_str)
        if not commits_data:
            print(f"    无当日 commit", flush=True)
            continue

        print(f"    {len(commits_data)} 个 commit，开始采集...", flush=True)

        # 3. Clone 指定分支到持久化本地目录（不删）
        local_clone = REPOS_DIR / project_path
        try:
            clone_project(web_url, local_clone, branch)
        except Exception as e:
            print(f"    clone 失败: {e}", flush=True)
            continue

        try:
            # 4. 过滤无效 commit
            filtered = []
            for c in commits_data:
                filtered_c = filter_commit(c)
                if filtered_c:
                    filtered.append(filtered_c)

            if not filtered:
                print(f"    过滤后无有效 commit", flush=True)
                continue

            print(f"    {len(filtered)} 个有效 commit", flush=True)

            # 5. 创建输出目录
            out_proj = commits_dir / project_path
            out_proj.mkdir(parents=True, exist_ok=True)

            # 6. 保存 patch 文件
            for c in filtered:
                sha = c['sha']
                patch_path = out_proj / f"{sha}.patch"
                save_commit_patch(local_clone, sha, patch_path)

            # 7. 保存元数据（追加去重）
            meta_path = out_proj / "commits.json"
            existing = []
            if meta_path.exists():
                with open(meta_path) as f:
                    existing = json.load(f)

            existing_shas = {c['sha'] for c in existing}
            for c in filtered:
                if c['sha'] not in existing_shas:
                    existing.append(c)

            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            total_commits += len(filtered)
            processed_projects += 1

        finally:
            pass  # 持久 clone 保留不删（与 reporter.py 共享）

    print(f"\n[code-insights] ✅ 完成！", flush=True)
    print(f"  日期: {date_str}", flush=True)
    print(f"  处理项目数: {processed_projects}", flush=True)
    print(f"  跳过项目数: {skipped_projects}", flush=True)
    print(f"  commit 总数: {total_commits}", flush=True)
    print(f"  输出目录: {commits_dir}", flush=True)
    return processed_projects, total_commits


# ── 入口 ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 2:
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        date_str = parse_date(sys.argv[1])

    dry_run = '--dry-run' in sys.argv

    try:
        projects, commits = collect_commits(date_str, dry_run=dry_run)
        print(f"\n采集完成: {projects} 个项目，{commits} 条 commit")
    except Exception as e:
        print(f"\n[ERROR] {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
