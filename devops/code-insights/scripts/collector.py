#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collector v2 — 全量 clone + 按天归档 commits.json
流程：
  1. repos/{group}/{project}/ 已存在 → git pull
  2. 不存在 → git clone
  3. git log 提取当日 commits → commits.json
"""
import subprocess, json, os, sys
from datetime import datetime, timedelta
from pathlib import Path

# =========== 配置 ===========
BASE = Path.home() / ".hermes" / "code-insights"
REPOS = BASE / "repos"
COMMITS = BASE / "commits"

GL_URL = "http://192.168.10.254:20080"
GL_USER = "devops"
GL_PASS = "devops@HyperMotion"
GL_GROUP_ID = "36"

TOKEN = None

# 分支规则（与 clone_projects.sh 一致）
BRANCH_RULES = {
    "atomy": "qa",
    "CI-CD": "master",
}
DEFAULT_BRANCH = "saas_qa"

# 核心项目列表（先跑这些，范围待 Ray 确认后扩展）
PROJECTS = [
    {"group": "hypermotion", "project": "nezha",     "path_with_namespace": "hypermotion/nezha"},
    {"group": "hypermotion", "project": "mass",      "path_with_namespace": "hypermotion/mass"},
    {"group": "hypermotion", "project": "deploy",    "path_with_namespace": "hypermotion/deploy"},
    {"group": "atomy",       "project": "hamalv3",   "path_with_namespace": "atomy/hamalv3"},
]


# =========== GitLab API ===========
def get_token():
    import urllib.request
    data = json.dumps({"grant_type": "password", "username": GL_USER, "password": GL_PASS}).encode()
    req = urllib.request.Request(f"{GL_URL}/oauth/token", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["access_token"]


def api(path, token):
    import urllib.request
    url = f"{GL_URL}/api/v4{path}" if "?" in path else f"{GL_URL}/api/v4{path}?per_page=100"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def resolve_branch(path_with_namespace):
    for key, branch in BRANCH_RULES.items():
        if key in path_with_namespace:
            return branch
    return DEFAULT_BRANCH


def get_project_id(path_with_namespace, token):
    proj_name = path_with_namespace.rsplit("/", 1)[-1]
    result = api(f"/projects?search={proj_name}&per_page=50", token)
    for p in result:
        if p.get("path_with_namespace") == path_with_namespace:
            return p["id"]
    return None


def get_commits(project_id, branch, date_str, token):
    """获取指定日期范围内的 commits"""
    after = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=0)).strftime("%Y-%m-%d")
    until = date_str + "T23:59:59Z"
    commits = []
    page = 1
    while True:
        url = f"/projects/{project_id}/repository/commits?ref_name={branch}&since={after}&until={until}&per_page=100&page={page}"
        result = api(url, token)
        if not result:
            break
        if isinstance(result, dict):
            result = result.get("list", []) or []
        commits.extend(result)
        if len(result) < 100:
            break
        page += 1
    return commits


# =========== Git 操作 ===========
def ensure_repo(group, project, path_with_namespace, branch):
    """确保 repo 存在，必要时 clone 或 pull"""
    repo_dir = REPOS / group / project
    git_dir = repo_dir / ".git"

    if git_dir.exists():
        print(f"  → git pull ({branch})")
        run(["git", "fetch", "origin", branch], cwd=repo_dir)
        run(["git", "checkout", branch], cwd=repo_dir)
        run(["git", "pull", "origin", branch], cwd=repo_dir)
    else:
        print(f"  → git clone ({branch})")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        # 重写 clone URL（嵌入认证）
        clone_url = f"ssh://{GL_USER}:{GL_PASS.replace('@', '%40')}@192.168.10.254:20022/{path_with_namespace}.git"
        run(["git", "clone", "--branch", branch, "--single-branch", clone_url, str(repo_dir)])

    return repo_dir


def run(cmd, cwd=None):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"  [ERROR] {' '.join(cmd)}: {result.stderr.strip()}")
    return result


def get_commits_from_repo(repo_dir, date_str):
    """从本地 repo 提取当日 commits"""
    after = date_str
    until = date_str + "T23:59:59"

    result = run([
        "git", "log", "--format=%H|%an|%ae|%ai|%s",
        "--since", after, "--until", until,
        "--no-merges",
    ], cwd=repo_dir)

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 4)
        if len(parts) < 5:
            continue
        sha, author, email, committed_date, message = parts
        commits.append({
            "sha": sha,
            "author": author,
            "email": email,
            "date": committed_date,
            "message": message,
        })
    return commits


# =========== 主流程 ===========
def collect(date_str):
    print(f"\n{'='*60}")
    print(f"  Collector v2  {date_str}")
    print(f"{'='*60}")

    global TOKEN
    TOKEN = get_token()
    print("[OK] token")

    for proj in PROJECTS:
        group, project = proj["group"], proj["project"]
        branch = resolve_branch(proj["path_with_namespace"])
        print(f"\n[{group}/{project}] branch={branch}")

        # 1. 确保 repo 可用
        repo_dir = ensure_repo(group, project, proj["path_with_namespace"], branch)

        # 2. 获取远程 commits（用于过滤作者/日期）
        project_id = get_project_id(proj["path_with_namespace"], TOKEN)
        if project_id:
            remote_commits = get_commits(project_id, branch, date_str, TOKEN)
            print(f"  远程 API: {len(remote_commits)} commits")
        else:
            remote_commits = []
            print("  [WARN] 未找到 project_id")

        # 3. 从本地 repo 提取
        local_commits = get_commits_from_repo(repo_dir, date_str)
        print(f"  本地 repo: {len(local_commits)} commits")

        # 4. 过滤：去掉 gitlab/bot/system
        SKIP_AUTHORS = {"gitlab", "bot", "system", ""}
        filtered = [c for c in local_commits if c["author"].lower() not in SKIP_AUTHORS]

        # 用远程 API 结果补充统计信息（additions/deletions）
        remote_map = {c["id"][:8]: c for c in remote_commits}
        for c in filtered:
            sha8 = c["sha"][:8]
            if sha8 in remote_map:
                stats = remote_map[sha8].get("stats", {})
                c["additions"] = stats.get("additions", 0)
                c["deletions"] = stats.get("deletions", 0)
            else:
                c["additions"] = 0
                c["deletions"] = 0

        # 5. 保存
        out_dir = COMMITS / date_str / group / project
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "commits.json"

        with open(out_file, "w") as f:
            json.dump({
                "date": date_str,
                "group": group,
                "project": project,
                "branch": branch,
                "commits": filtered,
            }, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] {out_file}")
        for c in filtered:
            print(f"  {c['sha'][:8]}  {c['author']}  +{c['additions']}/-{c['deletions']}  {c['message'][:50]}")

        print(f"\n共 {len(filtered)} 条有效 commit")


if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else "today"
    if date_str == "today":
        date_str = datetime.now().strftime("%Y-%m-%d")
    collect(date_str)
