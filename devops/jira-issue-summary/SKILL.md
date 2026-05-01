---
name: jira-issue-summary
description: JIRA Issue 产品维度 LLM 总结 — 图片多模态预识别 + 两阶段总结（summary → detailed）
---

# jira-issue-summary

对单个 JIRA Issue 进行 LLM 总结，从 raw JSON + 本地附件图片生成两个文件。

## 与 jira-fetcher 的关系

```
jira-fetcher（采集）→ raw/{KEY}.json + attachments/{KEY}/{filename}  ← 本 skill 读取这些
jira-issue-summary（LLM分析）→ parsed/{KEY}.summary.md + {KEY}.detailed.md  ← 本 skill 输出这些
```

## 目录结构

```
~/.hermes/dev-insights/
├── raw/{KEY}.json                              # jira-fetcher 采集的原始数据
├── attachments/{KEY}/{filename}                # jira-fetcher 下载的附件图片
└── parsed/
    ├── {KEY}.summary.md                        # 产品维度总结
    ├── {KEY}.detailed.md                       # 进度维度总结
    └── attachments/{KEY}/{img_name}.md          # 每张图片的识别结果
```

## 核心流程

```
1. 收集所有图片路径（描述图片 + 评论图片）→ 按上下文分类
2. 多模态识别全部图片 → 结果存 parsed/attachments/{KEY}/*.md（幂等，已存在则跳过）
3. summary LLM：标题 + 元数据 + 描述文本 + 描述图片识别结果 + 所有评论文本 + 评论图片识别结果
4. detailed LLM：summary 结论 + 所有评论文本 + 评论图片识别结果
```

**图片识别是预处理步骤，先于所有 LLM 总结执行。**

## 使用方式

```bash
# 读取 raw/*.json 和 attachments/
# 输出 parsed/{KEY}.summary.md + {KEY}.detailed.md
python3 ~/.hermes/skills/devops/jira-issue-summary/scripts/jira-summarize.py

# 指定日期（用于视图重建）
python3 ~/.hermes/skills/devops/jira-issue-summary/scripts/jira-summarize.py 2026-04-27
```

**幂等**：parsed/{KEY}.summary.md + {KEY}.detailed.md 都存在才跳过，不重复处理。图片识别结果幂等写入，已存在则跳过。

## 图片识别流程

**预处理阶段**，在所有 LLM 总结之前执行：

1. 从 `raw/{KEY}.json` 收集所有图片：
   - `description` 中的图片（JIRA RTE 格式 `!filename!` 或 `src=` URL）
   - `comments[].images` 中的图片（`local` 路径，指向 `attachments/{KEY}/`）
2. 对每张图片调用多模态模型，提供：
   - 该 issue 的标题
   - 图片所在上下文（描述正文 / 评论正文）
   - 问题：`用户插入这张图片想表达什么？`
3. 识别结果存为 `parsed/attachments/{KEY}/{img_name}.md`
4. **先识别完所有图片，再执行 LLM 总结**

## Summary 逻辑（产品维度）

输入：
- issue 标题
- 元数据（type / status / assignee / labels / components 等）
- 描述文本（description）
- 描述中所有图片的识别结果
- **所有评论文本（含评论中的关键上下文）**
- **所有评论图片的识别结果**

输出：`parsed/{KEY}.summary.md`
内容：`🎯 所属大目标：2-3句话说明这个 issue 属于哪个产品/项目大目标，在做什么功能，结合评论中关键讨论`

**踩坑**：Summary 必须包含评论，否则丢失关键上下文（如 MR 合并状态、关联工单、根因分析等）

## Detailed 逻辑（进度维度）

输入：
- summary 的结论（用于判断 issue 当前处于什么阶段）
- 所有评论文本（`comments[].body`）
- 所有评论图片的识别结果

输出：`parsed/{KEY}.detailed.md`
内容：`📍 当前进展：bullet points，格式「日期 人 做了啥」，评论+图片共同决定进度判断。无进展则说明当前状态`

## LLM 返回格式

Summary 和 Detailed 由两次独立 LLM 调用生成，各自返回纯 JSON 对象：

