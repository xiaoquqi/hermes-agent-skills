#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA 每日汇总报告生成器 v3
整合 JIRA 数据 + GitLab 真实 commit 代码行数
评分标准（基于真实代码贡献）：
  - 完成: 5分/个
  - 新建: 3分/个
  - GitLab 代码提交（按行数）: 100行=5分，上限15分
  - JIRA 评论（真实内容）: 2分/issue
  - GitLab 提到该 issue: 1分/issue（说明有代码关联）
阈值：≥20高 / ≥8中 / <8低
"""
import json, re, sys

# ============================================================
# 数据来源
# ============================================================
JIRA_CACHE = '/tmp/jira-2026-04-15.md'
GITLAB_CACHE = '/tmp/gitlab-commits-2026-04-15.json'

# GitLab author → JIRA assignee 映射
GL_TO_JIRA = {
    'zhangjiaqi': '张佳奇',
    'zhangtianjie9761': '张天洁',
    '张天洁': '张天洁',
    'wanghuixian': '王慧仙',
    '刘立祥': '刘立祥',
    'liulixiang9312': '刘立祥',
    'yongmengmeng8311': '雍蒙蒙',
    'lijianhai': '李建海',
    'guozhonghua': '郭中华',
}

# ============================================================
# 加载 GitLab 数据
# ============================================================
def load_gitlab():
    try:
        with open(GITLAB_CACHE) as f:
            raw = json.load(f)
    except:
        return {}

    # 归一化作者（大小写合并）
    by_person = {}
    for author, data in raw.get('by_person', {}).items():
        key = author.lower().strip()
        if key not in by_person:
            by_person[key] = {'name': author, 'commits': data['commits'], 'by_key': data['by_key']}
        else:
            by_person[key]['commits'].extend(data['commits'])
            for k, cs in data['by_key'].items():
                if k not in by_person[key]['by_key']:
                    by_person[key]['by_key'][k] = []
                by_person[key]['by_key'][k].extend(cs)
    return by_person

GITLAB = load_gitlab()

# ============================================================
# 解析 JIRA Markdown
# ============================================================
def parse_jira_md(path):
    with open(path) as f:
        content = f.read()

    issues = []
    parts = re.split(r'\n(?=### \[)', content)
    for part in parts:
        part = part.strip()
        if not part or part.startswith('# '):
            continue
        m = re.match(r'### \[([^\]]+)\]', part)
        if not m:
            continue
        key = m.group(1).strip()
        is_new = '🆕' in part
        is_done = '✅' in part
        lines = part.split('\n')

        summary = ''
        for line in lines[1:]:
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('**') and not line.startswith('#'):
                summary = line
                break

        status = ''.join(re.findall(r'状态:\s*([^\s|]+)', part)).strip()
        issuetype = ''.join(re.findall(r'类型:\s*([^\s|]+)', part)).strip()
        assignee = ''.join(re.findall(r'负责人:\s*([^\s|]+)', part)).strip()
        reporter = ''.join(re.findall(r'创建者:\s*([^\s|]+)', part)).strip()
        created = ''.join(re.findall(r'创建时间:\s*([\d-]+)', part)).strip()

        comments = []
        for line in lines:
            cm = re.match(r'- \*\*([^*]+)\*\* \(([^)]+)\):(.+)', line.strip())
            if cm:
                comments.append({
                    'author': cm.group(1).strip(),
                    'date': cm.group(2).strip(),
                    'body': cm.group(3).strip()
                })

        issues.append({
            'key': key, 'summary': summary, 'status': status,
            'issuetype': issuetype, 'assignee': assignee,
            'reporter': reporter, 'created': created,
            'is_new_today': is_new or '2026-04-15' in created,
            'is_done': is_done or status == 'Done',
            'comments': comments,
        })
    return issues

# ============================================================
# 评分
# ============================================================
def score_person(jira_issues, gitlab_data, person_jira_name):
    """计算个人评分和详情"""
    # JIRA 数据
    my_jira = [i for i in jira_issues if i['assignee'] == person_jira_name]
    done = [i for i in my_jira if i['is_done']]
    new_issues = [i for i in my_jira if i['is_new_today'] and not i['is_done']]
    in_prog = [i for i in my_jira if not i['is_done'] and not i['is_new_today']]

    # GitLab 数据
    gl_commits = []
    gl_by_key = {}
    for gkey, gdata in GITLAB.items():
        jira_name = GL_TO_JIRA.get(gkey, '')
        if jira_name == person_jira_name:
            gl_commits.extend(gdata['commits'])
            for k, cs in gdata['by_key'].items():
                if k not in gl_by_key:
                    gl_by_key[k] = []
                gl_by_key[k].extend(cs)

    # 真实评论（排除 gitlab bot）
    my_comments = []
    for issue in my_jira:
        for c in issue['comments']:
            author = c['author'].lower().strip()
            if author not in ('gitlab', 'girabot', 'jirabot', 'gbot', 'bot', 'system', ''):
                if len(c['body']) > 5:  # 排除纯图片/表情
                    my_comments.append((issue['key'], c))

    # GitLab 提到（某个 issue 有 gitlab commit）
    mentioned_issues = set()
    for k in gl_by_key.keys():
        mentioned_issues.add(k)

    # 评分
    score_done = len(done) * 5
    score_new = len(new_issues) * 3
    # GitLab 代码行评分：100行=5分，上限15分
    total_add = sum(c['additions'] for c in gl_commits)
    score_gitlab = min(15, int(total_add / 100) * 5) if gl_commits else 0
    score_comments = min(len(set(i[0] for i in my_comments)) * 2, 6)  # 最多3个issue的真实评论

    total = score_done + score_new + score_gitlab + score_comments

    if total >= 20:
        level = '🟢 高'
    elif total >= 8:
        level = '🟡 中'
    else:
        level = '🔴 低'

    return {
        'done': done, 'new': new_issues, 'in_prog': in_prog,
        'gl_commits': gl_commits, 'gl_by_key': gl_by_key,
        'my_comments': my_comments,
        'total_add': total_add,
        'score': total, 'level': level,
        'score_breakdown': {
            'done': (len(done), score_done),
            'new': (len(new_issues), score_new),
            'gitlab': (total_add, score_gitlab),
            'comments': (len(set(i[0] for i in my_comments)), score_comments),
        }
    }


# ============================================================
# 渲染报告
# ============================================================
def trunc(s, m=40):
    s = s.strip()
    return s[:m] + ('...' if len(s) > m else '')

def render_report(jira_issues):
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    all_done = [i for i in jira_issues if i['is_done']]
    all_new = [i for i in jira_issues if i['is_new_today']]

    lines = []
    lines.append(f"{'='*70}")
    lines.append(f"  📋 JIRA 每日汇总  2026-04-15")
    lines.append(f"{'='*70}")

    # 新建
    lines.append(f"\n📌 新建问题（共 {len(all_new)} 个）")
    if all_new:
        for i in all_new:
            lines.append(f"  + {i['key']} | {i.get('issuetype','?')} | {i['assignee'] or '?'} | {trunc(i.get('summary',''))}")
    else:
        lines.append("  无新建问题")

    # 完成
    lines.append(f"\n✅ 已完成问题（共 {len(all_done)} 个）")
    if all_done:
        for i in all_done:
            lines.append(f"  ✓ {i['key']} | {i['assignee'] or '?'} | {trunc(i.get('summary',''))}")
    else:
        lines.append("  无已完成问题")

    # GitLab 整体
    gl_total = sum(len(d['commits']) for d in GITLAB.values())
    gl_total_add = sum(c['additions'] for d in GITLAB.values() for c in d['commits'])
    lines.append(f"\n🔧 GitLab 整体  {gl_total} commits | +{gl_total_add} 行")

    # 按人拆解（评分从高到低）
    lines.append(f"\n{'='*70}")
    people = ['王嘉旺', '张佳奇', '张天洁', '刘立祥', '雍蒙蒙', '王慧仙', '李建海', '郭中华', '赵铭', '赵江波']
    scored = []
    for p in people:
        s = score_person(jira_issues, GITLAB, p)
        if s['done'] or s['new'] or s['gl_commits'] or s['my_comments']:
            scored.append((p, s))

    scored.sort(key=lambda x: -x[1]['score'])

    for person, s in scored:
        bd = s['score_breakdown']
        lines.append(f"\n{'─'*70}")
        lines.append(f"  👤 {person}")
        lines.append(f"  📈 完成 {bd['done'][0]}个(+{bd['done'][1]}) | 新建 {bd['new'][0]}个(+{bd['new'][1]}) | 评论 {bd['comments'][0]}个issue(+{bd['comments'][1]})")
        lines.append(f"  🔧 GitLab +{s['total_add']}行(+{bd['gitlab'][1]})")
        lines.append(f"  工作饱和度 {s['level']} | 综合评分 {s['score']}")

        if s['done']:
            lines.append(f"\n  ✅ 已完成（{len(s['done'])}个）")
            for i in s['done']:
                lines.append(f"     ✓ {i['key']} | {trunc(i.get('summary',''))}")

        if s['new']:
            lines.append(f"\n  🆕 新建（{len(s['new'])}个）")
            for i in s['new']:
                lines.append(f"     + {i['key']} | {trunc(i.get('summary',''))}")

        if s['gl_commits']:
            lines.append(f"\n  🔧 GitLab 代码（+{s['total_add']}行）")
            for k, cs in sorted(s['gl_by_key'].items(), key=lambda x: -sum(c['additions'] for c in x[1])):
                ca = sum(c['additions'] for c in cs)
                msgs = ' | '.join([c['message'][:30] for c in cs[:2]])
                lines.append(f"     [{k}] {len(cs)} commits (+{ca}) {msgs}")

        if s['my_comments']:
            lines.append(f"\n  💬 本人评论（{len(s['my_comments'])}条）")
            seen_keys = set()
            for key, c in s['my_comments'][:6]:
                if key not in seen_keys:
                    lines.append(f"     {key}: {trunc(c['body'], 50)}")
                    seen_keys.add(key)

    lines.append(f"\n{'='*70}")
    lines.append(f"  ⚠️  注意事项")
    lines.append(f"  - 王嘉旺: JIRA 5 done + 1 new，但 GitLab 无 commit，需确认")
    lines.append(f"  - 王慧仙: GitLab 有 REQ-5182 代码提交(+765行)，与 JIRA 评论不符")
    lines.append(f"  - GitLab 搜 commit 按 issue key 匹配，可能有遗漏（分支/未合并）")
    lines.append(f"  生成时间: {now}")
    lines.append(f"{'='*70}")

    return '\n'.join(lines)


def main():
    print("加载 JIRA 数据...")
    jira_issues = parse_jira_md(JIRA_CACHE)
    print(f"  JIRA issues: {len(jira_issues)}")

    print("加载 GitLab 数据...")
    print(f"  GitLab authors: {len(GITLAB)}")

    report = render_report(jira_issues)
    print("\n" + report)

    # 保存
    out = '/tmp/jira-report-final-2026-04-15.txt'
    with open(out, 'w') as f:
        f.write(report)
    print(f"\n✅ 报告已保存: {out}")


if __name__ == '__main__':
    main()
