#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研发日报生成器 v5 — 产品变化 + 每人具体产出 + 工作饱满度评价

报告结构（2026-04-16 确认）：
  1.【产品层面】→ 整体数据 + 趋势对比（今日 vs 前几天）
  2.【每人产出】→ 整体数据（所有人汇总） + 每人详情（具体做了什么 + 数据佐证 + 饱满度评价）
  3. 用数据证明：AI时代开发效率应该更高，实际产出是否匹配

饱满度判断标准（AI时代）：
  饱满：GL行 ≥ 300 或 Done ≥ 2 或 (GL行 ≥ 100 且质量无问题)
  一般：100 ≤ GL行 < 300，无严重质量问题
  偏低：GL行 < 100 或 连续无GitLab 或 大量重复commit
"""
import json, re, sys, os, glob
from datetime import datetime, timedelta
from collections import defaultdict

PYTHON = '/opt/anaconda3/bin/python3'
DATE = sys.argv[1] if len(sys.argv) > 1 else None
if not DATE:
    yesterday = datetime.now()
    wd = yesterday.weekday()
    offset = 1 if wd > 0 else 3
    yesterday = yesterday.replace(day=yesterday.day - offset)
    DATE = yesterday.strftime('%Y-%m-%d')

print(f"生成日期: {DATE}")

REPORT_DIR  = os.path.expanduser('~/.hermes/reports/daily/')
JIRA_CACHE  = f'/tmp/jira-{DATE}.md'
GL_CACHE    = f'/tmp/gitlab-commits-{DATE}.json'
os.makedirs(REPORT_DIR, exist_ok=True)

if not os.path.exists(JIRA_CACHE):
    print("抓取 JIRA 数据...")
    os.system(f"{PYTHON} ~/.hermes/skills/jira-daily-summary/scripts/jira_to_md.py {DATE} -o {JIRA_CACHE} > /dev/null 2>&1")

if not os.path.exists(GL_CACHE):
    print("抓取 GitLab 数据...")
    os.system(f"{PYTHON} ~/.hermes/skills/jira-daily-summary/scripts/gitlab_commits.py {DATE} > /dev/null 2>&1")

# ============================================================
# 数据加载
# ============================================================
def load_jira(path):
    """
    从 jira_to_md.py 生成的 markdown 中解析 JIRA issues。
    优先使用底部的汇总表（格式干净）补充 summary。
    """
    with open(path) as f:
        content = f.read()

    # ---- Step 1: 从汇总表获取干净 summary ----
    # 格式：| KEY | 摘要 | 类型 | 状态 | 负责人 | 创建时间 | 评论数 | 工时数 |
    summary_map = {}
    tbl_match = re.search(r'(?<=## 汇总\n\n)\| Key \| .*?\n\|[-| ]+\|([^\n]+\n)*', content)
    if tbl_match:
        for row in re.findall(r'\|\s*([A-Z]+-\d+)\s*\|\s*([^|]+?)\s*\|', tbl_match.group()):
            # 用贪婪模式：取 key 之后、下一个 | 之前的所有内容作为 summary
            summary_map[row[0].strip()] = row[1].strip()

    # ---- Step 2: 按 issue 分块解析 ----
    issues = []
    for part in re.split(r'\n(?=### \[)', content):
        part = part.strip()
        if not part or '### [' not in part:
            continue
        m = re.match(r'### \[([^\]]+)\]', part)
        if not m:
            continue
        key = m.group(1).strip()
        lines = part.split('\n')

        # 提取各字段（优先汇总表的 summary）
        status    = ''.join(re.findall(r'状态:\s*([^\s|]+)', part)).strip()
        issuetype = ''.join(re.findall(r'类型:\s*([^\s|]+)', part)).strip()
        assignee  = ''.join(re.findall(r'负责人:\s*([^\s|]+)', part)).strip()
        reporter  = ''.join(re.findall(r'创建者:\s*([^\s|]+)', part)).strip()
        created   = ''.join(re.findall(r'创建时间:\s*([\d-]+)', part)).strip()

        # summary：汇总表 > 自己解析（跳过 commit 引用行）
        summary = summary_map.get(key, '')
        if not summary:
            for l in lines[1:]:
                ls = l.strip()
                if not ls or ls.startswith('-') or ls.startswith('**') or ls.startswith('#'):
                    continue
                # 跳过 commit 引用行
                if re.match(r'\*\*gitlab\*\*', ls) or re.match(r'!\w+', ls) or '|http' in ls:
                    continue
                summary = ls
                break

        is_new  = '🆕' in part or DATE in created
        is_done = '✅' in part or status == 'Done'

        comments = [
            {'author': cm.group(1).strip(), 'date': cm.group(2).strip(), 'body': cm.group(3).strip()}
            for line in lines
            if (cm := re.match(r'- \*\*([^*]+)\*\* \(([^)]+)\):(.+)', line.strip()))
        ]

        issues.append({
            'key': key, 'summary': summary, 'status': status,
            'issuetype': issuetype, 'assignee': assignee,
            'reporter': reporter, 'created': created,
            'is_new': is_new, 'is_done': is_done,
            'comments': comments,
        })
    return issues

def load_gitlab(path):
    try:
        with open(path) as f:
            raw = json.load(f)
    except:
        return {}
    by_person = {}
    for author, data in raw.get('by_person', {}).items():
        key = author.lower().strip()
        commits = data['commits']
        by_key  = data['by_key']
        if key not in by_person:
            by_person[key] = {'name': author, 'commits': commits, 'by_key': by_key}
        else:
            shas = {c['sha'] for c in by_person[key]['commits']}
            for c in commits:
                if c['sha'] not in shas:
                    by_person[key]['commits'].append(c)
                    shas.add(c['sha'])
            for k, cs in by_key.items():
                if k not in by_person[key]['by_key']:
                    by_person[key]['by_key'][k] = []
                ks = {c['sha'] for c in by_person[key]['by_key'][k]}
                for c in cs:
                    if c['sha'] not in ks:
                        by_person[key]['by_key'][k].append(c)
                        ks.add(c['sha'])
    return by_person

print("加载数据...")
JIRA_ISSUES = load_jira(JIRA_CACHE)
GITLAB      = load_gitlab(GL_CACHE)
print(f"  JIRA: {len(JIRA_ISSUES)} issues,  GitLab: {len(GITLAB)} authors")

# ============================================================
# 人员配置
# ============================================================
DEVS = {'张佳奇', '张天洁', '刘立祥', '雍蒙蒙', '王慧仙', '李建海', '郭中华', '赵江波', '王嘉旺', '赵铭'}

GL_TO_JIRA = {
    'zhangjiaqi':          '张佳奇',
    'zhangtianjie9761':     '张天洁',
    '张天洁':               '张天洁',
    'wanghuixian':         '王慧仙',
    '刘立祥':               '刘立祥',
    'liulixiang9312':      '刘立祥',
    'yongmengmeng8311':    '雍蒙蒙',
    'lijianhai':           '李建海',
    'guozhonghua':         '郭中华',
}

# ============================================================
# 历史数据（读取前5天）
# ============================================================
def load_history(days=5):
    """返回 list of {date, gl_total_add, gl_total_commits, done_count, new_count, persons}"""
    history = []
    for i in range(1, days + 1):
        d = datetime.strptime(DATE, '%Y-%m-%d') - timedelta(days=i)
        dstr = d.strftime('%Y-%m-%d')
        path = os.path.join(REPORT_DIR, f'{dstr}.txt')
        if not os.path.exists(path):
            continue
        with open(path) as f:
            content = f.read()
        # 提取汇总数据
        total_add    = sum(int(x) for x in re.findall(r'GitLab.*?\+(\d+)行', content))
        total_commits = sum(int(x) for x in re.findall(r'GitLab.*?(\d+)次?提交', content))
        done_m       = re.search(r'JIRA 完成（(\d+)', content)
        new_m        = re.search(r'JIRA 新建（(\d+)', content)
        persons_data = {}
        for name in DEVS:
            sec = re.search(rf'👤 {re.escape(name)}.*?(?=\n  ─|$\n{{2}}【|\n{{3}}=)', content, re.DOTALL)
            if sec:
                gl_m  = re.search(r'GitLab.*?\+(\d+)行', sec.group())
                dup_m = re.search(r'(\d+) 次重复 commit', sec.group())
                nog_m = re.search(r'无 GitLab 提交|⚠️ 无 GitLab', sec.group())
                persons_data[name] = {
                    'gl_add':  int(gl_m.group(1)) if gl_m else 0,
                    'dup':    int(dup_m.group(1)) if dup_m else 0,
                    'no_gl':  bool(nog_m),
                }
        history.append({
            'date':       dstr,
            'gl_total_add':    total_add,
            'gl_total_commits': total_commits,
            'done':       int(done_m.group(1)) if done_m else 0,
            'new':        int(new_m.group(1)) if new_m else 0,
            'persons':    persons_data,
        })
    return history

HISTORY = load_history(5)

# ============================================================
# 分析函数
# ============================================================
def real_comments(issue_comments):
    for c in issue_comments:
        a = c['author'].lower().strip()
        if a in ('gitlab', 'girabot', 'jirabot', 'gbot', 'bot', 'system', ''):
            continue
        if len(c['body']) <= 5 or c['body'].startswith('!image'):
            continue
        yield c

def person_data(name):
    my_jira   = [i for i in JIRA_ISSUES if i['assignee'] == name]
    done      = [i for i in my_jira if i['is_done']]
    new_iss   = [i for i in my_jira if i['is_new']]

    gl_commits, gl_by_key = [], {}
    for gk, gd in GITLAB.items():
        if GL_TO_JIRA.get(gk) == name:
            gl_commits.extend(gd['commits'])
            for k, cs in gd['by_key'].items():
                gl_by_key.setdefault(k, []).extend(cs)

    my_comments = []
    for iss in my_jira:
        for c in real_comments(iss['comments']):
            my_comments.append((iss['key'], c))

    total_add = sum(c['additions'] for c in gl_commits)
    return {
        'done':      done,
        'new':       new_iss,
        'gl_commits': gl_commits,
        'gl_by_key': gl_by_key,
        'comments':  my_comments,
        'total_add': total_add,
        'score_done': len(done) * 5,
        'score_new':  len(new_iss) * 3,
        'score_gl':   min(15, int(total_add / 100) * 5),
        'score_cmts': min(len(set(i[0] for i in my_comments)) * 2, 6),
    }

def quality_check(gl_commits):
    if not gl_commits:
        return {'commits': 0, 'dup': 0, 'test_files': 0, 'low_output': False, 'findings': []}
    msgs = {}
    for c in gl_commits:
        msg = c['message'].split('\n')[0].strip()
        msgs[msg] = msgs.get(msg, 0) + 1
    dup = sum(cnt for msg, cnt in msgs.items() if cnt >= 2)
    low = any(c['additions'] < 5 for c in gl_commits)
    tests = sum(1 for c in gl_commits for f in c.get('files', [])
                 if 'test_' in f or '_spec.' in f or '/tests/' in f)
    findings = []
    if dup > 0:    findings.append(f"重复commit {dup}次")
    if tests == 0: findings.append("无测试文件")
    if low:        findings.append("存在极低产出commit(<5行)")
    return {'commits': len(gl_commits), 'dup': dup, 'test_files': tests,
            'low_output': low, 'findings': findings}

def workload_judge(total_add, done_count, new_count, gl_commits, qa):
    """
    饱满度评价（AI时代标准）：
      饱满：GL行≥300 或 Done≥2 或 (GL行≥100且质量无问题)
      一般：100≤GL行<300，质量基本正常
      偏低：GL行<100 或 无GitLab 或 严重质量问题（大量重复commit）
    """
    has_gl = total_add > 0 or len(gl_commits) > 0
    if not has_gl:
        return "⚠️ 偏低", "无代码提交，无法评估实际产出"
    if total_add >= 300 or done_count >= 2:
        if qa['findings']:
            return "✅ 饱满（有待改进）", f"产出量足({total_add}行)，但{qa['findings'][0]}"
        return "✅ 饱满", f"产出量充足({total_add}行，{done_count}个完成)"
    if total_add >= 100:
        if qa['findings']:
            return "🔄 一般", f"产出量基本正常，但{qa['findings'][0]}"
        return "🔄 一般", f"产出量基本正常({total_add}行)"
    if qa['dup'] >= 3 or qa['low_output']:
        return "⚠️ 偏低", f"产出量少({total_add}行)，质量问题突出"
    return "⚠️ 偏低", f"产出量偏少({total_add}行)，不符合AI时代正常开发节奏"

def trend_streak(name, field, days=5):
    """某人在最近N天中连续出现该field的天数（从最新往前数）"""
    if name not in HISTORY:
        return 0
    # HISTORY newest-first，取最近days天
    recent = HISTORY[:days]
    streak = 0
    for d in reversed(recent):
        pd = d['persons'].get(name, {})
        if pd.get(field):
            streak += 1
        else:
            break
    return streak

def work_description(gl_by_key, gl_commits):
    """生成描述性文字：具体在哪个issue上改了什么"""
    if not gl_by_key:
        return []
    result = []
    for key, commits in sorted(gl_by_key.items(), key=lambda x: -sum(c['additions'] for c in x[1])):
        total = sum(c['additions'] for c in commits)
        msgs = []
        for c in commits:
            msg = c['message'].split('\n')[0].strip()
            msg = re.sub(r'^(Resolved|Add|Fix|Update|Merge|Bump) ', '', msg)
            if msg and msg not in msgs:
                msgs.append(msg)
        main = msgs[0] if msgs else '(无描述)'
        extra = f"，另{len(msgs)-1}次小改" if len(msgs) > 1 else ""
        result.append({'issue': key, 'desc': main, 'extra': extra,
                       'lines': total, 'count': len(commits)})
    return result

# ============================================================
# 生成报告
# ============================================================
def render_report():
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    all_done = [i for i in JIRA_ISSUES if i['is_done']]
    all_new  = [i for i in JIRA_ISSUES if i['is_new']]

    # 团队整体 GitLab 数据
    team_gl_add     = sum(sum(c['additions'] for c in gd['commits']) for gd in GITLAB.values())
    team_gl_commits = sum(len(gd['commits']) for gd in GITLAB.values())

    # 历史均值
    hist_gl_adds    = [h['gl_total_add'] for h in HISTORY]
    hist_gl_commits = [h['gl_total_commits'] for h in HISTORY]
    avg_gl_add      = sum(hist_gl_adds) / len(hist_gl_adds) if hist_gl_adds else 0
    avg_commits     = sum(hist_gl_commits) / len(hist_gl_commits) if hist_gl_commits else 0

    # ============================================================
    # 头部
    # ============================================================
    lines.append("=" * 70)
    lines.append(f"  研发日报 {DATE}   生成: {now}")
    lines.append("=" * 70)

    # ============================================================
    # 【第一部分】产品层面 — 整体数据 + 趋势
    # ============================================================
    lines.append("\n【产品层面变化】")
    lines.append(f"\n  📊 今日整体数据：")
    lines.append(f"     GitLab: +{team_gl_add} 行 / {team_gl_commits} 次提交")
    lines.append(f"     JIRA:   新建 {len(all_new)} 个 | 完成 {len(all_done)} 个")

    # 趋势对比
    if HISTORY:
        lines.append(f"\n  📈 趋势对比（今日 vs 前几天日均）：")
        lines.append(f"     GitLab 产出：今日 +{team_gl_add} 行 | 前几天日均 +{avg_gl_add:.0f} 行"
                     + (" ▲ 偏高" if team_gl_add > avg_gl_add * 1.2 else (" ▼ 偏低" if team_gl_add < avg_gl_add * 0.7 else " → 持平")))
        diff_commits = team_gl_commits - avg_commits
        lines.append(f"     提交次数：今日 {team_gl_commits} 次 | 前几天日均 {avg_commits:.0f} 次"
                     + (f" ▲ +{diff_commits:.0f}" if diff_commits > 2 else (f" ▼ {diff_commits:.0f}" if diff_commits < -2 else " → 持平")))
    else:
        lines.append(f"\n  📈 趋势对比：无历史数据（明日开始有对比）")

    # JIRA 新建/完成的 issue 列表（说清楚是什么）
    if all_done:
        by_type = defaultdict(list)
        for i in all_done:
            by_type[i.get('issuetype', '其他')].append(i)
        lines.append(f"\n  ✅ 完成详情：")
        for t, iss in by_type.items():
            for i in iss:
                summary = i.get('summary', '').strip()
                assignee = i.get('assignee', '')
                if summary:
                    lines.append(f"     [{t}] {summary}（{assignee}）")
                else:
                    lines.append(f"     [{t}] {i['key']}（{assignee}）")

    if all_new:
        by_type = defaultdict(list)
        for i in all_new:
            by_type[i.get('issuetype', '其他')].append(i)
        lines.append(f"\n  🆕 新建详情：")
        for t, iss in by_type.items():
            for i in iss:
                summary = i.get('summary', '').strip()
                reporter = i.get('reporter', '')
                if summary:
                    lines.append(f"     [{t}] {summary}（{reporter}）")
                else:
                    lines.append(f"     [{t}] {i['key']}（{reporter}）")

    # ============================================================
    # 【第二部分】每人产出详情
    # ============================================================
    lines.append("\n" + "=" * 70)
    lines.append("\n【每人产出详情】")

    # --- 2a. 团队整体汇总表 ---
    lines.append(f"\n  📊 团队整体（{len([n for n in DEVS if person_data(n)['total_add'] > 0 or person_data(n)['done'] or person_data(n)['new']])} 人有产出）：")
    lines.append(f"  {'姓名':<8} {'完成':>4} {'新建':>4} {'GL行':>6} {'提交':>4} {'问题':<20} 饱满度")
    lines.append(f"  {'-'*8} {'-'*4} {'-'*4} {'-'*6} {'-'*4} {'-'*20} {'-'*10}")

    scored = []
    for name in DEVS:
        d = person_data(name)
        if not d['done'] and not d['new'] and not d['gl_commits'] and not d['comments']:
            continue
        qa   = quality_check(d['gl_commits'])
        total = d['score_done'] + d['score_new'] + d['score_gl'] + d['score_cmts']
        judge, reason = workload_judge(d['total_add'], len(d['done']), len(d['new']), d['gl_commits'], qa)
        qa_str = '; '.join(qa['findings']) if qa['findings'] else '—'

        scored.append({
            'name': name, 'done': len(d['done']), 'new': len(d['new']),
            'gl': d['total_add'], 'commits': len(d['gl_commits']),
            'qa_str': qa_str, 'judge': judge, 'reason': reason,
            'score': total,
            'done_issues': d['done'], 'new_issues': d['new'],
            'gl_by_key': d['gl_by_key'], 'comments': d['comments'],
            'qa': qa,
        })

    scored.sort(key=lambda x: -x['score'])

    for s in scored:
        gl_str = f"+{s['gl']}" if s['gl'] > 0 else '—'
        qa_short = s['qa_str'][:18] + '..' if len(s['qa_str']) > 20 else s['qa_str']
        lines.append(f"  {s['name']:<8} {s['done']:>4} {s['new']:>4} {gl_str:>6} {s['commits']:>4} {qa_short:<20} {s['judge']}")

    # --- 2b. 每人详细工作内容 ---
    lines.append(f"\n  📋 详细工作内容：")

    for s in scored:
        name = s['name']
        lines.append(f"\n  {'─'*64}")
        lines.append(f"  👤 {name}  {s['judge']}")

        # 具体完成的内容
        if s['done_issues']:
            lines.append(f"\n     ✅ 完成内容：")
            for i in s['done_issues']:
                summary = i.get('summary', '').strip()
                lines.append(f"       · {summary if summary else i['key']}")

        if s['new_issues']:
            lines.append(f"\n     🆕 新建内容：")
            for i in s['new_issues']:
                summary = i.get('summary', '').strip()
                lines.append(f"       · {summary if summary else i['key']}")

        # GitLab 代码变更（描述性）
        pd = person_data(name)  # 重新查询，避免d引用问题
        if s['gl_by_key']:
            work = work_description(s['gl_by_key'], pd['gl_commits'])
            lines.append(f"\n     🔧 代码变更（+{s['gl']}行，{s['commits']}次提交）：")
            for w in work:
                lines.append(f"       · [{w['issue']}] {w['desc']}{w['extra']}  (+{w['lines']}行)")

        # 评论（有意义的人类评论）
        if s['comments']:
            seen = set()
            for key, c in s['comments'][:3]:
                if key not in seen:
                    body = c['body'][:80].strip()
                    lines.append(f"       💬 {key}: {body}")
                    seen.add(key)

        # 代码质量问题
        if s['qa']['commits'] == 0:
            lines.append(f"\n     ⚠️  代码质量：今日无 GitLab 提交，无法追踪代码变化")
        elif s['qa']['findings']:
            lines.append(f"\n     ⚠️  代码质量：{' | '.join(s['qa']['findings'])}")

        # 趋势预警（连续问题）
        streak_dup  = trend_streak(name, 'dup')
        streak_nogl = trend_streak(name, 'no_gl')
        if streak_dup >= 2:
            lines.append(f"     ⛔ 趋势预警：连续{streak_dup}天有重复commit，代码习惯需改进")
        elif streak_nogl >= 2:
            lines.append(f"     ⛔ 趋势预警：连续{streak_nogl}天无GitLab提交，需关注工作饱和度")

        # 饱满度结论
        lines.append(f"\n     📌 评价：{s['reason']}（{s['judge']}）")

    # ============================================================
    # 【第三部分】共性问题 + 趋势
    # ============================================================
    lines.append(f"\n{'='*70}")
    lines.append("\n【共性质量问题】")

    devs_dup, devs_nogl, devs_notest, devs_low = [], [], [], []
    for name in DEVS:
        d  = person_data(name)
        qa = quality_check(d['gl_commits'])
        if not d['gl_commits']:
            devs_nogl.append(name)
        else:
            if qa['dup'] > 0:   devs_dup.append(name)
            if qa['test_files'] == 0: devs_notest.append(name)
            if qa['low_output']: devs_low.append(name)

    if devs_dup:     lines.append(f"  ⛔ 重复commit：{', '.join(devs_dup)}")
    if devs_notest:   lines.append(f"  ❌ 无测试文件：{', '.join(devs_notest)}")
    if devs_low:      lines.append(f"  📉 极低产出commit：{', '.join(devs_low)}")
    if devs_nogl:     lines.append(f"  ⚠️  无GitLab提交：{', '.join(devs_nogl)}")
    if not devs_dup and not devs_notest and not devs_low and not devs_nogl:
        lines.append("  ✅ 未发现共性问题")

    # 连续趋势
    lines.append("\n【趋势预警】（连续2天以上）")
    warns = []
    for name in DEVS:
        td = trend_streak(name, 'dup')
        tn = trend_streak(name, 'no_gl')
        if td >= 2: warns.append(f"  ⛔ {name} 连续{td}天重复commit")
        if tn >= 2: warns.append(f"  ⚠️  {name} 连续{tn}天无GitLab提交")
    if warns: lines.extend(warns)
    else:     lines.append("  — 无连续趋势问题")

    # 团队整体饱满度
    full_count   = sum(1 for s in scored if '饱满' in s['judge'])
    normal_count = sum(1 for s in scored if '一般' in s['judge'])
    low_count    = sum(1 for s in scored if '偏低' in s['judge'])
    lines.append(f"\n【团队饱满度】✅饱满 {full_count}人 | 🔄一般 {normal_count}人 | ⚠️偏低 {low_count}人")
    if low_count > 0:
        lines.append(f"  ⚠️  提示：{low_count}人产出偏低，请关注是否工作不饱和或存在阻塞")

    lines.append(f"\n{'='*70}")
    lines.append("审查说明：")
    lines.append("  - 代码质量基于commit文件名推断，无法读取实际diff内容")
    lines.append("  - GitLab数据受限于hypermotion组70个项目，可能有遗漏")
    lines.append("  - 饱满度标准：AI时代，300+行/天或2+issue完成才算饱满")
    lines.append("  - 趋势基于 ~/.hermes/reports/daily/ 历史报告")

    return '\n'.join(lines)

report = render_report()
print('\n' + report)

out = os.path.join(REPORT_DIR, f'{DATE}.txt')
with open(out, 'w') as f:
    f.write(report)
print(f"\n✅ 报告已保存: {out}")
