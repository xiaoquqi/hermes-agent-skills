#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dev Insights Fetcher - JIRA issue 采集与时间视图管理

目录结构：
  ~/.hermes/dev-insights/
  ├── raw/{KEY}.json                    # JIRA issue 数据
  ├── attachments/{KEY}/{filename}      # 附件和评论图片（本地文件）
  ├── daily/{date}/
  │   ├── new/{key}.json                # 当日新建 → raw/
  │   ├── updated/{key}.json            # 当日更新 → raw/
  │   └── parsed/                       # jira-summarize.py 建立
  ├── weekly/week={YYYY-Www}/
  │   ├── new/{key}.json
  │   └── updated/{key}.json
  └── monthly/{YYYY-MM}/
      ├── new/{key}.json
      └── updated/{key}.json

用法：
  python3 jira-fetch.py [date]       # 采集并刷新视图
  python3 jira-fetch.py --rebuild    # 仅重建视图
"""
import urllib.request
import json
import re
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# ── 重试装饰器 ────────────────────────────────────────────────────────────────
def retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0):
    """指数退避重试装饰器，适用于网络调用"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt < max_attempts:
                        delay = base_delay * (backoff_factor ** (attempt - 1))
                        print(f"  ⚠️  {func.__name__} 第 {attempt} 次失败: {e}，{delay:.1f}s 后重试...", flush=True)
                        time.sleep(delay)
                    else:
                        print(f"  ❌ {func.__name__} 最终失败: {e}", flush=True)
            raise last_exc
        return wrapper
    return decorator

# ── 配置 ────────────────────────────────────────────────────────────────────
HERMES_HOME = Path.home() / ".hermes"
INSIGHTS_DIR = HERMES_HOME / "dev-insights"
ATTACHMENTS_DIR = INSIGHTS_DIR / "attachments"
RAW_DIR = INSIGHTS_DIR / "raw"

JIRA_URL  = os.environ.get('JIRA_URL',      'http://office.oneprocloud.com.cn:9005')
JIRA_USER = os.environ.get('JIRA_USERNAME', 'sunqi')
JIRA_PASS = os.environ.get('JIRA_PASSWORD', 'sunqi1358')

# ── 节假日（复用 holiday-checker）───────────────────────────────────────────
_HC_PATH = HERMES_HOME / "skills" / "holiday-checker" / "scripts" / "holiday_check.py"
if _HC_PATH.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("holiday_checker", _HC_PATH)
    _hc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_hc)
    _prev_workday = _hc.prev_workday_fast
else:
    def _prev_workday(dt):
        d = dt - timedelta(days=1)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        return d


def parse_date(date_arg):
    today = datetime.now()
    if date_arg in (None, '', 'today'):
        return _prev_workday(today).strftime('%Y-%m-%d')
    elif date_arg == 'yesterday':
        return _prev_workday(today).strftime('%Y-%m-%d')
    return date_arg


