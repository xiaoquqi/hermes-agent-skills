---
name: ai-coding-bootcamp
description: AI代码编程入门课程，包含Cursor、Claude Code、Codex的全面学习路径和实战项目规划。
author: Hermes
version: 2.0.0
triggers:
  - "AI编程课程"
  - "Cursor教程"
  - "Claude Code教程"
  - "Codex教程"
  - "AI代码编辑器学习"
  - "AI coding bootcamp"
---

# AI 开发工具培训课程
> 基于 Claude Code / Cursor / OpenAI Codex 官方文档与优质视频综合构建  
> 更新时间：2026-04-12

---

## 课程概述

本课程分 **初级** 和 **中级** 两个阶段，系统讲解三大 AI 编程工具：

| 工具 | 厂商 | 形态 | 特点 |
|------|------|------|------|
| **Claude Code** | Anthropic | CLI / IDE插件 / 桌面应用 | 深度代码理解、MCP工具扩展、多Agent协作 |
| **Cursor** | Cursor AI | AI优先 IDE（VS Code fork）| 实时协作、Plan模式、内置Agent |
| **OpenAI Codex CLI** | OpenAI | 终端CLI工具 | 轻量快速、Sandbox安全、Git worktree并行 |

### 优质参考资源

**视频教程（YouTube）：**
- [Claude Code Full Tutorial - Tech With Tim](https://www.youtube.com/watch?v=ntDIxaeo3Wg)（35分钟，633k播放，15章节）
- [Mastering Claude Code 30min - Anthropic官方](https://www.youtube.com/watch?v=6eBSHbLKuN0)（28分钟，1M播放）
- [Kevin Stratvert Claude Code Beginner](https://www.youtube.com/watch?v=eMZmDH3T2bY)（14分钟，696k播放）
- [Cursor Tutorial Tech With Tim](https://www.youtube.com/watch?v=ocMOZpuAMw4)（15分钟，937k播放）
- [Cursor 2.0 Full Tutorial - Tech With Tim](https://www.youtube.com/watch?v=l30Eb76Tk5s)（27分钟）
- [Master Cursor AI 13min](https://www.youtube.com/watch?v=-SkWL0MK9Ec)（13分钟）
- [Codex CLI Complete Beginner Guide - pookie](https://www.youtube.com/watch?v=sTE0G95uEIw)（20分钟，14章节）
- [Master OpenAI Codex 26min - Keith AI](https://www.youtube.com/watch?v=EwVs3O2Zm6I)（26分钟）

**官方文档：**
- Claude Code: https://code.claude.com/docs
- Cursor: https://www.cursor.com/docs
- Codex CLI: https://github.com/openai/codex

---

# 初级课程：AI Coding 入门

## 模块 1：Claude Code 基础（4课时）

### 第1课：Claude Code 安装与首次使用
**学习目标：** 了解 Claude Code 是什么，安装并运行第一个会话

**1.1 Claude Code 是什么**
Claude Code 是一个 AI 代理编码工具，可以：
- 读取代码库、编辑文件、运行命令
- 与开发工具深度集成
- 跨终端、IDE、桌面应用和浏览器使用

**1.2 安装 Claude Code**
```bash
# macOS / Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash

# Windows PowerShell
irm https://claude.ai/install.ps1 | iex

# 或使用 Homebrew
brew install anthropic/claude-code/claude-code
```

**1.3 启动你的第一个会话**
```bash
cd your-project
claude
```

**1.4 基本命令一览**
| 命令 | 功能 |
|------|------|
| `/quit` 或 `/exit` | 退出 Claude Code |
| `/clear` | 清屏 |
| `/model` | 切换模型 |
| `/help` | 显示帮助 |

**实操任务：**
- [ ] 安装 Claude Code
- [ ] 在任意项目中启动 `claude`
- [ ] 输入第一个问题："这个项目是做什么的？"

---

### 第2课：与 Claude Code 对话（Ask & Act）
**学习目标：** 学会提问、让 Claude 读写文件、执行命令

**2.1 Claude Code 的两种模式**
- **Ask 模式**：提问、讨论代码（默认）
- **Act 模式**：让 Claude 执行操作（写入文件、运行命令）

**2.2 提问技巧**
```bash
# ❌ 模糊提问
"帮我修bug"

# ✅ 具体提问
"帮我修复 src/auth.py 第34行的 TokenExpiredError，错误信息是..."

# ✅ 带上下文的提问
"在 src/目录下添加一个新的API路由，处理 POST /api/users 请求"
```

**2.3 让 Claude 执行终端命令**
```bash
"请运行 npm install 安装依赖，然后运行 npm test 看测试是否通过"
```

**实操任务：**
- [ ] 让 Claude 读取项目中的任意文件
- [ ] 让 Claude 解释一段代码的功能
- [ ] 让 Claude 执行一个终端命令（如 `ls -la`）

---

### 第3课：Cursor 基础 — 安装与核心界面
**学习目标：** 熟悉 Cursor 编辑器，了解与传统 VS Code 的区别

**3.1 Cursor 是什么**
Cursor 是一个 AI 优先的代码编辑器，基于 VS Code fork，内置：
- **Composer**：多文件生成器
- **Chat**：全代码库问答
- **Agent**：自主完成任务
- **Plan Mode**：规划复杂功能

**3.2 安装 Cursor**
1. 访问 https://cursor.com/download
2. 下载对应系统的安装包
3. 安装后打开，可用 VS Code 主题和快捷键

**3.3 核心快捷键**
| 快捷键 | 功能 |
|--------|------|
| `Cmd+K` | 打开 Composer（代码生成）|
| `Cmd+L` | 打开 Chat（问答）|
| `Cmd+I` | 打开 Inline Chat（行内编辑）|
| `Cmd+Enter` | 提交 Agent 任务 |

**实操任务：**
- [ ] 下载安装 Cursor
- [ ] 打开/导入一个已有项目
- [ ] 使用 `Cmd+K` 生成一个 "Hello World" 函数

---

### 第4课：Cursor 核心功能 — Cmd K / Composer / Chat
**学习目标：** 掌握 Cursor 的三大核心操作方式

**4.1 Cmd K — 即时代码生成与编辑**
选中代码 → Cmd+K → 描述想要的变化

**4.2 Composer — 多文件生成器**
一次生成多个相关文件，理解项目整体结构，保持代码风格一致

**4.3 Chat — 全代码库问答**
`Cmd+L` 打开 Chat 面板，可以 @ 特定文件、文件夹、或 Git commit

**实操任务：**
- [ ] 用 Cmd+K 修改一个现有函数
- [ ] 用 Composer 生成一个完整的 React 组件（包含样式）
- [ ] 用 Chat 询问项目的入口文件和架构

---

### 第5课：OpenAI Codex CLI 入门
**学习目标：** 安装 Codex CLI，在终端中使用 AI 辅助编程

**5.1 Codex CLI 是什么**
OpenAI 开发的终端编程代理，轻量、快速、安全（Sandbox 隔离）。

```bash
# 安装
npm i -g @openai/codex
# 或
brew install --cask codex

# 启动
codex
```

**5.2 基础使用**
```bash
/code  "帮我创建一个新路由处理 /api/products"
/review  "检查最近3个commit的代码质量"
/fix  "修复 src/auth.py 的登录问题"
```

**5.3 AGENTS.md — 项目级指令**
类似 Claude Code 的 `.claude` 目录，Codex 使用 `AGENTS.md`

**实操任务：**
- [ ] 安装 Codex CLI
- [ ] 在项目中启动 `codex`
- [ ] 创建一个 `AGENTS.md` 文件描述你的项目

---

## 模块 2：三大工具横向对比（2课时）

### 第6课：如何选择 — 场景化对比分析
**学习目标：** 理解每个工具的适用场景，能根据项目需求选择合适的工具

**6.1 功能维度对比**

| 维度 | Claude Code | Cursor | Codex CLI |
|------|------------|--------|-----------|
| 代码理解深度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 实时协作 | ❌ | ⭐⭐⭐⭐⭐ | ❌ |
| 多人代码审查 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| 大型代码库索引 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| MCP 工具扩展 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| 多 Agent 并行 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 启动速度 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**6.2 场景选择指南**

**选 Claude Code 当：**
- 大型代码库（>10万行）
- 需要深度代码理解
- 复杂的 Agent 团队协作
- 需要 MCP 工具扩展

**选 Cursor 当：**
- 团队实时协作编程
- 偏好 GUI 化的 AI 交互
- 已经在用 VS Code
- 需要 Plan Mode 规划复杂功能

**选 Codex CLI 当：**
- 追求极致轻量快速
- 终端重度用户
- 需要 Git worktree 并行开发
- 安全要求高（Sandbox）

**6.3 组合使用策略**
- **Cursor** 做日常开发 + 实时协作
- **Claude Code** 做大型重构 + Agent 任务
- **Codex CLI** 做快速修复 + CI/CD 自动化

---

# 中级课程：AI Coding 进阶

## 模块 3：Claude Code 进阶（4课时）

### 第7课：记忆系统 — Instructions / Memory / Skills
**学习目标：** 让 Claude Code 学习你的项目规范，长期记忆团队约定

**7.1 CLAUDE.md — 项目级指令**
在项目根目录创建 `CLAUDE.md`，Claude Code 会自动读取

**7.2 Memory — 跨会话记忆**
```bash
/memory add "我们的支付集成使用 Stripe"
/memory list
```

**7.3 MCP — Model Context Protocol**
MCP 让 Claude 连接到外部工具：
```bash
claude mcp add linear \
  --env LINEAR_API_KEY=xxx \
  --env LINEAR_TEAM_ID=xxx
```

**实操任务：**
- [ ] 为你的项目创建 `CLAUDE.md`
- [ ] 用 `/memory add` 添加一个项目关键信息
- [ ] 配置一个 MCP 工具

---

### 第8课：Agent 团队与并行任务
**学习目标：** 使用 Claude Code 的多 Agent 能力，同时处理多个开发任务

**8.1 并行 Agent 团队**
```bash
/team \
  --agent backend:"重构认证模块" \
  --agent frontend:"更新登录界面" \
  --agent tests:"为认证模块写集成测试"
```

**实操任务：**
- [ ] 启动一个 Agent 完成一项重构任务
- [ ] 用 `/team` 启动两个并行 Agent

---

### 第9课：Git 与 CI/CD 集成
**学习目标：** 在 Git 工作流中深度使用 Claude Code

**9.1 提交（Commit）**
```bash
"帮我创建 commit，描述这次添加的功能：实现了用户头像上传功能"
```

**9.2 代码审查（Review）**
```bash
"审查 src/auth.py 的改动，关注安全性"
```

**9.3 GitHub Actions CI/CD**
在 `.github/workflows/` 中集成 Claude Code

**实操任务：**
- [ ] 修改几个文件后，让 Claude 创建 commit
- [ ] 让 Claude 审查你最近的 commit

---

## 模块 4：Cursor 进阶（3课时）

### 第10课：Cursor 进阶 — Plan Mode / Agent Review / Rules
**学习目标：** 掌握 Cursor 的高级功能

**10.1 Plan Mode — 复杂功能的规划与预览**
打开 Plan Mode：`Cmd+Shift+P` → "Cursor: Toggle Plan Mode"
- 描述你想要的功能
- Claude 生成实施计划（分步骤）
- **你可以逐个步骤确认**再执行

**10.2 Rules for AI — 项目规范**
创建 `.cursorrules` 文件定义项目规范

**10.3 Subagents — 子代理**
在 Cursor 中启动专门的子代理处理特定任务

**实操任务：**
- [ ] 开启 Plan Mode，让 Claude 规划一个小功能
- [ ] 创建 `.cursorrules` 文件定义项目规范

---

## 模块 5：Codex CLI 进阶（2课时）

### 第11课：Codex 多任务与并行开发
**学习目标：** 使用 Git Worktree 实现并行开发

**11.1 Git Worktree + Codex**
```bash
# 创建新的 worktree
git worktree add ../my-feature feature-branch

# 在不同 worktree 中启动 Codex
cd ../feature-a && codex --context "专注于用户认证功能"
```

---

## 模块 6：高级主题（3课时）

### 第12课：MCP 生态 — 连接一切工具
**学习目标：** 理解 MCP 协议，会配置和使用 MCP 工具

**常用 MCP 服务器：**
| MCP 工具 | 功能 |
|---------|------|
| `@modelcontextprotocol/server-filesystem` | 文件读写 |
| `@modelcontextprotocol/server-git` | Git 操作 |
| `linear` | Linear 项目管理 |

---

### 第13课：Prompt 工程与工具调优
**学习目标：** 掌握给 AI 编程工具写高质量提示词的技巧

**四大原则：**
1. **明确任务边界** — 具体指出文件路径、错误信息
2. **提供上下文** — 技术栈、约束、参考代码
3. **指定输出格式** — 要什么格式的输出
4. **分步骤引导** — 大任务分解为小步骤

---

### 第14课：构建你的 AI Coding 工作流
**学习目标：** 整合三个工具，构建高效的日常开发工作流

**典型场景：**
```
新功能开发：
Cursor Plan Mode → 规划功能方案
Cursor Composer → 生成核心代码
Cursor Chat → 审查和优化
Claude Code → 写测试和文档
Codex CLI → 快速 lint fix
```

---

## 附录

### A. 快捷键速查表

**Claude Code**
| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/model` | 切换模型 |
| `/memory` | 记忆管理 |
| `/skills` | 技能管理 |

**Cursor**
| 快捷键 | 功能 |
|--------|------|
| `Cmd+K` | Composer |
| `Cmd+L` | Chat |
| `Cmd+I` | Inline Chat |

**Codex CLI**
| 命令 | 功能 |
|------|------|
| `/code` | 执行代码任务 |
| `/review` | 代码审查 |
| `/fix` | 修复问题 |

### B. 官方资源链接

- Claude Code Docs: https://code.claude.com/docs
- Cursor Docs: https://www.cursor.com/docs
- Codex GitHub: https://github.com/openai/codex

### C. 推荐视频教程清单

**Claude Code:**
- ✅ [Tech With Tim - 35分钟入门](https://www.youtube.com/watch?v=ntDIxaeo3Wg)
- ✅ [Anthropic官方 - 30分钟精通](https://www.youtube.com/watch?v=6eBSHbLKuN0)
- ✅ [Kevin Stratvert - 14分钟速成](https://www.youtube.com/watch?v=eMZmDH3T2bY)

**Cursor:**
- ✅ [Tech With Tim - 15分钟入门](https://www.youtube.com/watch?v=ocMOZpuAMw4)
- ✅ [Tech With Tim - Cursor 2.0 27分钟](https://www.youtube.com/watch?v=l30Eb76Tk5s)
- ✅ [Zinho - 13分钟掌握](https://www.youtube.com/watch?v=-SkWL0MK9Ec)

**Codex CLI:**
- ✅ [pookie - 完整入门指南](https://www.youtube.com/watch?v=sTE0G95uEIw)
- ✅ [Keith AI - 26分钟精通](https://www.youtube.com/watch?v=EwVs3O2Zm6I)
