# AI 开发工具培训课程（完整版）
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

**核心内容：**

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

**1.5 首次登录与认证**
首次使用会提示登录 Claude 账户（Pro/Max/Teams/Enterprise）或 Anthropic Console

**实操任务：**
- [ ] 安装 Claude Code
- [ ] 在任意项目中启动 `claude`
- [ ] 输入第一个问题："这个项目是做什么的？"

---

### 第2课：与 Claude Code 对话（Ask & Act）
**学习目标：** 学会提问、让 Claude 读写文件、执行命令

**核心内容：**

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

**2.3 让 Claude 读写文件**
```bash
# 让 Claude 读取文件内容
"请读取 src/main.py 并解释它的作用"

# 让 Claude 写文件
"请帮我创建一个用户认证的 Express 中间件，保存在 src/middleware/auth.js"
```

**2.4 让 Claude 执行终端命令**
```bash
"请运行 npm install 安装依赖，然后运行 npm test 看测试是否通过"
```
Claude 会：
1. 询问你是否允许执行命令
2. 执行后显示输出
3. 继续下一步骤

**2.5 查看完整可用工具列表**
```bash
/help tools
```

**实操任务：**
- [ ] 让 Claude 读取项目中的任意文件
- [ ] 让 Claude 解释一段代码的功能
- [ ] 让 Claude 执行一个终端命令（如 `ls -la`）

---

### 第3课：Cursor 基础 — 安装与核心界面
**学习目标：** 熟悉 Cursor 编辑器，了解与传统 VS Code 的区别

**核心内容：**

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

**3.3 核心界面介绍**
```
┌─────────────────────────────────────────────────┐
│  🔍 Search (Cmd+K)   │   💬 Chat Panel          │
│                      │                          │
│  [代码编辑区]         │  AI 对话区                │
│                      │                          │
├──────────────────────┴──────────────────────────┤
│  [状态栏: 模型选择 | Agent状态 | 文件索引状态]     │
└─────────────────────────────────────────────────┘
```

**3.4 快捷键（与 VS Code 兼容 + 新增）**
| 快捷键 | 功能 |
|--------|------|
| `Cmd+K` | 打开 Composer（代码生成）|
| `Cmd+L` | 打开 Chat（问答）|
| `Cmd+I` | 打开 Inline Chat（行内编辑）|
| `Cmd+Enter` | 提交 Agent 任务 |
| `Cmd+Shift+L` | 应用到所有相似位置 |

**3.5 支持的模型**
- Claude 4.6 Opus（200k上下文，可扩展至1M）
- GPT-4o / GPT-4.5
- Cursor Small（内置快速模型）

**实操任务：**
- [ ] 下载安装 Cursor
- [ ] 打开/导入一个已有项目
- [ ] 使用 `Cmd+K` 生成一个 "Hello World" 函数
- [ ] 使用 `Cmd+L` 询问项目结构

---

### 第4课：Cursor 核心功能 — Cmd K / Composer / Chat
**学习目标：** 掌握 Cursor 的三大核心操作方式

**核心内容：**

**4.1 Cmd K — 即时代码生成与编辑**
- 选中代码 → Cmd+K → 描述想要的变化
- 或直接 Cmd+K 输入新功能需求
- 支持多行编辑建议

```javascript
// 选中这段代码后，用 Cmd+K 说 "转换为 async/await"
// 原来：
fetch('/api/users').then(res => res.json()).then(data => console.log(data))

// Claude 会改写为：
const response = await fetch('/api/users');
const data = await response.json();
console.log(data);
```

**4.2 Composer — 多文件生成器**
Composer 是 Cursor 最强大的功能之一，可以：
- 一次生成多个相关文件
- 理解项目整体结构
- 保持代码风格一致

使用方式：
1. `Cmd+K` 打开 Composer
2. 描述你要构建的功能
3. Claude 生成多个文件
4. Review → Accept

**4.3 Chat — 全代码库问答**
- `Cmd+L` 打开 Chat 面板
- 可以 @ 特定文件、文件夹、或 Git commit
- 持续对话，记住上下文

常用指令：
```
@files      引用文件
@folder     引用整个目录
@git        引用 Git 历史
@docs       引用 Cursor 文档
```