def iso_week_of(date_str):
    """返回 'YYYY-Www' 格式的 ISO 周号"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return dt.strftime('%Y-W%V')


# ── JIRA API ────────────────────────────────────────────────────────────────
def get_jira():
    from atlassian import Jira
    return Jira(url=JIRA_URL, username=JIRA_USER, password=JIRA_PASS, cloud=False, timeout=30)


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def jira_search(date_str, update_or_create='updated'):
    jql = f'({update_or_create} >= "{date_str}" AND {update_or_create} <= "{date_str} 23:59") ORDER BY {update_or_create} DESC'
    jira = get_jira()
    data = jira.jql(jql, fields='summary,status,assignee,reporter,created,updated,issuetype,priority,description,labels,parent', limit=200)
    return data.get('issues', [])


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def jira_get_comments(issue_key):
    try:
        jira = get_jira()
        raw = jira.issue_get_comments(issue_key)
        if isinstance(raw, dict):
            return raw.get('comments', []) or []
        elif isinstance(raw, list):
            return raw
    except Exception:
        pass
    return []


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def jira_get_attachments(issue_key):
    try:
        jira = get_jira()
        raw = jira.get_attachments_ids_from_issue(issue_key)
        if not isinstance(raw, list):
            return []
        attachments = []
        for att in raw:
            att_name = att.get('filename', '')
            if att_name and att_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                attachments.append({
                    'filename': att_name,
                    'id': att.get('attachment_id', ''),
                    'url': f"{JIRA_URL}/secure/attachment/{att.get('attachment_id', '')}/{att_name}",
                    'created': (att.get('created', '') or '')[:10],
                })
        return attachments
    except Exception:
        pass
    return []


# ── 附件下载 ────────────────────────────────────────────────────────────────
def _get_auth_opener():
    """返回带 JIRA 认证的 urllib opener"""
    import base64
    credentials = base64.b64encode(f"{JIRA_USER}:{JIRA_PASS}".encode()).decode()
    handler = urllib.request.HTTPHandler()
    opener = urllib.request.build_opener(handler)
    opener.addheaders = [
        ('Authorization', f'Basic {credentials}'),
        ('User-Agent', 'jira-fetcher/1.0'),
    ]
    return opener


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def download_file(url, local_path):
    """下载文件到本地路径，带重试"""
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    opener = _get_auth_opener()
    with opener.open(url, timeout=30) as resp:
        with open(local_path, 'wb') as f:
            f.write(resp.read())
    return local_path


# ── 单 issue 解析 ───────────────────────────────────────────────────────────
def parse_issue(issue):
    fields = issue.get('fields', {})
    key = issue['key']

    # 创建该 issue 的附件目录
    issue_att_dir = ATTACHMENTS_DIR / key
    issue_att_dir.mkdir(parents=True, exist_ok=True)

    # 评论图片：只保留 URL
    raw_comments = jira_get_comments(key)
    comments = []
    all_body_images = []   # 收集所有评论图片 URL
    for c in raw_comments:
        body = c.get('body', '') or ''
        author = c.get('author', {}) or {}
        created = (c.get('created', '') or '')[:10]
        body_images = re.findall(r'!([^!]+)!', body)
        body_images = [img.strip() for img in body_images if img and not img.startswith('global-rte')]
        body_images += re.findall(r'src="([^"]+)"', body)
        if body.startswith('{quote}'):
            body = re.sub(r'\{quote\}', '', body).strip()
        all_body_images.extend(body_images)
        comments.append({
            'author': author.get('displayName', author.get('name', 'Unknown')),
            'body': body[:500],
            'images': body_images,
            'created': created,
        })

    parent = fields.get('parent')
    parent_key = parent.get('key', '') if parent else ''

    # 附件：只取图片元数据
    raw_atts = jira_get_attachments(key)
    attachments = []
    for att in raw_atts:
        att_name = att.get('filename', '')
        if not att_name or not att_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            continue
        att_url = att.get('url', '')
        local_path = str(issue_att_dir / att_name)
        attachments.append({
            'filename': att_name,
            'url': att_url,
            'local': local_path,
            'created': att.get('created', ''),
        })

    # 评论图片下载：区分 full URL 和 filename
    downloaded_body_images = []   # [{original, local}]
    for img_url in set(all_body_images):
        img_url = img_url.strip()
        if not img_url:
            continue
        # 构造本地路径
        img_name = Path(img_url).name.split('?')[0] or f"img_{hash(img_url) & 0xFFFFFFFF}"
        local_img = str(issue_att_dir / img_name)
        # 判断是 full URL 还是 filename
        if img_url.startswith('http'):
            src_url = img_url
        elif img_url.startswith('/'):
            # 相对路径 -> 拼 JIRA 基础路径
            src_url = f"{JIRA_URL}{img_url}"
        else:
            # 纯文件名 -> 在附件列表中查找对应 URL
            src_url = None
            for att in raw_atts:
                if att.get('filename') == img_url:
                    src_url = att.get('url', '')
                    break
        if src_url:
            try:
                download_file(src_url, local_img)
                downloaded_body_images.append({'original': img_url, 'local': local_img})
            except Exception as e:
                print(f"  ⚠️  评论图片下载失败 {img_url}: {e}", flush=True)
                downloaded_body_images.append({'original': img_url, 'local': ''})
        else:
            downloaded_body_images.append({'original': img_url, 'local': ''})

    # 附件下载（跳过已存在的）
    for att in attachments:
        local = att['local']
        if not Path(local).exists():
            try:
                download_file(att['url'], local)
            except Exception as e:
                print(f"  ⚠️  附件下载失败 {att['filename']}: {e}", flush=True)
                att['local'] = ''

    # 更新评论中的 images 为本地路径列表（保留 original 作为 fallback）
    for comment in comments:
        updated_images = []
        for img_entry in downloaded_body_images:
            if img_entry['original'] in comment['images']:
                updated_images.append(img_entry['local'] or img_entry['original'])
        comment['images'] = updated_images

    return {
        'key': key,
        'type': fields.get('issuetype', {}).get('name', 'Unknown'),
        'status': fields.get('status', {}).get('name', 'Unknown'),
        'priority': fields.get('priority', {}).get('name', 'None'),
        'summary': fields.get('summary', ''),
        'description': (fields.get('description') or '')[:1000],
        'assignee': (fields.get('assignee') or {}).get('displayName', 'Unassigned'),
        'reporter': (fields.get('reporter') or {}).get('displayName', 'Unknown'),
        'created': (fields.get('created', '') or '')[:10],
        'updated': (fields.get('updated', '') or '')[:10],
        'labels': fields.get('labels', []) or [],
        'parent_key': parent_key,
        'components': [c.get('name', '') for c in (fields.get('components') or []) if c.get('name')],
        'fixVersions': [v.get('name', '') for v in (fields.get('fixVersions') or []) if v.get('name')],
        'comments': comments,
        'attachments': attachments,
    }


# ── 视图重建 ────────────────────────────────────────────────────────────────
def _ensure_symlink(src, dst):
    """安全创建 symlink：删除旧文件/链接后创建"""
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    if not src.exists():
        print(f"  ⚠️  源文件不存在: {src}")
        return False
    dst.symlink_to(src)
    return True


def _clear_subdirs(parent_dir, keep_dirs=('new', 'updated', 'parsed')):
    """清空视图目录下的所有子目录和 symlinks"""
    if parent_dir.exists():
        for item in parent_dir.iterdir():
            if item.is_dir():
                import shutil
                shutil.rmtree(item)
            else:
                item.unlink()


def _rebuild_period(period_dir, keys, label):
    """为一个 period（daily/weekly/monthly）重建 new/ 和 updated/ 子目录"""
    for sub in ('new', 'updated'):
        sub_dir = period_dir / sub
        sub_dir.mkdir(parents=True, exist_ok=True)
        _clear_subdirs(sub_dir, keep_dirs=())

    new_keys = keys.get('new', [])
    upd_keys = keys.get('updated', [])

    new_count = upd_count = 0
    for key in new_keys:
        src = RAW_DIR / f"{key}.json"
        dst = period_dir / "new" / f"{key}.json"
        if _ensure_symlink(src, dst):
            new_count += 1

    for key in upd_keys:
        src = RAW_DIR / f"{key}.json"
        dst = period_dir / "updated" / f"{key}.json"
        if _ensure_symlink(src, dst):
            upd_count += 1

    print(f"  {label}: new={new_count}, updated={upd_count}", flush=True)
    return new_count, upd_count


def rebuild_daily(date_str, keys):
    """重建 daily/{date}/ 视图"""
    daily_dir = INSIGHTS_DIR / "daily" / date_str
    daily_dir.mkdir(parents=True, exist_ok=True)
    _clear_subdirs(daily_dir)
    _rebuild_period(daily_dir, keys, "daily")
    return keys


def rebuild_weekly(date_str, keys):
    """重建 weekly/week={iso_week}/ 视图（聚合当周所有日的新+更）"""
    week = iso_week_of(date_str)
    weekly_dir = INSIGHTS_DIR / "weekly" / f"week={week}"
    weekly_dir.mkdir(parents=True, exist_ok=True)

    # 合并该周每日已存在的新建/更新 keys
    existing_new = set()
    existing_upd = set()
    if weekly_dir.exists():
        new_dir = weekly_dir / "new"
        upd_dir = weekly_dir / "updated"
        if new_dir.exists():
            existing_new = {f.stem for f in new_dir.iterdir() if f.suffix == '.json'}
        if upd_dir.exists():
            existing_upd = {f.stem for f in upd_dir.iterdir() if f.suffix == '.json'}

    merged = {
        'new': list(existing_new | set(keys.get('new', []))),
        'updated': list(existing_upd | set(keys.get('updated', []))),
    }
    _clear_subdirs(weekly_dir)
    _rebuild_period(weekly_dir, merged, "weekly")
    return merged


def rebuild_monthly(date_str, keys):
    """重建 monthly/{YYYY-MM}/ 视图"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    month_str = dt.strftime('%Y-%m')
    monthly_dir = INSIGHTS_DIR / "monthly" / month_str
    monthly_dir.mkdir(parents=True, exist_ok=True)

    existing_new = set()
    existing_upd = set()
    if monthly_dir.exists():
        new_dir = monthly_dir / "new"
        upd_dir = monthly_dir / "updated"
        if new_dir.exists():
            existing_new = {f.stem for f in new_dir.iterdir() if f.suffix == '.json'}
        if upd_dir.exists():
            existing_upd = {f.stem for f in upd_dir.iterdir() if f.suffix == '.json'}

    merged = {
        'new': list(existing_new | set(keys.get('new', []))),
        'updated': list(existing_upd | set(keys.get('updated', []))),
    }
    _clear_subdirs(monthly_dir)
    _rebuild_period(monthly_dir, merged, "monthly")
    return merged


