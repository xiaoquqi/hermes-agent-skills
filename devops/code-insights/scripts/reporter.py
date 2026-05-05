#!/usr/bin/env python3
"""
Code Insights 报告生成器 - 使用 Claude Code 分析
每个 commit 生成 summary + detailed 两个报告文件
"""

import json
import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime
from functools import lru_cache
import tempfile
import os

# ── 配置 ──────────────────────────────────────────────
BASE_DIR    = Path.home() / ".hermes" / "code-insights"
COMMITS_DIR = BASE_DIR / "commits"
REPORT_DIR  = BASE_DIR / "reports" / "daily"
# 共享本地持久 clone 目录（与 collector.py 共用）
REPOS_DIR   = BASE_DIR / "repos"

# Git 配置 - 可以通过环境变量覆盖
GIT_BASE_URL = os.environ.get("GIT_BASE_URL", "http://192.168.10.254:20080")
GIT_USERNAME = os.environ.get("GIT_USERNAME", "")
GIT_TOKEN    = os.environ.get("GIT_TOKEN", "")

SUMMARY_PROMPT_TPL = """你是一个产品经理，从代码变更推断产品层面的影响。

## 输入
项目: {project}
分支: {branch}
提交: {sha}
作者: {author}
时间: {committed_date}
提交信息: {message}
涉及文件: {chunk_file}

## Patch（代码变更）
```diff
{patch}
```

## 输出要求（Summary 报告）

### 1. 产品改动
- 用一句话描述这个 commit 做了什么（面向产品/管理层）
- 说明改了什么模块/功能

### 2. 风险评估（爆炸半径）
- 影响范围：小 / 中 / 大
- 理由：
  - 改了哪些依赖模块：
  - 是否涉及核心业务流程：
  - 是否有回滚难度：
- 建议：（如果有）

## 约束
- 不超过 150 字
- 不重编，只基于 patch 内容推断
- 风险评估要具体，不要模糊
"""

DETAILED_PROMPT_TPL = """你是一个代码质量专家，严格审查代码变更质量，评估开发效率。

## 输入
项目: {project}
分支: {branch}
提交: {sha}
作者: {author}
时间: {committed_date}
提交信息: {message}
涉及文件: {chunk_file}

## Patch（代码变更）
```diff
{patch}
```

## 输出要求（Detailed 报告）

### 1. 代码质量评分
| 维度 | 评分（1-5）| 说明 |
|------|------------|------|
| 代码规范 | | |
| 可维护性 | | |
| 安全性 | | |
| 测试覆盖 | | |
| 综合评级 | | |

### 2. 主要问题
（最多3个，用代码位置引用）

### 3. 改进建议
（要具体可操作）

### 4. 效率评估
代码行数：+{added} / -{removed}
提交粒度：（合理 / 偏大 / 偏小，简单说明理由）
理论开发周期：（估算这次提交如果一次性写好需要多久，然后指出提交暴露的问题导致的额外消耗，充分暴露研发人员的能力短板。用数字说话，不要客气）
"""

# ── 工具函数 ──────────────────────────────────────────

MAX_TOKENS_INPUT = 100000  # Claude context window


def count_patch_stats(patch: str) -> tuple[int, int]:
    """统计 patch 增加/删除行数"""
    added = removed = 0
    for line in patch.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return added, removed


@lru_cache(maxsize=256)
def split_patch(patch: str) -> list[dict]:
    """
    将 patch 按文件拆分，文件过大时按逻辑块二次拆分。
    返回: [{"file": "path/file.py", "content": "...", "is_partial": bool}, ...]
    """
    files = []
    current_file = None
    current_lines = []

    for line in patch.splitlines(True):  # keepends
        if line.startswith("diff --git"):
            if current_file is not None:
                current_file["content"] = "".join(current_lines)
                files.append(current_file)
            fname = line.split(" b/", 1)[-1].strip() if " b/" in line else "unknown"
            current_file = {"file": fname, "content": "", "lines": 0}
            current_lines = []
        elif current_file is not None:
            current_lines.append(line)
            current_file["lines"] += 1

    if current_file is not None:
        current_file["content"] = "".join(current_lines)
        files.append(current_file)

    # 过滤掉辅助行（---、+++、index），保留实际 diff 内容
    for f in files:
        f["content"] = "".join(
            l for l in f["content"].splitlines(True)
            if not l.startswith(("--- ", "+++ ", "index "))
        )

    # 按文件大小降序排列，优先放满每个 chunk
    files.sort(key=lambda x: len(x["content"]), reverse=True)

    # 分块：保持文件完整，超大文件按 @@ 块拆分
    chunks = []
    current_chunk_files = []
    current_chunk_size = 0

    # 预留 prompt + 输出空间，约 2000 token
    max_patch_per_call = (MAX_TOKENS_INPUT - 2000) * 4  # 粗估：1 token ≈ 4 字符

    for f in files:
        fsize = len(f["content"])
        # 单文件超限时按 @@ 段落拆分
        if fsize > max_patch_per_call:
            sub_chunks = _split_by_hunks(f, max_patch_per_call)
            for sc in sub_chunks:
                chunks.append({"file": f["file"], "content": sc, "is_partial": True})
        elif current_chunk_size + fsize > max_patch_per_call:
            # 当前 chunk 满了，先保存
            if current_chunk_files:
                chunks.append(_merge_chunk_files(current_chunk_files))
            current_chunk_files = [f]
            current_chunk_size = fsize
        else:
            current_chunk_files.append(f)
            current_chunk_size += fsize

    if current_chunk_files:
        chunks.append(_merge_chunk_files(current_chunk_files))

    return chunks


