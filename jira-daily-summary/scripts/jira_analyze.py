#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA 分析模块
职责：接收干净的 JSON 数据，进行规则分析 + 可选 LLM 增强
对外暴露：CLI + Python function
"""
import os, sys, json, argparse, re
from datetime import datetime
from typing import Optional, Dict, Any, List

LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://zh.agione.co/hyperone/xapi/api')
LLM_API_KEY  = os.environ.get('LLM_API_KEY',  'ak-29c67e1cf9f3461190ce639ab469a0c1')
MAIN_MODEL   = 'minimax/minimax-m2.7/b1d92'

AREA_KEYWORDS = {
    '块存储':     ['块存储', 'block', 'storage', '网关', 'volume', 'ceph', 'SAN'],
    '对象存储':   ['对象存储', 'object', 'S3', 'oss', 'minio'],
    'Linux Agent': ['linux-agent', 'linux agent', 'debian', 'ubuntu', 'centos', 'suse', 'Linux Agent'],
    'Windows Agent': ['windows-agent', 'Windows Agent', 'win', 'hyper-v'],
    'VMware':     ['vmware', 'ESXi', 'vcenter', 'VCenter'],
    'AWS':        ['AWS', 'Amazon', 'EC2'],
    '阿里云':     ['阿里云', 'aliyun', 'ACK'],
    'Xhere':      ['Xhere', 'xhere'],
    '前端':       ['前端', 'frontend', 'Vue', 'React'],
    '后端/CI-CD': ['ci-cd', 'CI-CD', 'pipeline', 'gitlab', 'jenkins'],
    'AI/规划':    ['AI', '规划', '需求讨论'],
    '错误优化':   ['错误优化', '报错', 'Bug修复'],
    '文档/其他':  ['文档', 'doc'],
}


def guess_area(summary: str) -> str:
    s = summary.lower()
    for area, keywords in AREA_KEYWORDS.items():
        if any(kw.lower() in s for kw in keywords):
            return area
    return '其他'


def make_client(timeout=60):
    try:
        from openai import OpenAI
        return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=timeout)
    except Exception:
        return None


def extract_json(raw: str) -> Optional[dict]:
    try:
        matches = list(re.finditer(r'\{\s*"saturation"', raw))
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


# ──────────────────────────────────────────────────────────
# 规则引擎
# ──────────────────────────────────────────────────────────

def score_person(person_issues: List[Dict], person_name: str) -> Dict:
    """
    对一个人的所有 issue 打分，返回基础分析结果
    分数 = 完成数*3 + 新建数*2 + (本人评论数)*1
    注意：只统计该人自己写的评论，其他人写在同一 issue 上的不算
    """
    # 统计该人自己写的评论
    my_comment_count = 0
    my_worklog_count = 0
    for issue in person_issues:
        my_comment_count += sum(
            1 for c in issue.get('comments', [])
            if c.get('author', '') == person_name
        )
        my_worklog_count += sum(
            1 for w in issue.get('worklogs', [])
            if w.get('author', '') == person_name
        )

    new_count = sum(1 for i in person_issues if i.get('_is_new_today'))
    done_count = sum(1 for i in person_issues if i.get('status') == 'Done')

    raw_score = done_count * 3 + new_count * 2 + my_comment_count * 1

    # 工作量等级
    if raw_score >= 6:
        level = '高'
        verdict = '产出丰富'
    elif raw_score >= 2:
        level = '中'
        verdict = '工作量正常'
    else:
        level = '低'
        verdict = '任务不足，建议增加开发任务'

    # 风险点
    concern = ''
    if done_count > 5:
        concern = '完成数量偏多，需确认是否都真实完成'
    elif new_count == 0 and done_count == 0 and my_comment_count == 0:
        concern = '今日无有效产出，需关注'

    return {
        'raw_score': raw_score,
        'new_count': new_count,
        'done_count': done_count,
        'my_comment_count': my_comment_count,
        'my_worklog_count': my_worklog_count,
        'issue_count': len(person_issues),
        'saturation': level,
        'verdict': verdict,
        'reason': (
            f'完成{done_count}个，'
            f'新建{new_count}个，'
            f'本人评论{my_comment_count}条，'
            f'综合评分{raw_score}'
        ),
        'concern': concern,
    }


def analyze_person(person_name: str, person_issues: List[Dict],
                   date_str: str, use_llm: bool = False) -> Dict:
    """
    分析单人的工作表现
    1. 先用规则引擎打分（只统计该人自己的评论）
    2. （可选）LLM 增强，输出更智能的 verdict 和 concern
    """
    rule_result = score_person(person_issues, person_name)

    if not use_llm:
        return {
            'name': person_name,
            'date': date_str,
            **rule_result,
            'issues': person_issues,
            'llm_used': False,
        }

    # LLM 增强：过滤出该人自己参与的评论
    client = make_client()
    if not client:
        return {'name': person_name, 'date': date_str, **rule_result,
                'issues': person_issues, 'llm_used': False}

    # 该人自己写的评论
    my_comments_by_issue = []
    for issue in person_issues:
        my_cmts = [c for c in issue.get('comments', []) if c.get('author', '') == person_name]
        if my_cmts:
            my_comments_by_issue.append((issue, my_cmts))

    new_issues = [i for i in person_issues if i.get('_is_new_today')]
    done_issues = [i for i in person_issues if i.get('status') == 'Done']

    new_s = ' | '.join([f"{i['key']}:{i['summary'][:30]}" for i in new_issues[:3]])
    done_s = ' | '.join([f"{i['key']}:{i['summary'][:30]}" for i in done_issues[:3]])
    act_s = ' | '.join([
        f"{i['key']}(自撰{len(cmts)}条):{str(cmts[0]['body'])[:30]}"
        for i, cmts in my_comments_by_issue[:3]
    ])

    prompt = f"""你是研发团队管理者。分析研发人员{person_name}在{date_str}的工作表现。