def rebuild_all(date_str, keys):
    """重建该日相关的所有视图"""
    rebuild_daily(date_str, keys)
    rebuild_weekly(date_str, keys)
    rebuild_monthly(date_str, keys)


# ── 主采集 ──────────────────────────────────────────────────────────────────
def fetch_and_index(date_str):
    """
    采集指定日期新建 + 更新的 issue：
    1. 写入 raw/（每个 issue 一个 JSON）
    2. 重建 daily / weekly / monthly 视图（new/ + updated/ 子目录）
    返回：{'new': [keys], 'updated': [keys]}
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[dev-insights] 抓取新建 issue ({date_str})...", flush=True)
    new_issues = jira_search(date_str, 'created')
    print(f"[dev-insights] 新建: {len(new_issues)} 个", flush=True)

    print(f"[dev-insights] 抓取更新 issue ({date_str})...", flush=True)
    updated_issues = jira_search(date_str, 'updated')
    print(f"[dev-insights] 更新: {len(updated_issues)} 个", flush=True)

    # 区分 new vs updated（在 raw/ 中已存在的 key 视为 updated）
    existing = {f.stem for f in RAW_DIR.glob("*.json")}
    new_keys, upd_keys = [], []
    seen = {}

    for issue in new_issues:
        key = issue['key']
        if key not in seen:
            seen[key] = issue

    for issue in updated_issues:
        key = issue['key']
        if key not in seen:
            seen[key] = issue

    for key, issue in seen.items():
        data = parse_issue(issue)
        out_path = RAW_DIR / f"{key}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if key in existing:
            upd_keys.append(key)
        else:
            new_keys.append(key)

    keys = {'new': new_keys, 'updated': upd_keys}
    total = len(new_keys) + len(upd_keys)
    print(f"[dev-insights] 新建 {len(new_keys)}，更新 {len(upd_keys)}（共 {total} 个 issue）", flush=True)

    # 重建视图
    print(f"[dev-insights] 重建时间视图...", flush=True)
    rebuild_all(date_str, keys)

    print(f"[dev-insights] ✅ 完成", flush=True)
    return keys


# ── 入口 ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Dev Insights Fetcher')
    parser.add_argument('date', nargs='?', default=None)
    parser.add_argument('--rebuild', action='store_true', help='仅重建视图，不采集')
    args = parser.parse_args()

    date_str = parse_date(args.date)

    if args.rebuild:
        if not RAW_DIR.exists():
            print(f"[dev-insights] raw/ 不存在，先采集数据")
            keys = fetch_and_index(date_str)
        else:
            # rebuild 时无法区分 new/updated，整体重建 new/updated 各一份
            all_keys = [f.stem for f in RAW_DIR.glob("*.json")]
            keys = {'new': all_keys, 'updated': all_keys}
            print(f"[dev-insights] 重建视图（{len(all_keys)} 个 issue）...")
            rebuild_all(date_str, keys)
        print("[dev-insights] ✅ 视图重建完成")
    else:
        keys = fetch_and_index(date_str)