**4.4 @Rules — 自定义规则**
在 `.cursorrules` 文件中定义项目规范：
```markdown
# .cursorrules
- 使用 TypeScript strict 模式
- 组件文件用 PascalCase 命名
- API 错误统一返回 { error: string, code: number }
```

**实操任务：**
- [ ] 用 Cmd+K 修改一个现有函数
- [ ] 用 Composer 生成一个完整的 React 组件（包含样式）
- [ ] 用 Chat 询问项目的入口文件和架构

---

### 第5课：OpenAI Codex CLI 入门
**学习目标：** 安装 Codex CLI，在终端中使用 AI 辅助编程

**核心内容：**

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

**5.2 与 Claude Code 的核心区别**
| 特性 | Codex CLI | Claude Code |
|------|-----------|-------------|
| 交互方式 | 纯终端，轻量 | 多界面（CLI/IDE/Web）|
| 安全模型 | Sandbox 隔离 | 权限模式 |
| 并行开发 | Git worktree 多任务 | 串行为主 |
| 厂商 | OpenAI | Anthropic |

**5.3 基础使用**
```bash
# 在项目中启动
cd my-project
codex

# 常用命令
/code  "帮我创建一个新路由处理 /api/products"
/review  "检查最近3个commit的代码质量"
/test  "为 src/utils.ts 编写单元测试"
/fix  "修复 src/auth.py 的登录问题"
```

**5.4 AGENTS.md — 项目级指令**
类似 Claude Code 的 `.claude` 目录，Codex 使用 `AGENTS.md`：
```markdown
# AGENTS.md
## 项目概述
本项目是一个 RESTful API 服务，使用 FastAPI 构建。

## 技术栈
- Python 3.11+
- FastAPI
- PostgreSQL
- Redis

## 代码规范
- 所有路由放在 app/routes/ 目录
- 使用 Pydantic 进行数据验证
```

**5.5 安全模式**
Codex 在 Sandbox 中运行命令，默认：
- 不能访问网络（除非开启）
- 文件操作有历史记录
- 可以配置允许/禁止的命令白名单

**实操任务：**
- [ ] 安装 Codex CLI
- [ ] 在项目中启动 `codex`
- [ ] 创建一个 `AGENTS.md` 文件描述你的项目

---

## 模块 2：三大工具横向对比（2课时）

### 第6课：如何选择 — 场景化对比分析
**学习目标：** 理解每个工具的适用场景，能根据项目需求选择合适的工具

**核心内容：**

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
| 学习曲线 | 中等 | 较低 | 较低 |

**6.2 场景选择指南**

**选 Claude Code 当：**
- 大型代码库（>10万行）
- 需要深度代码理解
- 复杂的 Agent 团队协作
- 需要 MCP 工具扩展
- 已在使用 Slack 集成

**选 Cursor 当：**
- 团队实时协作编程
- 偏好 GUI 化的 AI 交互
- 想要"所见即所得"的编辑体验
- 已经在用 VS Code
- 需要 Plan Mode 规划复杂功能

**选 Codex CLI 当：**
- 追求极致轻量快速
- 终端重度用户
- 需要 Git worktree 并行开发
- 安全要求高（Sandbox）
- 云端 CI/CD 集成

**6.3 组合使用策略**
很多高级用户会组合使用：
- **Cursor** 做日常开发 + 实时协作
- **Claude Code** 做大型重构 + Agent 任务
- **Codex CLI** 做快速修复 + CI/CD 自动化

**实操任务：**
- [ ] 在同一个项目中分别用三个工具完成同一个简单任务
- [ ] 记录每个工具的响应质量、速度、交互体验

---

# 中级课程：AI Coding 进阶

## 模块 3：Claude Code 进阶（4课时）

### 第7课：记忆系统 — Instructions / Memory / Skills
**学习目标：** 让 Claude Code 学习你的项目规范，长期记忆团队约定

**核心内容：**

