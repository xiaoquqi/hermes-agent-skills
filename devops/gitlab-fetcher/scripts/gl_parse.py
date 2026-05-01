#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab Daily Parser - 分析每个人的 commit，输出人类可读的日工作描述
输入：~/.hermes/product-data/raw/{DATE}/gitlab/{author}.json
输出：~/.hermes/product-data/parsed/{DATE}/gitlab/{author}.md

设计原则：
- 不分析单条 commit，按人合并分析（能看到效率问题）
- commit 相同的归并成一组（揭示重复提交问题）
- 输出：实现了/修复了/优化了/新增了 等工程师语言
"""
import json, os, sys
from pathlib import Path

# ── GitLab → JIRA 用户名映射 ──────────────────────────────────────────────
GL_TO_JIRA = {
    'zhangjiaqi':       '张佳奇',
    'zhangtianjie9761': '张天洁',
    'wanghuixian':      '王慧仙',
    'liulixiang9312':   '刘立祥',
    'yongmengmeng8311': '雍蒙蒙',
    'lijianhai':        '李建海',
    'guozhonghua':       '郭中华',
    'luoxiangru':       '罗湘儒',
    'wangjiawang':      '王佳望',
}

AUTHOR_ALIAS = {
    'yongmengmeng8311': '雍蒙蒙',
    'zhangtianjie9761': '张天洁',
    'liulixiang9312':   '刘立祥',
    'lijianhai':        '李建海',
    'guozhonghua':       '郭中华',
    'luoxiangru':       '罗湘儒',
}


def build_prompt(author, data, date_str):
    """构建 LLM 分析 prompt"""
    display_name = AUTHOR_ALIAS.get(author, author)
    total_commits = data['commit_count']
    total_add = data['total_additions']
    total_del = data['total_deletions']
    projects = data['projects']
    all_keys = data['all_jira_keys']
    groups = data['commit_groups']

    # 统计重复 commit
    repeated_groups = [g for g in groups if g['count'] > 1]

    lines = []
    lines.append(f"# GitLab 日工作分析")
    lines.append(f"")
    lines.append(f"**日期**：{date_str}")
    lines.append(f"**工程师**：{display_name}（{author}）")
    lines.append(f"**项目**：{' / '.join([p.split('/')[-1] for p in projects])}")
    lines.append(f"**代码量**：+{total_add} / -{total_del} 行")
    lines.append(f"**Commit 次数**：{total_commits} 次（{len(groups)} 个分组）")
    lines.append(f"**关联 JIRA**：{', '.join(all_keys) if all_keys else '无'}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    lines.append(f"## Commit 分组详情")
    lines.append(f"")
    for i, g in enumerate(groups, 1):
        keys_str = ', '.join(set(c['jira_keys'][0] if c['jira_keys'] else '' for c in data['commits'] if c['message'] == g['message'])) or '无 JIRA key'
        lines.append(f"### {i}. {g['message'][:70]}")
        lines.append(f"- **次数**：{g['count']} 次提交" + (" ⚠️ 重复提交" if g['count'] > 1 else ""))
        lines.append(f"- **代码量**：+{g['total_add']} / -{g['total_del']} 行")
        lines.append(f"- **项目**：{' / '.join([p.split('/')[-1] for p in g['projects']])}")
        lines.append(f"- **关联**：{keys_str}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## LLM 分析（请填写）")
    lines.append(f"")
    lines.append(f"**今日交付（用一句话描述）**：")
    lines.append(f"> 请描述这一天主要完成了什么功能/修复了什么问题/实现了什么改进。用「实现了xxx」「修复了xxx」「优化了xxx」开头。")
    lines.append(f"")
    lines.append(f"**技术关键词**（2-3个）：")
    lines.append(f"")
    lines.append(f"**效率评估**：")
    lines.append(f"- Commit 频率：")
    if total_commits <= 3:
        lines.append(f"  - 正常（{total_commits} 次提交，粒度合理）")
    elif repeated_groups:
        lines.append(f"  - ⚠️ 碎片化：{total_commits} 次提交，其中 {len(repeated_groups)} 组为重复 commit")
    else:
        lines.append(f"  - 正常偏高（{total_commits} 次提交，建议适当合并）")
    lines.append(f"- 代码量评估：")
    if total_add >= 300:
        lines.append(f"  - 正常（+{total_add} 行，匹配工作时长）")
    elif total_add < 50:
        lines.append(f"  - ⚠️ 过低：仅 +{total_add} 行，可能存在阻塞或工作不饱和")
    else:
        lines.append(f"  - 偏低（+{total_add} 行，需确认工作是否饱和）")
    lines.append(f"- 重复 commit：")
    if repeated_groups:
        for g in repeated_groups:
            lines.append(f"  - ⚠️ 「{g['message'][:40]}」重复 {g['count']} 次，建议 squash 后再合并")
    else:
        lines.append(f"  - 无")
    lines.append(f"")
    lines.append(f"**与 JIRA 关联**：")
    if all_keys:
        lines.append(f"- 关联 {len(all_keys)} 个 JIRA：{', '.join(all_keys)}")
    else:
        lines.append(f"- ⚠️ 无任何 JIRA key 关联（{total_commits} 次提交全部游离）")
    lines.append(f"")

    return '\n'.join(lines)


def parse_date(date_str):
    return date_str


def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitLab Daily Parser")
    parser.add_argument('date', nargs='?', default=None, help='日期 yyyy-MM-dd')
    parser.add_argument('--dry-run', action='store_true', help='只打印 prompt，不写文件')
    parser.add_argument('--author', help='只分析指定作者')
    args = parser.parse_args()

    # 日期
    from datetime import datetime, timedelta
    _HC_PATH = Path(__file__).parent.parent.parent / "holiday-checker" / "scripts" / "holiday_check.py"
    if _HC_PATH.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("holiday_checker", _HC_PATH)
        _hc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_hc)
        prev_workday = _hc.prev_workday_fast
    else:
        def prev_workday(dt):
            d = dt - timedelta(days=1)
            while d.weekday() >= 5:
                d -= timedelta(days=1)
            return d

    if args.date:
        date_str = args.date
    else:
        date_str = prev_workday(datetime.now()).strftime('%Y-%m-%d')

    # 读取 RAW 数据
    raw_dir = Path.home() / ".hermes" / "product-data" / "raw" / date_str / "gitlab"
    if not raw_dir.exists():
        print(f"[gl_parse] 错误：找不到 RAW 数据 {raw_dir}")
        print(f"请先运行：python3 gl_daily.py {date_str}")
        sys.exit(1)

    # 输出目录
    out_dir = Path.home() / ".hermes" / "product-data" / "parsed" / date_str / "gitlab"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 遍历所有 author JSON
    json_files = sorted(raw_dir.glob("*.json"))

    if args.author:
        json_files = [f for f in json_files if f.stem == args.author]
        if not json_files:
            print(f"[gl_parse] 错误：找不到 author {args.author}")
            sys.exit(1)

    print(f"[gl_parse] date={date_str}, authors={len(json_files)}", flush=True)

    for f in json_files:
        if f.name.startswith('_') or f.name == '_meta.json':
            continue
        author = f.stem
        with open(f, encoding='utf-8') as fp:
            data = json.load(fp)

        prompt = build_prompt(author, data, date_str)

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"=== {author} ===")
            print(f"{'='*60}")
            print(prompt)
            continue

        out_path = out_dir / f"{author}.md"
        with open(out_path, 'w', encoding='utf-8') as fp:
            fp.write(prompt)
        print(f"  ✅ {out_path}", flush=True)

    if not args.dry_run:
        print(f"\n[gl_parse] ✅ 完成：{len(json_files)} 个 author")
        print(f"[gl_parse] 💡 下一步：请编辑 {out_dir}/ 下的 .md 文件，填写 LLM 分析结果")


if __name__ == '__main__':
    main()