def _split_by_hunks(file_info: dict, max_size: int) -> list[str]:
    """
    按 git diff 的 @@ 段落拆分，超大段落内部截断。
    """
    content = file_info["content"]
    fname = file_info["file"]
    hunks = []
    current_hunk = []

    for line in content.splitlines(True):
        if line.startswith("@@ "):
            if current_hunk:
                hunks.append("".join(current_hunk))
            current_hunk = [line]
        else:
            current_hunk.append(line)

    if current_hunk:
        hunks.append("".join(current_hunk))

    # 合并 hunk 到 chunk，不超限
    result = []
    current = f"=== {fname} (partial) ===\n"
    for hunk in hunks:
        if len(current) + len(hunk) > max_size:
            if current.strip():
                result.append(current)
            current = f"=== {fname} (partial) ===\n"
            # 单个 hunk 仍超限 → 截断（保留头尾各 1/3）
            if len(hunk) > max_size:
                cut = int(max_size * 0.6)
                result.append(hunk[:cut] + f"\n... [内容过长，已截断] ...\n")
                continue
        current += hunk

    if current.strip():
        result.append(current)
    return result


def _merge_chunk_files(files: list[dict]) -> dict:
    """将多个文件合并为一个 chunk"""
    combined = ""
    for f in files:
        combined += f"=== {f['file']} ===\n{f['content']}\n"
    return {
        "file": "\n".join(f["file"] for f in files),
        "content": combined,
        "is_partial": False
    }


def call_claude_code(prompt: str, timeout: int = 120) -> str:
    """调用 Claude Code 进行分析"""
    try:
        result = subprocess.run(
            ["claude", "--print", "--output-format", "text", "--no-session-persistence",
             "--dangerously-skip-permissions", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "CLAUDE_CODE_SIMPLE": "1"}
        )
        if result.returncode != 0:
            return f"[Claude Code 错误: {result.stderr.strip()}]"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[Claude Code 超时]"
    except FileNotFoundError:
        return "[Claude Code 未找到，请确保已安装]"
    except Exception as e:
        return f"[Claude Code 调用失败: {e}]"


def resolve_branch(project_path: str) -> str:
    """解析分支规则"""
    if project_path.startswith("atomy/"):
        return "qa"
    elif "CI-CD" in project_path or project_path == "hypermotion/CI-CD":
        return "master"
    return "saas_qa"


def get_git_url(project_path: str) -> str:
    """
    根据项目路径构建 Git URL
    支持通过 GIT_BASE_URL, GIT_USERNAME, GIT_TOKEN 环境变量配置
    """
    base = GIT_BASE_URL.rstrip("/")
    
    # 如果 base 是 git@ 开头，使用 SSH 格式
    if base.startswith("git@"):
        # e.g., git@gitlab.example.com:group/repo.git
        return f"{base}:{project_path}.git"
    elif base.startswith("http"):
        # HTTP/HTTPS 格式
        if GIT_TOKEN:
            # 尝试插入 token 到 URL
            parsed = base.split("://", 1)
            return f"{parsed[0]}://{GIT_TOKEN}@{parsed[1]}/{project_path}.git"
        return f"{base}/{project_path}.git"
    else:
        # 默认为 HTTPS
        return f"https://{base}/{project_path}.git"


def clone_and_prepare_repo(project_path: str, sha: str, patch_content: str, repos_base: Path = None) -> tuple[bool, str]:
    """
    使用 collector.py 已创建的持久化本地 clone（REPOS_DIR）。
    直接 checkout 到指定 SHA，无需重新 clone。
    Returns (success, work_dir_or_error_msg)
    """
    if repos_base is None:
        repos_base = REPOS_DIR
    work_dir = repos_base / project_path

    # 如果持久 clone 存在，直接 checkout 到目标 SHA（detached HEAD）
    if work_dir.exists() and (work_dir / ".git").exists():
        try:
            # 先确保 fetch 了目标 commit
            subprocess.run(
                ["git", "-C", str(work_dir), "fetch", "origin", sha, "--depth=50"],
                capture_output=True, text=True, timeout=60
            )
            # checkout 到目标 commit
            subprocess.run(
                ["git", "-C", str(work_dir), "checkout", sha, "--force"],
                capture_output=True, text=True, timeout=30
            )
            return True, str(work_dir)
        except subprocess.TimeoutExpired:
            return False, "Git checkout 超时"
        except Exception as e:
            return False, f"Git 操作失败: {e}"

    return False, f"持久 clone 不存在: {work_dir}（请先运行 collector.py）"