**7.1 CLAUDE.md — 项目级指令**
在项目根目录创建 `CLAUDE.md`，Claude Code 会自动读取：
```markdown
# CLAUDE.md
## 项目规范
- Python 类型注解必须完整
- Git commit 使用 Conventional Commits 格式
- API 错误统一返回 FastAPI HTTPException

## 技术栈
- FastAPI + Pydantic
- PostgreSQL + SQLAlchemy
- Redis 缓存

## 常用命令
- `make dev` 启动开发服务器
- `make test` 运行测试
- `make migrate` 执行数据库迁移
```

**7.2 Memory — 跨会话记忆**
Claude Code 可以记住关键信息：
```bash
/memory add "我们的支付集成使用 Stripe，API密钥存在环境变量 STRIPE_SECRET_KEY"
```
下次会话中可以直接询问："我们的支付集成用的是什么？"

查看记忆：
```bash
/memory list
/memory remove <id>
```

**7.3 Skills — 扩展技能**
Skills 让你定义 Claude 可以使用的专业技能：
```bash
# 查看内置 skills
/skills list

# 查看某个 skill
/skills show <skill-name>
```

**7.4 Hooks — 自动化钩子**
在 `.claude/hooks/` 中定义自动化行为：
```bash
# pre-commit hook: 自动检查代码格式
# .claude/hooks/pre-commit
#!/bin/bash
make lint
```

**7.5 MCP — Model Context Protocol**
MCP 让 Claude 连接到外部工具：
```bash
# 配置示例：连接 Linear 项目管理
claude mcp add linear \
  --env LINEAR_API_KEY=xxx \
  --env LINEAR_TEAM_ID=xxx
```

常用 MCP：
- **Filesystem**: 安全的文件操作
- **Git**: Git 操作增强
- **Search**: 代码库语义搜索
- **Linear/Jira**: 项目管理集成

**实操任务：**
- [ ] 为你的项目创建 `CLAUDE.md`
- [ ] 用 `/memory add` 添加一个项目关键信息
- [ ] 配置一个 MCP 工具

---

### 第8课：Agent 团队与并行任务
**学习目标：** 使用 Claude Code 的多 Agent 能力，同时处理多个开发任务

**核心内容：**

**8.1 Agent 是什么**
Agent 是一个可以自主完成复杂任务的 AI 子代理：
- 拥有独立的上下文
- 可以使用工具（读写文件、运行命令）
- 与其他 Agent 协作

**8.2 启动 Agent 任务**
```bash
/agent 帮我重构 src/api/ 目录下的所有路由，使用依赖注入模式
```

**8.3 并行 Agent 团队**
Claude Code 支持同时运行多个 Agent：
```bash
# 启动一个 Agent 团队
/team \
  --agent backend:"重构认证模块" \
  --agent frontend:"更新登录界面" \
  --agent tests:"为认证模块写集成测试"
```

**8.4 任务管理与状态**
- Agent 完成任务后会通知你
- 可以查看每个 Agent 的输出
- 支持在任务中途介入调整

**8.5 Subagent — 委托子任务**
在长时间任务中，委托子任务给专门的 Agent：
```bash
# 在主对话中
"请用 /agent 启动一个 Agent 分析 src/utils 中的重复代码并提出重构方案"
```

**实操任务：**
- [ ] 启动一个 Agent 完成一项重构任务
- [ ] 观察 Agent 如何分解任务、执行步骤
- [ ] 用 `/team` 启动两个并行 Agent

---

### 第9课：Git 与 CI/CD 集成
**学习目标：** 在 Git 工作流中深度使用 Claude Code

**核心内容：**

**9.1 提交（Commit）**
```bash
"帮我创建 commit，描述这次添加的功能：实现了用户头像上传功能"
```
Claude 会：
1. 扫描修改的文件
2. 生成符合 Conventional Commits 的 message
3. 显示 diff 预览
4. 确认后执行 commit

**9.2 拉取请求（Pull Request）**
```bash
"帮我创建一个 PR，标题是'添加用户头像上传'，内容要包含：解决的问题、使用的方案、测试说明"
```

**9.3 代码审查（Review）**
```bash
"审查 src/auth.py 的改动，关注安全性"
```
Claude 会：
- 分析代码变更
- 检查潜在 bug
- 提出改进建议
- 标记安全风险

