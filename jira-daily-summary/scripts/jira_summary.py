#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA Daily Team Summary V3
两部分结构：
  Part1 总体概览：新建/完成/领域分布/数量统计
  Part2 个人拆解：每人新建+更新+完成 + 工作饱和度 + 可行动结论
"""
import os, sys, json, re, base64
from datetime import datetime, timedelta
from typing import Optional

JIRA_URL  = os.environ.get('JIRA_URL',      'http://office.oneprocloud.com.cn:9005')
JIRA_USER = os.environ.get('JIRA_USERNAME', 'sunqi')
JIRA_PASS = os.environ.get('JIRA_PASSWORD',  'sunqi1358')

LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://zh.agione.co/hyperone/xapi/api')
LLM_API_KEY  = os.environ.get('LLM_API_KEY',  'ak-29c67e1cf9f3461190ce639ab469a0c1')
MAIN_MODEL   = 'minimax/minimax-m2.7/b1d92'


def make_client(timeout=60):
    try:
        from openai import OpenAI
        return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=timeout)
    except Exception as e:
        print(f"[WARN] LLM client failed: {e}", flush=True)
        return None


def extract_json(raw: str) -> Optional[dict]:
    try:
        matches = list(re.finditer(r'\{\s*"depth"', raw))
        if not matches:
            return None
        last_start = matches[-1].start()
        count = 0
        for i in range(last_start, len(raw)):
            if raw[i] == '{':
                count += 1
            elif raw[i] == '}':
                count -= 1
                if count == 0:
                    return json.loads(raw[last_start:i+1])
        return None
    except Exception:
        return None


def get_jira():
    from atlassian import Jira
    return Jira(url=JIRA_URL, username=JIRA_USER, password=JIRA_PASS, cloud=False, timeout=30)


def prev_workday(d: datetime) -> datetime:
    d = d - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def get_date_range(date_arg: Optional[str]) -> tuple[str, str]:
    today = datetime.now()
    prev = prev_workday(today)
    prev_str = prev.strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    if date_arg in (None, '', 'today', 'yesterday'):
        return prev_str, prev_str
    elif date_arg in ('this-week', '本周'):
        start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        return start, today_str
    else:
        return date_arg, date_arg


def search_issues_by_date(jira, date_str: str, date_field: str = 'created', max_results=200):
    """按创建时间或更新时间搜索"""
    if date_field == 'created':
        jql = f'created >= "{date_str}" AND created <= "{date_str} 23:59" ORDER BY created DESC'
    else:
        jql = f'updated >= "{date_str}" AND updated <= "{date_str} 23:59" ORDER BY updated DESC'
    fields = 'summary,status,assignee,reporter,created,updated,issuetype,priority,resolution'
    result = jira.jql(jql, limit=max_results, fields=fields)
    return result.get('issues', []) if isinstance(result, dict) else (result or [])


def get_issue_comments(jira, issue_key: str) -> list:
    try:
        raw = jira.issue_get_comments(issue_key)
        if isinstance(raw, dict):
            return raw.get('comments', []) or []
        elif isinstance(raw, list):
            return raw
    except Exception:
        pass
    return []


def get_issue_worklogs(jira, issue_key: str) -> list:
    try:
        raw = jira.get_issue_worklog(issue_key)
        if isinstance(raw, dict):
            return raw.get('worklogs', []) or []
        elif isinstance(raw, list):
            return raw
    except Exception:
        pass
    return []


def group_by_assignee(issues: list) -> dict:
    grouped = {}
    for issue in issues:
        fields = issue.get('fields', {})
        assignee = fields.get('assignee')
        if not assignee:
            continue
        name = assignee.get('displayName') or assignee.get('name', 'Unknown')
        grouped.setdefault(name, []).append(issue)
    return grouped


# ── 领域标签识别 ─────────────────────────────────────
AREA_KEYWORDS = {
    '块存储':    ['块存储', 'block', 'storage', '网关', 'volume', 'ceph', 'SAN'],
    '对象存储':  ['对象存储', 'object', 'S3', 'oss', 'minio'],
    'Linux Agent': ['linux-agent', 'Linux Agent', 'linux agent', 'debian', 'ubuntu', 'centos', 'suse'],
    'Windows Agent': ['windows-agent', 'Windows Agent', 'win', 'hyper-v'],
    'VMware':    ['vmware', 'ESXi', 'vcenter', 'VCenter'],
    'AWS':       ['AWS', 'Amazon', 'EC2', 'S3-AWS'],
    '阿里云':    ['阿里云', 'aliyun', 'ACK', 'OSS-阿里'],
    'Xhere':     ['Xhere', 'xhere'],
    '前端':      ['前端', 'frontend', 'Vue', 'React', '前端'],
    '后端/CI-CD': ['ci-cd', 'CI-CD', 'pipeline', 'gitlab', 'jenkins'],
    'AI/规划':   ['AI', '规划', '需求讨论', '设计'],
    '错误优化':  ['错误优化', '报错', '优化', 'Bug修复'],
    '文档/其他': ['文档', 'doc', 'wiki'],
}


def guess_area(summary: str) -> str:
    s = summary.lower()
    for area, keywords in AREA_KEYWORDS.items():
        if any(kw.lower() in s for kw in keywords):
            return area
    return '其他'


def saturation_icon_new(deep: int, mid: int, total: int) -> tuple:
    ratio = (deep * 1.0 + mid * 0.5) / total if total else 0
    if ratio >= 0.6:
        return '🟢', '高'
    elif ratio >= 0.3:
        return '🟡', '中'
    else:
        return '🔴', '低'


# ── 分析单人的工作饱和度 ─────────────────────────────
SATURATION_PROMPT = """你是研发团队管理者。以下是研发人员{name}在{date}的工作记录。

