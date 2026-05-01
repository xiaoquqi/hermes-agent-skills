#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab Commit Patch 采集脚本

clone 项目到本地，用 git 命令提取 patch，按天存储。

输出结构：
  ~/.hermes/code-insights/commits/{date}/{project}/
  ├── commits.json       # commit 元数据
  └── {commit_id}.patch # 每个 commit 的完整 diff
"""
import urllib.request
import urllib.error
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
CACHE_DIR = Path.home() / ".hermes" / "gitlab-cache"  # 复用已有 token 缓存

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


def get_group_projects(token):
    """获取 hypermotion 组下所有项目"""
    projects = []
    for page in range(1, 30):
        try:
            result = api(f'/groups/{GL_GROUP_ID}/projects?page={page}&order_by=last_activity_at', token)
            if not result:
                break
            projects.extend([p for p in result if p['path_with_namespace'].startswith('hypermotion/')])
            if len(result) < 100:
                break
        except Exception as e:
            print(f'  [WARN] group projects page {page}: {e}', flush=True)
            break
    return projects


def get_project_commits_for_date(token, project_id, project_name, date_str):
    """获取项目在指定日期的 commits（通过 commits API）"""
    from urllib.parse import quote
    after = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    until_encoded = quote(f"{date_str} 23:59:59", safe='')
    commits = []
    for page in range(1, 30):
        try:
            url = (f'/projects/{project_id}/repository/commits'
                   f'?all=true&since={after}&until={until_encoded}&page={page}')
            result = api(url, token)
            if not result:
                break
            if isinstance(result, dict):
                result = result.get('list', []) or []
            # 过滤出当日日期的 commit
            filtered_this_page = 0
            for c in result:
                committed_date = (c.get('committed_date', '') or '')[:10]
                if committed_date == date_str:
                    commits.append(c)
                    filtered_this_page += 1
            if len(result) < 100:
                break
        except Exception:
            break
    return commits


# ── Git 操作 ─────────────────────────────────────────────────────────────────
def clone_project(project_url, clone_dir, depth=100):
    """Shallow clone 项目"""
    from urllib.parse import urlparse, urlunparse, quote
    # 修正 clone URL：替换不可达的 host，并嵌入认证信息
    # 项目 http_url_to_repo 可能是 http://office.oneprocloud.com:20080/...
    # GL_URL 格式：http://192.168.10.254:20080
    gl_netloc = urlparse(GL_URL).netloc  # e.g. "192.168.10.254:20080"
    parsed = urlparse(project_url)
    # 嵌入认证：username = GL_USER, password = GL_PASS (URL-encoded)
    auth_netloc = f"{quote(GL_USER, safe='')}:{quote(GL_PASS, safe='')}@{gl_netloc}"
    project_url = urlunparse(('http', auth_netloc, parsed.path, parsed.params, parsed.query, ''))

    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    clone_dir.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        'git', 'clone',
        '--depth', str(depth),
        '--no-single-branch',
        '--bare',  # bare 模式不需要 worktree，节省空间
        project_url,
        str(clone_dir)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"clone 失败: {result.stderr.strip()}")
    return clone_dir


def get_commits_for_date(clone_dir, date_str):
    """获取指定日期的所有 commit 元数据"""
    since = f"{date_str} 00:00:00"
    until = f"{date_str} 23:59:59"

    cmd = [
        'git', '-C', str(clone_dir), 'log',
        '--since', since,
        '--until', until,
        '--format', '%H|%an|%ae|%ad|%s',
        '--date=iso',
        '--all'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('|', 4)
        if len(parts) < 5:
            continue
        sha, author_name, author_email, committed_date, message = parts
        commits.append({
            'sha': sha,
            'author_name': author_name,
            'author_email': author_email,
            'committed_date': committed_date.strip(),
            'message': message.strip()[:200],
        })
    return commits


def save_commit_patch(clone_dir, sha, output_patch_path):
    """保存单个 commit 的 patch 文件"""
    # 获取 patch（不含 commit 信息，只有 diff）
    cmd = ['git', '-C', str(clone_dir), 'show', sha, '--format=', '--patch']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    # 如果没有 patch 内容（binary 文件等），写入空文件
    output_patch_path.write_text(result.stdout or '')


# ── 主采集逻辑 ────────────────────────────────────────────────────────────────
def collect_commits(date_str, dry_run=False):
    """
    采集指定日期的所有 GitLab commit patch 和元数据
    """
    print(f"[code-insights] date={date_str}", flush=True)

    token = get_token()
    print("[code-insights] token ok", flush=True)

    projects = get_group_projects(token)
    print(f"[code-insights] found {len(projects)} projects in group {GL_GROUP_ID}", flush=True)

    commits_dir = BASE_DIR / "commits" / date_str
    commits_dir.mkdir(parents=True, exist_ok=True)

    total_commits = 0
    processed_projects = 0

    for proj in projects:
        pid = proj['id']
        pname = proj['path_with_namespace']
        web_url = proj['http_url_to_repo']

        print(f"\n  [{pname}]", flush=True)

        # 1. 直接用 commits API 获取当日 commits
        commits_data = get_project_commits_for_date(token, pid, pname, date_str)
        if not commits_data:
            print(f"    无当日 commit，跳过", flush=True)
            continue

        print(f"    {len(commits_data)} 个 commit，开始采集...", flush=True)

        # 2. Clone 到临时目录
        tmp_clone = Path(f"/tmp/code-insights-{date_str}-{pname.replace('/', '_')}")
        try:
            clone_project(web_url, tmp_clone)
        except Exception as e:
            print(f"    clone 失败: {e}", flush=True)
            continue

        try:
            # 3. 直接用 API 返回的数据，过滤无效 commit
            filtered = []
            for c in commits_data:
                author = (c.get('author_name', '') or '').lower()
                msg = (c.get('message', '') or '').split('\n')[0].strip()
                if author in ('gitlab', 'bot', 'system', ''):
                    continue
                if re.match(r"^Merge branch", msg):
                    continue
                filtered.append({
                    'sha': c.get('id', '') or '',
                    'author_name': c.get('author_name', '') or '',
                    'author_email': c.get('author_email', '') or '',
                    'committed_date': (c.get('committed_date', '') or '')[:19],
                    'message': msg[:200],
                })

            if not filtered:
                print(f"    过滤后无有效 commit，跳过", flush=True)
                continue

            print(f"    {len(filtered)} 个有效 commit", flush=True)

            # 5. 创建输出目录
            out_proj = commits_dir / pname
            out_proj.mkdir(parents=True, exist_ok=True)

            # 6. 保存 patch 文件
            for c in filtered:
                sha = c['sha']
                patch_path = out_proj / f"{sha}.patch"
                save_commit_patch(tmp_clone, sha, patch_path)

            # 7. 保存元数据
            meta_path = out_proj / "commits.json"
            existing = []
            if meta_path.exists():
                with open(meta_path) as f:
                    existing = json.load(f)

            # 合并去重
            existing_shas = {c['sha'] for c in existing}
            for c in filtered:
                if c['sha'] not in existing_shas:
                    existing.append(c)

            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            total_commits += len(filtered)
            processed_projects += 1

        finally:
            # 清理临时 clone
            if tmp_clone.exists():
                shutil.rmtree(tmp_clone)

    print(f"\n[code-insights] ✅ 完成！", flush=True)
    print(f"  日期: {date_str}", flush=True)
    print(f"  处理项目数: {processed_projects}", flush=True)
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