**9.4 GitHub Actions CI/CD**
在 `.github/workflows/` 中集成 Claude Code：
```yaml
# .github/workflows/code-review.yml
name: Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Claude Code Review
        run: |
          claude --print "
          审查这个 PR 的代码变更，
          关注：安全性、性能、代码风格
          " > review.md
      - uses: actions/upload-artifact@v4
        with:
          name: review
          path: review.md
```

**9.5 GitLab CI/CD 集成**
类似 GitHub Actions，Claude Code 也支持 GitLab CI/CD

**实操任务：**
- [ ] 修改几个文件后，让 Claude 创建 commit
- [ ] 让 Claude 审查你最近的 commit
- [ ] 创建一个简单的 GitHub Actions workflow

---

## 模块 4：Cursor 进阶（3课时）

### 第10课：Cursor 进阶 — Plan Mode / Agent Review / Rules
**学习目标：** 掌握 Cursor 的高级功能，提升开发效率

**核心内容：**

**10.1 Plan Mode — 复杂功能的规划与预览**
Plan Mode 是 Cursor 2.0 的核心功能：

1. 打开 Plan Mode：`Cmd+Shift+P` → "Cursor: Toggle Plan Mode"
2. 描述你想要的功能
3. Claude 生成实施计划（分步骤）
4. **你可以逐个步骤确认**再执行
5. 每个步骤显示预估的代码变更

适用场景：
- 大型重构
- 新功能设计
- 不确定如何实施的复杂任务

**10.2 Agent Review — 代码审查**
Cursor 的 Agent 可以做深度代码审查：

1. `Cmd+L` 打开 Chat
2. 输入 `@files src/feature` 
3. "审查这个功能的代码质量和安全性"

Agent Review 会：
- 检查代码逻辑
- 发现潜在的 bug
- 提出改进建议
- 可以直接生成修复代码

**10.3 Rules for AI — 项目规范**
创建 `.cursorrules` 文件：
```markdown
# .cursorrules
## 语言与框架
- TypeScript + React + TailwindCSS
- Next.js App Router
- Prisma ORM + PostgreSQL

## 代码规范
- 组件用 PascalCase，hooks 用 camelCase
- API 响应统一：{ data, error, status }
- 错误处理用 try-catch，异步统一用 async/await

## 安全
- 禁止在前端存储敏感信息
- 所有 API 路由需要认证（除 /api/auth/*）
- 使用环境变量管理密钥
```

**10.4 Skills — 可复用技能**
Skills 允许你定义 Claude 可以执行的复杂操作序列：
```markdown
# skills/deploy.md
## Deploy Skill
这个 skill 用于部署应用到生产环境。

### 步骤
1. 运行 `npm run build` 构建项目
2. 运行 `npm test` 确保测试通过
3. 执行 `deploy script`
4. 验证部署结果
```

**10.5 Subagents — 子代理**
在 Cursor 中启动专门的子代理处理特定任务：
- 后端代理：处理 API 和数据库
- 前端代理：处理 UI 组件
- DevOps 代理：处理部署和配置

**实操任务：**
- [ ] 开启 Plan Mode，让 Claude 规划一个小功能
- [ ] 创建 `.cursorrules` 文件定义项目规范
- [ ] 使用 Agent Review 审查一段代码

---

## 模块 5：Codex CLI 进阶（3课时）

### 第11课：Codex 多任务与并行开发
**学习目标：** 使用 Git Worktree 实现并行开发，用 Codex 同时处理多个任务

**核心内容：**

**11.1 Git Worktree 简介**
Git Worktree 允许你在同一仓库的多个分支上同时工作，不影响彼此：

```bash
# 创建新的 worktree
git worktree add ../my-feature feature-branch

# 列出所有 worktree
git worktree list
```

**11.2 Codex + Worktree 并行任务**
```bash
# 在主分支启动 Codex 监控整体进度
codex

# 在另一个 worktree 启动 Codex 处理功能A
cd ../feature-a
codex --context "专注于用户认证功能"

# 在第三个 worktree 处理功能B
cd ../feature-b
codex --context "专注于支付集成"
```

**11.3 多任务指令**
Codex 支持同时处理多个任务：
```bash
# 并行处理
/codex run "任务1: 修复登录bug" "任务2: 添加单元测试" "任务3: 更新文档"
```