【新建】{new_count}个问题：{new_summary}

【更新/评论】{update_count}个问题有评论活动：{update_summary}

【已完成】{done_count}个问题：{done_summary}

请分析并返回JSON（只返回JSON，不要思考过程）：
{{"saturation": "高|中|低",
  "verdict": "一句话结论（如：任务充足、需增加开发任务、任务过载、产出丰富、产出较少等）",
  "reason": "判断理由，2-3句话",
  "concern": "是否有风险或需要关注的问题，1句话"}}

判断标准：
- 特别注意：JIRA上被标记为Done的问题代表实质性交付，必须重点考量
- 饱和度高：完成3个以上问题，或完成1-2个问题同时有代码贡献/MR/深度评论
- 饱和度中：完成1-2个问题，或有多个问题的新建/评论参与
- 饱和度低：新建、评论、完成均很少或为0
- 结论要具体：如"产出丰富"或"任务不足，建议增加开发任务"等"""



def analyze_saturation(person_name: str, new_count: int, new_summary: str,
                       update_count: int, update_summary: str,
                       done_count: int, done_summary: str,
                       date_str: str, client) -> dict:
    default = {'saturation': '低', 'verdict': f'{person_name} 今日无有效工作记录',
               'reason': '无新建、更新或完成记录', 'concern': ''}
    if not client:
        return default

    prompt = SATURATION_PROMPT.format(
        name=person_name,
        date=date_str,
        new_count=new_count,
        new_summary=new_summary or '无',
        update_count=update_count,
        update_summary=update_summary or '无',
        done_count=done_count,
        done_summary=done_summary or '无',
    )

    try:
        resp = client.chat.completions.create(
            model=MAIN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600, temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = extract_json(raw)
        if parsed and parsed.get('saturation') in ('高', '中', '低'):
            return parsed
    except Exception:
        pass
    return default


# ── 核心报告生成 ─────────────────────────────────────
def generate_summary(date_arg: Optional[str] = None) -> str:
    try:
        jira = get_jira()
    except Exception as e:
        return f"JIRA连接失败: {e}"

    start_date, end_date = get_date_range(date_arg)
    print(f"统计日期: {start_date}", flush=True)

    # 搜索该日期新建的 issue
    try:
        created_issues = search_issues_by_date(jira, start_date, 'created')
    except Exception as e:
        return f"查询新建issue失败: {e}"

    # 搜索该日期更新的 issue（包括完成的）
    try:
        updated_issues = search_issues_by_date(jira, start_date, 'updated')
    except Exception as e:
        return f"查询更新issue失败: {e}"

    # 排除 GBot/Jirabot
    BOT_NAMES = {'girabot', 'girabot ', 'jirabot', 'gbot', 'bot', 'system'}
    created_issues = [
        i for i in created_issues
        if (i.get('fields', {}).get('assignee') or {}).get('displayName', '').lower().strip() not in BOT_NAMES
        and (i.get('fields', {}).get('reporter') or {}).get('displayName', '').lower().strip() not in BOT_NAMES
    ]
    updated_issues = [
        i for i in updated_issues
        if (i.get('fields', {}).get('assignee') or {}).get('displayName', '').lower().strip() not in BOT_NAMES
    ]

    if not created_issues and not updated_issues:
        return f"在 {start_date} 没有找到任何 JIRA 活动记录"

    # 分类：新建 / 更新（含评论）/ 已完成
    new_issues = []
    updated_with_comments = []
    done_issues = []

    for issue in updated_issues:
        fields = issue.get('fields', {})
        status = fields.get('status', {}).get('name', '')
        key = issue.get('key', '')

        # 检查评论
        comments = get_issue_comments(jira, key)
        has_meaningful_comment = False
        commenter = ''
        for c in comments:
            author = c.get('author', {})
            author_name = author.get('displayName', '').lower().strip()
            if author_name and author_name not in BOT_NAMES:
                body = str(c.get('body', '')).strip()
                if body and len(body) > 5:
                    has_meaningful_comment = True
                    commenter = author.get('displayName', '')
                    break

        if status == 'Done':
            done_issues.append(issue)
        elif has_meaningful_comment:
            updated_with_comments.append((issue, comments, commenter))

    # 按人分组（基于 updated_issues，因为 assignee 才是承担责任的人）
    by_person = group_by_assignee(updated_issues)
    client = make_client(timeout=60)

    # ─────────────── PART 1: 总体概览 ───────────────
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  JIRA 每日汇总  {start_date}")
    lines.append(f"{'='*60}")

    # 1.1 新建 issue
    area_count = {}
    for i in created_issues:
        area = guess_area(i.get('fields', {}).get('summary', ''))
        area_count[area] = area_count.get(area, 0) + 1

    lines.append(f"\n📌 新建问题（{len(created_issues)} 个）")
    if area_count:
        area_str = '  '.join([f"{k}({v})" for k, v in sorted(area_count.items(), key=lambda x: -x[1])])
        lines.append(f"   领域分布: {area_str}")
    for issue in created_issues[:10]:
        f = issue.get('fields', {})
        assignee = (f.get('assignee') or {}).get('displayName', '未分配')
        lines.append(f"   + {issue['key']} | {f.get('issuetype',{}).get('name','?')} | "
                     f"{assignee} | {f.get('summary','')[:45]}{'...' if len(f.get('summary',''))>45 else ''}")
    if len(created_issues) > 10:
        lines.append(f"   ... 还有 {len(created_issues)-10} 个")

    # 1.2 已完成 issue
    lines.append(f"\n✅ 已完成问题（{len(done_issues)} 个）")
    for issue in done_issues[:10]:
        f = issue.get('fields', {})
        assignee = (f.get('assignee') or {}).get('displayName', '?')
        lines.append(f"   ✓ {issue['key']} | {assignee} | {f.get('summary','')[:45]}{'...' if len(f.get('summary',''))>45 else ''}")
    if len(done_issues) > 10:
        lines.append(f"   ... 还有 {len(done_issues)-10} 个")

    # 1.3 整体统计
    total_people = len(by_person)
    lines.append(f"\n📊 整体统计")
    lines.append(f"   新建 {len(created_issues)} | 已完成 {len(done_issues)} | "
                 f"有评论更新 {len(updated_with_comments)} | 涉及人员 {total_people}")
    lines.append(f"   活跃领域: {', '.join(sorted(area_count.keys())) if area_count else '无'}")

    # ─────────────── PART 2: 按人拆解 ───────────────
    lines.append(f"\n{'='*60}")
    lines.append(f"  按人拆解")
    lines.append(f"{'='*60}")

    for name, person_issues in sorted(by_person.items(), key=lambda x: -len(x[1])):
        # 分离：新建 / 评论更新 / 已完成
        my_new = [i for i in person_issues
                  if i.get('fields',{}).get('created','')[:10] == start_date]
        my_done = [i for i in person_issues
                   if i.get('fields',{}).get('status',{}).get('name','') == 'Done']
        my_updated_issues = []
        for i in person_issues:
            key = i.get('key', '')
            comments = get_issue_comments(jira, key)
            my_comments = [c for c in comments
                           if (c.get('author', {}).get('displayName', '') == name
                               and len(str(c.get('body', '')).strip()) > 5)]
            if my_comments:
                my_updated_issues.append((i, my_comments))

        new_c = len(my_new)
        upd_c = len(my_updated_issues)
        done_c = len(my_done)

        # 生成 summary 文本
        new_s = ' | '.join([f"{i['key']}" for i in my_new[:3]])
        upd_s = ' | '.join([f"{i['key']}({len(cmts)}条评论)" for i, cmts in my_updated_issues[:3]])
        done_s = ' | '.join([f"{i['key']}" for i in my_done[:3]])

        # LLM 判断饱和度
        sat = analyze_saturation(name, new_c, new_s, upd_c, upd_s, done_c, done_s, start_date, client)
        sat_icon, sat_label = {'高': ('🟢', '高'), '中': ('🟡', '中'), '低': ('🔴', '低')}.get(sat.get('saturation', '低'), ('⚪', '?'))

        verdict = sat.get('verdict', '')
        concern = sat.get('concern', '')

        lines.append(f"\n{'─'*60}")
        lines.append(f"  👤 {name}")
        lines.append(f"  📈 新建 {new_c} | 更新 {upd_c} | 已完成 {done_c}")
        lines.append(f"  工作饱和度 {sat_icon} {sat_label}")

        if verdict:
            # 映射为更直观的 emoji
            if '增加' in verdict or '更多' in verdict:
                lines.append(f"  💡 {verdict}")
            elif '过载' in verdict or '饱和' in verdict:
                lines.append(f"  ⚠️ {verdict}")
            elif '无' in verdict or '无记录' in verdict.lower():
                lines.append(f"  ⚪ {verdict}")
            else:
                lines.append(f"  💬 {verdict}")

        if concern:
            lines.append(f"  🔍 {concern}")

        # 详情
        if my_new:
            lines.append(f"  🆕 新建: {', '.join([i['key'] for i in my_new])}")
            for i in my_new:
                f = i.get('fields', {})
                area = guess_area(f.get('summary', ''))
                lines.append(f"     {i['key']} [{area}] {f.get('summary','')[:40]}{'...' if len(f.get('summary',''))>40 else ''}")

        if my_updated_issues:
            lines.append(f"  💬 更新:")
            for i, cmts in my_updated_issues[:5]:
                f = i.get('fields', {})
                comment_preview = ' | '.join([str(c.get('body',''))[:30] for c in cmts[:2]])
                lines.append(f"     {i['key']} | {comment_preview[:60]}{'...' if len(comment_preview)>60 else ''}")

        if my_done:
            lines.append(f"  ✅ 已完成: {', '.join([i['key'] for i in my_done])}")
            for i in my_done:
                f = i.get('fields', {})
                lines.append(f"     {i['key']} | {f.get('summary','')[:40]}{'...' if len(f.get('summary',''))>40 else ''}")

    lines.append(f"\n{'='*60}")
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"{'='*60}")

    return '\n'.join(lines)


if __name__ == '__main__':
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = generate_summary(date_arg)
    print(result)
