---
name: litellm-agione-minimax
description: litellm 调用 agione 网关 minimax 模型的关键配置（custom_llm_provider + /v1 结尾）
triggers:
  - litellm + agione
  - minimax + litellm
  - custom_llm_provider openai
---

# litellm + agione 网关调用 minimax 模型

## 关键配置

必须同时满足两个条件，否则会报错：

1. **`api_base` 必须以 `/v1` 结尾**
   - litellm 会在后面追加 `/chat/completions`
   - 正确：`https://zh.agione.co/hyperone/xapi/api/v1` → 最终调用 `.../api/v1/chat/completions`
   - 错误：`https://zh.agione.co/hyperone/xapi/api` → litellm 追加 `/v1/chat/completions` → 404

2. **`custom_llm_provider="openai"` 必须显式传入**
   - 不加：litellm 解析 `minimax/minimax-m2.7/b1d92` 中的 `minimax` 作为 provider，走自己的 minimax handler，model name 被错误转换
   - 加了：强制走 OpenAI 兼容 handler，model name 原样透传给网关

## 正确代码

```python
import litellm

response = litellm.completion(
    model="minimax/minimax-m2.7/b1d92",
    messages=[{"role": "user", "content": "hello"}],
    api_base="https://zh.agione.co/hyperone/xapi/api/v1",  # /v1 结尾
    api_key="your-token-here",
    custom_llm_provider="openai",                            # 必须加
)
```

## 常见错误

| 错误信息 | 原因 | 解决 |
|---|---|---|
| `appId or chat_session_id cannot be empty` | `api_base` 末尾少了 `/v1` | 加 `/v1` |
| `Request token has expired` | token 真的过期了 | 刷新 token |
| `Model not found` | model name 在网关不支持 | 检查 model 名是否正确 |

## 环境变量

- `LLM_API_KEY` 或 `MINIMAX_API_KEY` — agione token
- `LLM_BASE_URL` — agione base（需以 `/api` 结尾，代码会自己拼接 `/v1`）
- `LLM_MODEL` — 模型名，默认 `minimax/minimax-m2.7/b1d92`