【新建 {len(new_issues)} 个】：{new_s or '无'}
【完成 {len(done_issues)} 个】：{done_s or '无'}
【本人有评论更新 {len(my_comments_by_issue)} 个问题】：{act_s or '无'}

规则引擎初判：饱和度={rule_result['saturation']}，评分={rule_result['raw_score']}，
其中完成{rule_result['done_count']}个、新建{rule_result['new_count']}个、本人评论{rule_result['my_comment_count']}条。

请结合以上信息，返回更精准的分析JSON：
{{"saturation": "高|中|低",
  "verdict": "一句话结论",
  "reason": "判断理由，2句",
  "concern": "风险提示，1句，无风险则返回空字符串"}}

要求：
- verdict 要有具体建议（如：任务充足、建议增加任务、产出过载需关注）
- reason 要结合规则引擎的评分和实际数据
- concern 如果没有风险则为空字符串"""

    try:
        resp = client.chat.completions.create(
            model=MAIN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600, temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = extract_json(raw)
        if parsed and parsed.get('saturation') in ('高', '中', '低'):
            return {
                'name': person_name,
                'date': date_str,
                'raw_score': rule_result['raw_score'],
                'new_count': rule_result['new_count'],
                'done_count': rule_result['done_count'],
                'my_comment_count': rule_result['my_comment_count'],
                'my_worklog_count': rule_result['my_worklog_count'],
                'issue_count': rule_result['issue_count'],
                'saturation': parsed.get('saturation', rule_result['saturation']),
                'verdict': parsed.get('verdict', rule_result['verdict']),
                'reason': parsed.get('reason', rule_result['reason']),
                'concern': parsed.get('concern', rule_result['concern']),
                'issues': person_issues,
                'llm_used': True,
            }
    except Exception:
        pass

    return {'name': person_name, 'date': date_str, **rule_result,
            'issues': person_issues, 'llm_used': False}


def run_analysis(data: Dict, date_str: str, use_llm: bool = False) -> Dict:
    """
    对完整的 enriched data 运行分析
    返回总体分析 + 每人分析
    """
    created = data.get('created', [])
    updated = data.get('updated', [])

    # 标记新建（created 在目标日期）
    for i in created:
        i['_is_new_today'] = (i.get('created', '') == date_str)

    # 找出更新的（updated 在目标日期，但 created 不一定是今天）
    updated_today = [i for i in updated if i.get('updated', '') == date_str]
    for i in updated_today:
        i['_is_new_today'] = (i.get('created', '') == date_str)

    # 按人分组（基于 updated 的 assignee）
    by_person: Dict[str, List[Dict]] = {}
    for issue in updated_today:
        assignee = issue.get('assignee', '')
        if assignee:
            by_person.setdefault(assignee, []).append(issue)

    # 总体统计
    area_count = {}
    for i in created:
        area = guess_area(i.get('summary', ''))
        area_count[area] = area_count.get(area, 0) + 1

    done_total = sum(1 for i in updated_today if i.get('status') == 'Done')

    # 每人分析
    person_results = []
    for name, issues in sorted(by_person.items(), key=lambda x: -len(x[1])):
        result = analyze_person(name, issues, date_str, use_llm=use_llm)
        person_results.append(result)

    # 新建 issue 列表（按人）
    new_by_person: Dict[str, List[Dict]] = {}
    for i in created:
        if i.get('_is_new_today'):
            assignee = i.get('assignee', '未分配')
            new_by_person.setdefault(assignee, []).append(i)

    return {
        'date': date_str,
        'summary': {
            'created_count': len(created),
            'done_count': done_total,
            'updated_count': len(updated_today),
            'person_count': len(by_person),
            'area_distribution': area_count,
        },
        'person_results': person_results,
        'new_issues_by_person': new_by_person,
    }


def main():
    parser = argparse.ArgumentParser(description='JIRA Analyzer')
    parser.add_argument('--json', help='输入 JSON 文件路径（不提供则从 stdin 读取）')
    parser.add_argument('--date', help='日期 YYYY-MM-DD')
    parser.add_argument('--llm', action='store_true', help='启用 LLM 增强分析')
    parser.add_argument('--rule-only', action='store_true', help='仅使用规则引擎（默认）')
    args = parser.parse_args()

    use_llm = args.llm and not args.rule_only

    # 从 stdin 或文件读取数据
    if args.json:
        with open(args.json) as f:
            payload = json.load(f)
    else:
        payload = json.load(sys.stdin)

    date_str = args.date or payload.get('query_date') or payload.get('date', '')

    enriched = payload.get('data', {})

    result = run_analysis(enriched, date_str, use_llm=use_llm)

    output = {
        'date': date_str,
        'analysis': result,
        'llm_used': use_llm,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
