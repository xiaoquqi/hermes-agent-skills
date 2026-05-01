#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA Issue 产品维度总结（支持图片识别）
- 读取：dev-insights/raw/*.json（扁平）
- 输出：dev-insights/parsed/{KEY}.md（扁平）
- 视图：daily/{date}/parsed/ + weekly/week={}/parsed/ + monthly/{}/parsed/

依赖：Pillow (pip install pillow)，环境变量由 Hermes agent 运行时注入（MINIMAX_API_KEY, LLM_BASE_URL, LLM_MODEL 等）
"""
import os, sys, json, re, base64, io, time, mimetypes
import requests
import litellm
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
                        print(f"  ⚠️  {func.__name__} 第 {attempt} 次失败: {e}，{delay:.1f}s 后重试...", flush=True, file=sys.stderr)
                        time.sleep(delay)
                    else:
                        print(f"  ❌ {func.__name__} 最终失败: {e}", flush=True, file=sys.stderr)
            raise last_exc
        return wrapper
    return decorator

# ── API ─────────────────────────────────────────────────────────────────────
# agione 是 OpenAI 兼容网关，必须：
#   1. api_base 以 /v1 结尾（litellm 会追加 /chat/completions）
#   2. custom_llm_provider="openai"（强制走 OpenAI 兼容 handler）
AGIONE_BASE = os.environ.get("LLM_BASE_URL", "https://zh.agione.co/hyperone/xapi/api")
API_URL     = AGIONE_BASE.rstrip("/") + "/v1"   # → .../api/v1
TEXT_MODEL  = os.environ.get("LLM_MODEL",          "minimax/minimax-m2.7/b1d92")
VISION_MODEL = os.environ.get("LLM_VISION_MODEL",  "minimax/minimax-m2.7/b1d92")
LLM_KEY     = os.environ.get("MINIMAX_API_KEY",        "") or os.environ.get("LLM_API_KEY", "")
os.environ["OPENAI_API_KEY"] = LLM_KEY   # litellm custom_llm_provider="openai" 只认这个名

# ── 路径 ─────────────────────────────────────────────────────────────────────
INSIGHTS_DIR = Path.home() / ".hermes" / "dev-insights"
RAW_DIR      = INSIGHTS_DIR / "raw"
PARSED_DIR   = INSIGHTS_DIR / "parsed"

# ── 图像预处理 ───────────────────────────────────────────────────────────────
MAX_DIM = 1280        # 长边缩到不超过 1280px
JPEG_QUALITY = 85    # JPEG 压缩质量


def preprocess_image(raw_bytes: bytes) -> bytes:
    """
    下载后的原始字节 → PIL 缩放 → 压缩 JPEG
    返回压缩后的 JPEG 字节
    """
    img = Image.open(io.BytesIO(raw_bytes))
    # 转为 RGB（避免 PNG 透明通道问题）
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 缩放
    w, h = img.size
    if max(w, h) > MAX_DIM:
        ratio = MAX_DIM / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    # 压缩
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


# ── 图像识别 ─────────────────────────────────────────────────────────────────
@retry(max_attempts=3, base_delay=3.0, backoff_factor=2.0)
def vision_analyze(image_bytes: bytes, question: str) -> str:
    """litellm 统一调用 vision 模型"""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    response = litellm.completion(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text",      "text":      question},
            ]
        }],
        temperature=0.1,
        max_tokens=512,
        api_base=API_URL,
        api_key=LLM_KEY,
        custom_llm_provider="openai",
    )
    return response["choices"][0]["message"]["content"]


# ── 视图重建 ────────────────────────────────────────────────────────────────
def iso_week_of(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%Y-W%V")


def ensure_symlink(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    if not src.exists():
        return False
    dst.symlink_to(src)
    return True


def _clear_parsed(period_dir):
    pd = period_dir / "parsed"
    if pd.exists():
        import shutil
        shutil.rmtree(pd)


def rebuild_parsed_views(keys, date_str):
    """
    为每个 key 建立两个 symlink：
      {view}/parsed/{key}.summary.md → ../../../../../parsed/{key}.summary.md
      {view}/parsed/{key}.detailed.md → ../../../../../parsed/{key}.detailed.md
    """
    week  = iso_week_of(date_str)
    month = date_str[:7]
    daily   = INSIGHTS_DIR / "daily"   / date_str
    weekly  = INSIGHTS_DIR / "weekly"  / f"week={week}"
    monthly = INSIGHTS_DIR / "monthly" / month

    _clear_parsed(daily)
    _clear_parsed(weekly)
    _clear_parsed(monthly)

    dc = wc = mc = 0
    for key in keys:
        for suffix in ("summary.md", "detailed.md"):
            src = PARSED_DIR / f"{key}.{suffix}"
            if not src.exists():
                continue
            for view_dir in (daily, weekly, monthly):
                dst = view_dir / "parsed" / f"{key}.{suffix}"
                if ensure_symlink(src, dst):
                    if view_dir == daily:
                        dc += 1
                    elif view_dir == weekly:
                        wc += 1
                    else:
                        mc += 1

    return {"daily": dc, "weekly": wc, "monthly": mc}


# ── LLM 文本总结 ─────────────────────────────────────────────────────────────
@retry(max_attempts=3, base_delay=3.0, backoff_factor=2.0)
def call_text_llm(prompt: str) -> str:
    """litellm 统一调用 text 模型，含自动重试+provider fallback"""
    response = litellm.completion(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1200,
        api_base=API_URL,
        api_key=LLM_KEY,
        custom_llm_provider="openai",
    )
    return response["choices"][0]["message"]["content"]


# ── 图片收集 & 预处理 ─────────────────────────────────────────────────────────
ATTACHMENTS_DIR      = INSIGHTS_DIR / "attachments"
PARSED_ATT_DIR       = PARSED_DIR  / "attachments"   # parsed/attachments/{KEY}/


def _collect_issue_images(issue: dict) -> list:
    """
    收集 issue 所有图片路径 + 所在上下文。
    返回: [{local, context, label}, ...]
      - local:   本地文件路径
      - context:  "description" | "comment: {author}@{date}"
      - label:    用于文件名的简短标签
    """
    key = issue.get("key", "UNK")
    images = []
    seen = set()

    # 1) 描述中的图片
    desc = issue.get("description") or ""
    atts = {Path(a.get("local", "")).name: a.get("local", "")
            for a in issue.get("attachments", []) or []
            if a.get("local")}

    for m in re.finditer(r'!([^!]+)!', desc):
        fname = m.group(1).strip()
        if not fname or fname.startswith("global-rte"):
            continue
        local = atts.get(fname)
        if not local:
            continue
        if local in seen:
            continue
        seen.add(local)
        images.append({"local": local, "context": "description",
                       "label": f"desc_{fname}"})

    # 2) 评论中的图片
    for c in (issue.get("comments") or []):
        author = c.get("author", "unknown")
        date   = c.get("created", "")[:10]
        for idx, img_local in enumerate(c.get("images") or []):
            if not img_local or img_local in seen:
                continue
            seen.add(img_local)
            fname = Path(img_local).name
            images.append({
                "local":   img_local,
                "context": f"comment by {author}@{date}",
                "label":   f"comment_{author}_{idx}_{fname}",
            })

    return images


def preprocess_all_images(key: str, images: list) -> dict:
    """
    对所有图片做视觉识别，结果存 parsed/attachments/{key}/*.md
    返回: {label: "识别文本", ...}
    """
    out_dir = PARSED_ATT_DIR / key
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for img in images:
        local  = img["local"]
        label  = img["label"]
        ctx    = img["context"]
        md_path = out_dir / f"{label}.md"

        # 跳过已识别过的
        if md_path.exists():
            results[label] = md_path.read_text(encoding="utf-8").strip()
            continue

        if not Path(local).exists():
            results[label] = f"[文件不存在: {local}]"
            md_path.write_text(results[label], encoding="utf-8")
            continue

        try:
            raw = Path(local).read_bytes()
            if len(raw) < 500:
                results[label] = "[图片太短，可能下载失败]"
                md_path.write_text(results[label], encoding="utf-8")
                continue

            processed = preprocess_image(raw)
            desc = vision_analyze(
                processed,
                f"这是一张来自 JIRA issue {key} 的{ctx}区域的截图。\n"
                f"请描述图中关键内容，以及用户插入这张图想表达什么（证明、说明问题、还是其他）？"
            )
            results[label] = desc
            md_path.write_text(desc, encoding="utf-8")
        except Exception as e:
            results[label] = f"[识别失败: {e}]"
            md_path.write_text(results[label], encoding="utf-8")

    return results


def _parse_llm_json(raw: str, prompt: str, key: str) -> dict:
    """从 LLM 输出中解析 JSON，失败则用同一 prompt 重试"""
    for attempt in range(1, 4):
        text = re.sub(r'^```json\s*', '', raw.strip(), flags=re.MULTILINE)
        text = re.sub(r'^```\s*$',   '', text, flags=re.MULTILINE).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        m = re.search(r'\{[^{}]*"summary"[^{}]*\}[^{}]*"detailed"[^{}]*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        if attempt < 3:
            delay = 3.0 * (2 ** (attempt - 1))
            print(f"  ⚠️  {key} LLM 返回非 JSON（第 {attempt} 次），{delay:.1f}s 后重试...", flush=True, file=sys.stderr)
            time.sleep(delay)
            raw = call_text_llm(prompt)
    return None


# ── Summary prompt ────────────────────────────────────────────────────────────
SUMMARY_PROMPT_TPL = """你是产品经理，请分析以下 JIRA Issue，生成产品维度的 summary。

## Issue 元数据
- KEY: {key}
- 类型: {type}
- 状态: {status}
- 标题: {summary}
- 描述:
{description}

## 描述中的图片分析结果
{desc_images}

## 所有评论（包含重要上下文）
{comments}

## 评论中的图片分析结果
{comment_images}

## 输出要求
直接输出 JSON，不要任何解释，不要 markdown 代码块：
- 只用 issue 原始数据中出现的词汇，不要自行发明或扩写任何未给出的名称（包括但不限于项目名、产品名、缩写全称）
- 产品/项目名必须严格沿用 issue 中已有的写法

{{"summary": "🎯 所属大目标：2-3句话说明这个 issue 属于哪个产品/项目大目标，在做什么功能，结合评论中关键讨论"}}
"""


# ── Detailed prompt ───────────────────────────────────────────────────────────
DETAILED_PROMPT_TPL = """你是产品进度分析师，请根据以下信息，生成进度维度的 detailed。

## Issue 基本信息
- KEY: {key}
- 类型: {type}
- 状态: {status}
- 标题: {summary}

## Summary 结论（判断当前所处阶段）
{summary_text}

## 所有评论
{comments}

## 评论中的图片分析结果
{comment_images}

## 输出要求
直接输出 JSON，不要任何解释，不要 markdown 代码块：
{{"detailed": "📍 当前进展：bullet points，格式「日期 人 做了啥」，包含功能+完成人+完成时间。无进展则说明当前状态"}}
"""


def summarize_issue(key: str, issue: dict) -> dict:
    """
    新逻辑：
    1. 收集所有图片（描述图片 + 评论图片）
    2. 多模态识别全部图片 → 结果存 parsed/attachments/{key}/*.md
    3. Summary：标题 + 描述 + 描述图片识别结果
    4. Detailed：Summary 结论 + 所有评论 + 评论图片识别结果
    """
    # 1. 收集所有图片
    images = _collect_issue_images(issue)
    total_imgs = len(images)
    desc_labels = {img["label"] for img in images if img["context"] == "description"}
    print(f"  📷 {total_imgs} 张图片（描述:{len(desc_labels)} 评论:{total_imgs - len(desc_labels)}）", flush=True)

    # 2. 预处理：多模态识别全部图片
    img_results = preprocess_all_images(key, images)   # {label: 识别文本}

    # 3. Summary — 先算好所有需要的文本
    desc_img_text = "\n".join(
        f"- {label}: {img_results.get(label, '[无结果]')}"
        for label in desc_labels
    ) or "（无描述图片）"

    comment_img_text = "\n".join(
        f"- {label}: {img_results.get(label, '[无结果]')}"
        for label, img in ((l, i) for l, i in img_results.items() if l not in desc_labels)
    ) or "（无评论图片）"

    comments_block = []
    for c in (issue.get("comments") or []):
        body = (c.get("body") or "").strip()
        if body:
            comments_block.append(f"- [{c.get('created','')[:10]}] {c.get('author','')}: {body[:300]}")
    comments_text = "\n".join(comments_block) or "（无评论）"

    summary_prompt = SUMMARY_PROMPT_TPL.format(
        key       = key,
        type      = issue.get("type", ""),
        status    = issue.get("status", ""),
        summary   = issue.get("summary", ""),
        description = (issue.get("description") or "")[:1000],
        desc_images = desc_img_text,
        comments   = comments_text,
        comment_images = comment_img_text,
    )
    print(f"  🤖 Summary LLM...", flush=True, end=" ", file=sys.stderr)
    summary_raw = call_text_llm(summary_prompt)
    summary_data = _parse_llm_json(summary_raw, summary_prompt, key)
    if summary_data is None:
        return {"summary": f"[Summary 失败] {key}", "detailed": "[Summary 失败，无详情]"}
    summary_text = summary_data.get("summary", "")

    # 4. Detailed — 复用上方已算好的变量
    detailed_prompt = DETAILED_PROMPT_TPL.format(
        key           = key,
        type          = issue.get("type", ""),
        status        = issue.get("status", ""),
        summary       = issue.get("summary", ""),
        summary_text  = summary_text,
        comments      = comments_text,
        comment_images = comment_img_text,
    )
    print(f"🤖 Detailed LLM...", flush=True, end=" ", file=sys.stderr)
    detailed_raw = call_text_llm(detailed_prompt)
    detailed_data = _parse_llm_json(detailed_raw, detailed_prompt, key)
    if detailed_data is None:
        return {"summary": summary_text, "detailed": "[Detailed 失败]"}
    return {
        "summary": summary_text,
        "detailed": detailed_data.get("detailed", ""),
    }


# ── 入口 ──────────────────────────────────────────────────────────────────────
def parse_date(date_arg):
    if date_arg in (None, "", "today"):
        return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return date_arg


def main(date_str):
    files = sorted(RAW_DIR.glob("*.json"))
    total = len(files)
    processed = skipped = errors = 0
    done_keys = []

    for i, fp in enumerate(files, 1):
        key = fp.stem
        if not (key.startswith("REQ-") or key.startswith("BUG-")):
            continue

        out_sum = PARSED_DIR / f"{key}.summary.md"
        out_det = PARSED_DIR / f"{key}.detailed.md"
        if out_sum.exists() and out_det.exists():
            print(f"[{i}/{total}] ⏭️  已存在: {key}", flush=True)
            skipped += 1
            done_keys.append(key)
            continue

        print(f"[{i}/{total}] 🔄 {key} ... ", flush=True, end="", file=sys.stderr)
        try:
            issue = json.loads(fp.read_text())
            result = summarize_issue(key, issue)

            out_sum.write_text(result.get("summary", ""), encoding="utf-8")
            out_det.write_text(result.get("detailed", ""), encoding="utf-8")
            print(f"✅", flush=True, file=sys.stderr)
            processed += 1
            done_keys.append(key)
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}", flush=True, file=sys.stderr)
            errors += 1
        except Exception as e:
            print(f"❌ {e}", flush=True, file=sys.stderr)
            errors += 1

    if done_keys:
        print(f"\n[jira-summarize] 重建视图...", flush=True, file=sys.stderr)
        counts = rebuild_parsed_views(done_keys, date_str)
        for k, v in counts.items():
            print(f"   {k}/parsed/ → {v} symlinks", flush=True, file=sys.stderr)

    print(f"\n[jira-summarize] ✅ 处理 {processed}，跳过 {skipped}，出错 {errors}", flush=True, file=sys.stderr)
    print(json.dumps({"processed": processed, "skipped": skipped, "errors": errors}))


if __name__ == "__main__":
    main(parse_date(sys.argv[1] if len(sys.argv) > 1 else None))