def _build_prompt(template: str, **kwargs) -> str:
    """填充 prompt 模板"""
    return template.format(**kwargs)


def process_commit(commit, patch_content, project_path, report_root, is_summary: bool, work_dir: str = None):
    """处理单个 commit，生成 summary 或 detailed 报告（支持大 patch 分块）"""
    sha     = commit["sha"]
    author  = commit["author_name"]
    date    = commit["committed_date"]
    message = commit["message"]
    branch  = resolve_branch(project_path)
    added, removed = count_patch_stats(patch_content)

    chunks = split_patch(patch_content)
    results = []

    for i, chunk in enumerate(chunks):
        chunk_note = f"（第 {i+1}/{len(chunks)} 部分）" if len(chunks) > 1 else ""

        if is_summary:
            prompt = _build_prompt(SUMMARY_PROMPT_TPL,
                project=project_path, branch=branch, sha=sha,
                author=author, committed_date=date, message=message,
                patch=chunk["content"], chunk_note=chunk_note,
                chunk_file=chunk["file"])
        else:
            prompt = _build_prompt(DETAILED_PROMPT_TPL,
                project=project_path, branch=branch, sha=sha,
                author=author, committed_date=date, message=message,
                patch=chunk["content"], added=added, removed=removed,
                chunk_note=chunk_note, chunk_file=chunk["file"])

        # 如果有 work_dir，添加上下文信息
        if work_dir:
            prompt = f"[工作目录: {work_dir}]\n\n{prompt}"

        result = call_claude_code(prompt)
        results.append(result)
        print(f"    {'['+str(i+1)+'/'+str(len(chunks))+']' if len(chunks)>1 else '  '} ✅")

    final = "\n\n---\n\n".join(results)

    out_dir = report_root / project_path
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "summary" if is_summary else "detailed"
    (out_dir / f"{sha}.{suffix}.md").write_text(
        f"# {suffix.title()} — {sha[:8]}{' (分块)' if len(chunks)>1 else ''}\n\n"
        f"**项目:** {project_path}\n"
        f"**作者:** {author}\n"
        f"**时间:** {date}\n"
        f"**分支:** {branch}\n"
        f"**提交:** {message}\n\n"
        f"---\n\n{final}"
    )

    return sha[:8], author, message, added, removed


# ── 主流程 ─────────────────────────────────────────────

def main(date_str: str):
    commits_base = COMMITS_DIR / date_str
    if not commits_base.exists():
        print(f"❌ 目录不存在: {commits_base}")
        return

    report_root = REPORT_DIR / date_str
    report_root.mkdir(parents=True, exist_ok=True)

    # 遍历所有 commits.json
    json_files = list(commits_base.rglob("commits.json"))
    if not json_files:
        print(f"❌ 找不到 commits.json: {commits_base}")
        return

    total = 0
    for json_file in json_files:
        project_path = str(json_file.parent.relative_to(commits_base))
        commits_data = json.loads(json_file.read_text())

        print(f"\n📦 {project_path}: {len(commits_data)} commits")

        # 为每个项目尝试 clone 一次（如果需要）
        work_dir = None
        clone_success = False

        for commit in commits_data:
            sha = commit["sha"]
            patch_file = json_file.parent / f"{sha}.patch"
            if not patch_file.exists():
                print(f"  ⚠️  patch 不存在: {sha[:8]}")
                continue

            patch_content = patch_file.read_text()
            chunks = split_patch(patch_content)  # 缓存，避免重复解析
            print(f"  🔍 {sha[:8]} | {commit['author_name']} | {len(patch_content.splitlines())} 行 patch")

            # 尝试 clone 并应用 patch（只尝试一次 per 项目）
            if not clone_success:
                success, result = clone_and_prepare_repo(
                    project_path, sha, patch_content
                )
                if success:
                    work_dir = result
                    clone_success = True
                    print(f"    📁 已克隆到: {work_dir}")
                else:
                    print(f"    ⚠️  Clone 失败，将使用 patch 直接分析: {result}")

            short_sha, author, msg, added, removed = process_commit(
                commit, patch_content, project_path, report_root, is_summary=True,
                work_dir=work_dir if clone_success else None
            )
            print(f"    Summary {'[分块]' if len(chunks)>1 else ''}")
            short_sha, author, msg, added, removed = process_commit(
                commit, patch_content, project_path, report_root, is_summary=False,
                work_dir=work_dir if clone_success else None
            )
            print(f"    Detailed {'[分块]' if len(chunks)>1 else ''} | +{added}/-{removed} | {msg[:50]}")
            total += 1

    print(f"\n✅ 完成！共处理 {total} 个 commit")
    print(f"📂 报告目录: {report_root}")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else "today"
    if date_arg == "today":
        date_arg = datetime.now().strftime("%Y-%m-%d")
    main(date_arg)