**11.4 任务队列**
```bash
# 添加到队列
/codex queue add "优化数据库查询"
/codex queue add "添加缓存层"

/# 查看队列
/codex queue list

# 执行队列
/codex queue run
```

**11.5 任务结果汇总**
每个任务完成后，Codex 会生成报告：
- 修改了哪些文件
- 执行了哪些命令
- 是否有错误或警告

**实操任务：**
- [ ] 用 Git Worktree 创建两个分支的工作目录
- [ ] 在两个 worktree 中分别用 Codex 处理不同任务
- [ ] 体验并行开发的效率

---

### 第12课：Codex 安全与自动化脚本
**学习目标：** 掌握 Codex 的安全配置和脚本自动化

**核心内容：**

**12.1 Sandbox 安全模式**
Codex 默认在 Sandbox 中运行：
- 文件操作有历史记录，可回滚
- 网络访问受限
- 命令执行有白名单

配置示例：
```json
// ~/.codex/config.json
{
  "sandbox": {
    "enabled": true,
    "allowedCommands": ["npm", "git", "python", "make"],
    "blockedPaths": ["/etc", "/usr", "~/.ssh"]
  }
}
```

**12.2 MCP 与外部工具连接**
Codex 通过 MCP 连接外部工具：
```bash
# 列出可用的 MCP 工具
/codex mcp list

# 添加 MCP 服务器
/codex mcp add filesystem /path/to/mcp-server
```

**12.3 Automation — 自动化脚本**
用 Codex 编写可复用的自动化脚本：
```bash
# 创建自动化脚本
/codex script create "ci-check" "
1. 运行测试
2. 运行 lint
3. 运行 type check
4. 报告结果
"

/# 执行脚本
/codex script run ci-check
```

**12.4 定时任务**
配合 cron 使用 Codex：
```bash
# 每天早上自动检查代码库健康状态
cron:
  schedule: "0 9 * * *"
  command: "codex --print '检查代码库状态，报告：1. 测试通过率 2. lint错误数 3. 最近的问题'"
```

**12.5 在 CI/CD 中使用 Codex**
```yaml
# .github/workflows/codex-ci.yml
name: Codex CI
on: [push, pull_request]
jobs:
  codex:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Codex Check
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          npx @openai/codex --sandbox \
            --check "代码风格检查" \
            --check "安全漏洞扫描"
```

**实操任务：**
- [ ] 配置 Codex 的 Sandbox 安全设置
- [ ] 创建一个自动化脚本处理日常任务
- [ ] 在 CI pipeline 中集成 Codex

---

## 模块 6：高级主题（3课时）

### 第13课：MCP 生态 — 连接一切工具
**学习目标：** 理解 MCP 协议，会配置和使用 MCP 工具

**核心内容：**

**13.1 MCP（Model Context Protocol）是什么**
MCP 是一种标准协议，让 AI 模型连接外部工具和数据源：
- 文件系统
- Git
- 数据库
- API 服务
- 项目管理工具（Linear, Jira）

**13.2 Claude Code 中的 MCP**
```bash
# 列出可用 MCP
claude mcp list

# 添加 MCP 服务器
claude mcp add my-server -- npx -y @modelcontextprotocol/server-filesystem

# 测试 MCP
claude
> 使用 filesystem 工具列出 /tmp 目录
```

**13.3 常用 MCP 服务器**
| MCP 工具 | 功能 |
|---------|------|
| `@modelcontextprotocol/server-filesystem` | 文件读写 |
| `@modelcontextprotocol/server-git` | Git 操作 |
| `@modelcontextprotocol/server-brave-search` | 网络搜索 |
| `@modelcontextprotocol/server-slack` | Slack 消息 |
| `linear` | Linear 项目管理 |

**13.4 在 Cursor 中使用 MCP**
在 Cursor 设置中配置 MCP：
1. `Cmd+,` 打开设置
2. 搜索 "MCP"
3. 添加 MCP 服务器配置