- **summary**：一段话，格式 `🎯 所属大目标：...`
- **detailed**：bullet points，格式 `📍 当前进展：- 日期 人 做了啥`

## 稳定性保障

- **图片识别重试**：vision_analyze 带 `@retry` 装饰器，3 次重试，指数退避 3s→6s→12s
- **LLM 请求重试**：call_text_llm 带 `@retry`，3 次重试，指数退避 3s→6s→12s
- **单 issue 失败隔离**：主循环 try/except，失败不影响其他 issue
- **单图片失败隔离**：单张图片识别失败不影响其他图片和后续 LLM 总结

## LLM API 配置（agione OpenAI 兼容网关）

通过 litellm 统一调用，**必须满足三个条件才能正确路由到 agione 网关**：

```python
# 1. api_base 必须以 /v1 结尾（litellm 会追加 /chat/completions）
AGIONE_BASE = os.environ.get("LLM_BASE_URL", "https://zh.agione.co/hyperone/xapi/api")
API_URL     = AGIONE_BASE.rstrip("/") + "/v1"   # → .../api/v1

# 2. minimax 模型必须指定 custom_llm_provider="openai"（强制走 OpenAI 兼容 handler）
TEXT_MODEL   = os.environ.get("LLM_MODEL",          "minimax/minimax-m2.7/b1d92")
VISION_MODEL = os.environ.get("LLM_VISION_MODEL",   "minimax/minimax-m2.7/b1d92")

# 3. 优先读 MINIMAX_API_KEY（有效 key），回退到 LLM_API_KEY
LLM_KEY     = os.environ.get("MINIMAX_API_KEY",        "") or os.environ.get("LLM_API_KEY", "")
```

**踩坑记录**：
- `custom_llm_provider` 不加 → litellm 用自己的 minimax handler，model 名路由错误
- api_base 不加 `/v1` 后缀 → 拼出 `.../api/chat/completions`（404）
- **litellm `custom_llm_provider="openai"` 时只认 `OPENAI_API_KEY`** → 读 `MINIMAX_API_KEY` 后必须 `os.environ["OPENAI_API_KEY"] = LLM_KEY`，否则 litellm 报 "Request token has expired"（key 实际存在但变量名不对被忽略）
- 读 `LLM_API_KEY` 而非 `MINIMAX_API_KEY` → token 过期（`.env` 中 `LLM_API_KEY=***` 是占位符，`MINIMAX_API_KEY` 才是有效 key）
- **已修复**：Summary prompt 未传入评论 → LLM 丢失 MR 合并状态、关联工单等关键上下文 → **现 Summary 和 Detailed 均传入完整评论内容**
- **已修复**：LLM 自行扩写未知缩写（如看到"MTM迁移项目"就编出"Machine Transfer Migration"）→ **Summary prompt 输出要求里加了约束：只用 issue 原始数据中出现的词汇，禁止发明或扩写任何未给出的名称**

```bash
# 验证 key（Hermes agent 已加载 .env，直接读 os.environ）
python3 -c "
import os
print('MINIMAX_API_KEY:', os.environ.get('MINIMAX_API_KEY', '')[:20])
print('LLM_API_KEY:',     os.environ.get('LLM_API_KEY',     '')[:20])
"
```

## 依赖

- Python `litellm`（统一 LLM 调用，含自动重试+多 provider fallback）
- Python `Pillow`（图片预处理）
- 图片路径：直接读 `attachments/{KEY}/{filename}` 本地文件（jira-fetcher 已下载）
- 环境变量：`MINIMAX_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_VISION_MODEL`（`MINIMAX_API_KEY` 优先，`LLM_API_KEY` 为回退），由 Hermes agent 运行时自动注入，脚本直接 `os.environ.get()` 读取
- ⚠️ **关键**：litellm `custom_llm_provider="openai"` 时只认 `OPENAI_API_KEY` 环境变量名，必须在读取 key 后主动 `os.environ["OPENAI_API_KEY"] = LLM_KEY`，否则 litellm 报 "Request token has expired"（实际是 key 找不到）