**13.5 自定义 MCP 开发**
```typescript
// my-mcp-server.ts
import { Server } from '@modelcontextprotocol/sdk/server';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server-stdio';

const server = new Server(
  { name: 'my-mcp-server', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler('tools/list', async () => ({
  tools: [{
    name: 'get_weather',
    description: '获取城市天气',
    inputSchema: {
      type: 'object',
      properties: {
        city: { type: 'string' }
      }
    }
  }]
}));

const transport = new StdioServerTransport();
server.connect(transport);
```

**实操任务：**
- [ ] 配置 filesystem MCP 读写项目文件
- [ ] 配置一个 API MCP（如 GitHub 或 Linear）
- [ ] 尝试用 Claude 操作 MCP 工具

---

### 第14课：Prompt 工程与工具调优
**学习目标：** 掌握给 AI 编程工具写高质量提示词的技巧

**核心内容：**

**14.1 给 AI 编程助手写提示词的原则**

**原则1：明确任务边界**
```bash
# ❌ 模糊
"修复这个bug"

# ✅ 明确
"修复 src/api/users.py 中 get_user_by_email() 函数，
当 email 不存在时应返回 None 而不是抛出异常"
```

**原则2：提供上下文**
```bash
# ❌ 无上下文
"添加日志"

# ✅ 有上下文
"在 src/payment/stripe.py 的 process_payment() 函数中添加日志，
使用项目的 logging 配置（已在 CLAUDE.md 中定义），
记录：订单ID、金额、处理结果"
```

**原则3：指定输出格式**
```bash
# ❌ 无格式要求
"优化这个查询"

# ✅ 有格式要求
"优化这个 SQL 查询，使用 EXPLAIN 分析性能，
输出：1) 优化后的SQL 2) 性能对比 3) 索引建议"
```

**原则4：分步骤引导**
```bash
"分三步完成：1) 先理解现有代码 2) 设计新方案 3) 实施并测试"
```

**14.2 Claude Code 特有的提示技巧**
```bash
# 使用 @ 引用上下文
"@src/auth.py 这个模块如何与 @lib/jwt.py 配合工作？"

# 使用 /slient 静默模式（不执行命令）
"解释一下这个算法的复杂度，不用修改代码"

# 使用 /隔板 隔离会话
# 启动新的专注会话，不带历史上下文
/compact
```

**14.3 Cursor 特有的提示技巧**
```bash
# Cmd+K 中使用 Stream Diff
- 输入修改指令
- 实时预览变更
- Tab 逐行接受/拒绝

# @ 文件引用
"@components/Button.tsx 这个按钮组件，
如何在 @pages/Login.tsx 中添加防抖处理？"
```

**14.4 Codex 特有的提示技巧**
```bash
# 使用 /spec 明确规范
/codex "按照 AGENTS.md 的规范，重构 src/api/"

# 使用 /guardrails 设置限制
/codex --guardrails "不要修改 test/ 目录，不要删除任何文件"
```

**14.5 提示词模板库**

**Bug 修复模板：**
```
## Bug 描述
- 文件路径：<path>
- 错误信息：<error_message>
- 复现步骤：
  1. <step1>
  2. <step2>

## 期望行为
<what_should_happen>

## 已尝试的方案
<what_youve_tried>
```

**新功能模板：**
```
## 功能需求
<describe_feature>

## 技术约束
- 语言/框架：<stack>
- 必须使用：<requirements>
- 禁止使用：<prohibitions>

## 参考代码
<existing_code_if_any>

## 验收标准
1. <criterion1>
2. <criterion2>
```

**实操任务：**
- [ ] 用高质量提示词让 Claude Code 完成一个中型任务
- [ ] 对比模糊提示词 vs 高质量提示词的效果差异
- [ ] 为你常用的任务创建提示词模板

---

### 第15课：构建你的 AI Coding 工作流
**学习目标：** 整合三个工具，构建高效的日常开发工作流

**核心内容：**

**15.1 典型日常使用场景**

**场景A：新功能开发**
```
1. Cursor Plan Mode → 规划功能方案
2. Cursor Composer → 生成核心代码
3. Cursor Chat → 审查和优化
4. Claude Code → 写测试和文档
5. Codex CLI → 快速 lint fix
```

**场景B：Bug 修复**
```
1. Claude Code → 分析错误日志
2. Cursor → 定位并修复代码
3. Codex → 写回归测试
4. Claude Code → 创建 commit 和 PR
```

**场景C：代码审查**
```
1. Claude Code → PR 代码审查
2. Cursor → 查看变更对比
3. Codex → 检查安全漏洞
4. Claude Code → 生成审查报告
```

**15.2 团队协作配置**

**共享 .cursorrules（所有工具共用）：**
```markdown
# .cursorrules
## 代码规范
- Prettier 代码格式化
- ESLint + TypeScript strict
- Jest 测试覆盖率 > 80%

## Git 规范
- Conventional Commits
- PR 需要至少 2 人 review
- master/main 受保护
```

**15.3 工作流自动化**

使用 Claude Code 的 hooks：
```
.claude/
├── hooks/
│   ├── pre-commit    # commit 前检查
│   ├── post-checkout # 切换分支提醒
│   └── pre-push      # push 前检查
├── CLAUDE.md         # 项目说明
└── skills/           # 团队共享技能
```

**15.4 效率指标**
建议追踪的指标：
- 每个任务平均交互次数
- AI 生成代码的接受率
- 任务完成时间对比（用AI vs 不用AI）
- 代码审查发现的问题数

**15.5 持续学习资源**
- Claude Code Blog: https://anthropic.com/news
- Cursor Changelog: https://cursor.com/changelog
- OpenAI Codex: https://github.com/openai/codex
- YouTube 频道：Tech With Tim, Kevin Stratvert, Net Ninja

**实操任务：**
- [ ] 选择一个中型任务，用组合工作流完成
- [ ] 记录每个工具的优缺点
- [ ] 为你的团队定制 `.cursorrules`

---

## 附录

### A. 快捷键速查表

**Claude Code**
| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/model` | 切换模型 |
| `/quit` | 退出 |
| `/clear` | 清屏 |
| `/memory` | 记忆管理 |
| `/skills` | 技能管理 |

**Cursor**
| 快捷键 | 功能 |
|--------|------|
| `Cmd+K` | Composer |
| `Cmd+L` | Chat |
| `Cmd+I` | Inline Chat |
| `Cmd+Shift+P` | Command Palette |

**Codex CLI**
| 命令 | 功能 |
|------|------|
| `/code` | 执行代码任务 |
| `/review` | 代码审查 |
| `/fix` | 修复问题 |
| `/test` | 生成测试 |

### B. 官方资源链接

- Claude Code Docs: https://code.claude.com/docs
- Cursor Docs: https://www.cursor.com/docs
- Codex GitHub: https://github.com/openai/codex
- Anthropic Blog: https://www.anthropic.com/news
- Cursor Changelog: https://www.cursor.com/changelog

### C. 推荐视频教程清单

**Claude Code:**
- ✅ [Tech With Tim - 35分钟入门](https://www.youtube.com/watch?v=ntDIxaeo3Wg)
- ✅ [Anthropic官方 - 30分钟精通](https://www.youtube.com/watch?v=6eBSHbLKuN0)
- ✅ [Kevin Stratvert - 14分钟速成](https://www.youtube.com/watch?v=eMZmDH3T2bY)
- ✅ [4小时实战课程](https://www.youtube.com/watch?v=QoQBzR1NIqI)

**Cursor:**
- ✅ [Tech With Tim - 15分钟入门](https://www.youtube.com/watch?v=ocMOZpuAMw4)
- ✅ [Tech With Tim - Cursor 2.0 27分钟](https://www.youtube.com/watch?v=l30Eb76Tk5s)
- ✅ [Zinho - 13分钟掌握](https://www.youtube.com/watch?v=-SkWL0MK9Ec)
- ✅ [2.5小时完整课程](https://www.youtube.com/watch?v=2aldTxnbNt0)

**Codex CLI:**
- ✅ [pookie - 完整入门指南](https://www.youtube.com/watch?v=sTE0G95uEIw)
- ✅ [Keith AI - 26分钟精通](https://www.youtube.com/watch?v=EwVs3O2Zm6I)
- ✅ [OpenAI官方 - 5分钟演示](https://www.youtube.com/watch?v=iqNzfK4_meQ)
