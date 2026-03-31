# 15 - Hook 系统

## 概述

Hook 系统允许在 Claude Code 的关键事件点（工具使用前后、会话开始、权限请求等）注入自定义逻辑。支持 Shell 命令、LLM Prompt、多轮 Agent、HTTP Webhook 四种执行方式。

- **执行引擎**：`utils/hooks/`（17 个文件）
- **Schema 定义**：`schemas/hooks.ts`
- **配置管理**：`utils/hooks/hooksConfigManager.ts`

## Hook 事件（19+ 种）

### 工具相关

| 事件 | 触发时机 | 匹配字段 |
|------|---------|----------|
| `PreToolUse` | 工具执行**前** | `tool_name` |
| `PostToolUse` | 工具执行**后**（成功） | `tool_name` |
| `PostToolUseFailure` | 工具执行**后**（失败） | `tool_name` |
| `PermissionDenied` | Auto 模式分类器拒绝工具 | `tool_name` |
| `PermissionRequest` | 权限对话框显示时 | `tool_name` |

### 会话相关

| 事件 | 触发时机 | 匹配字段 |
|------|---------|----------|
| `SessionStart` | 新会话开始 | `source`（startup/resume/clear/compact） |
| `SessionEnd` | 会话结束 | `reason` |
| `UserPromptSubmit` | 用户提交 Prompt | — |
| `Stop` | Claude 准备结束回复前 | — |
| `StopFailure` | 因 API 错误结束 | `error` 类型 |

### Agent 相关

| 事件 | 触发时机 | 匹配字段 |
|------|---------|----------|
| `SubagentStart` | 子 Agent 启动 | `agent_type` |
| `SubagentStop` | 子 Agent 结束 | `agent_type` |
| `TeammateIdle` | 队友进入空闲 | — |
| `TaskCreated` | 任务创建 | — |
| `TaskCompleted` | 任务完成 | — |

### 压缩相关

| 事件 | 触发时机 | 匹配字段 |
|------|---------|----------|
| `PreCompact` | 压缩前 | `trigger`（manual/auto） |
| `PostCompact` | 压缩后 | `trigger` |

### 通知与 MCP

| 事件 | 触发时机 | 匹配字段 |
|------|---------|----------|
| `Notification` | 通知发送时 | `notification_type` |
| `Setup` | 仓库设置（init/维护） | `trigger` |
| `Elicitation` | MCP 服务器请求用户输入 | `mcp_server_name` |
| `ElicitationResult` | 用户回应 MCP 请求 | `mcp_server_name` |

## Hook 类型（5 种）

### ① Command（Shell 命令）

```typescript
{
  type: 'command',
  command: string,              // Shell 命令
  shell?: 'bash' | 'powershell', // Shell 类型
  if?: string,                   // 条件表达式
  timeout?: number,              // 超时（毫秒）
  once?: boolean,                // 只执行一次
  async?: boolean,               // 异步执行
  asyncRewake?: boolean,         // 异步完成后唤醒
}
```

**执行方式**：通过子进程执行 Shell 命令。Hook 输入通过环境变量传递。

### ② Prompt（LLM 单轮）

```typescript
{
  type: 'prompt',
  prompt: string,               // Prompt 文本
  if?: string,                  // 条件表达式
  timeout?: number,             // 超时
  model?: string,               // 模型覆盖
  once?: boolean,               // 只执行一次
}
```

**执行方式**：调用 `queryModelWithoutStreaming()`，期望返回 JSON：

```json
{
  "ok": true,          // 是否允许继续
  "reason": "..."      // 可选：原因说明
}
```

### ③ Agent（LLM 多轮）

```typescript
{
  type: 'agent',
  prompt: string,               // 初始 Prompt
  if?: string,                  // 条件
  timeout?: number,             // 超时
  model?: string,               // 模型覆盖
  once?: boolean,               // 只执行一次
}
```

**执行方式**：运行完整的多轮 `query()` 循环，可使用工具（最多 50 轮），通过 `SyntheticOutputTool` 返回结构化输出。

### ④ HTTP（Webhook）

```typescript
{
  type: 'http',
  url: string,                  // Webhook URL
  if?: string,                  // 条件
  timeout?: number,             // 超时
  headers?: Record<string, string>,  // 请求头
  allowedEnvVars?: string[],    // 允许的环境变量
  once?: boolean,               // 只执行一次
}
```

**执行方式**：POST JSON 到指定 URL。

**安全特性**：
- SSRF 防护（`ssrfGuardedLookup`）
- 环境变量插值（仅允许列出的变量）
- 沙箱代理支持

### ⑤ Function（内存回调）

```typescript
{
  type: 'function',
  callback: (messages: Message[], signal?: AbortSignal) => boolean | Promise<boolean>,
  errorMessage: string,         // 错误消息
  timeout?: number,             // 超时
  id?: string,                  // 标识
}
```

**特点**：
- 仅限会话作用域（不可持久化）
- 用于内部程序化 Hook

## Hook 配置

### 配置结构

```json
// settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "eslint --check $FILE_PATH",
            "timeout": 10000
          }
        ]
      },
      {
        "matcher": "Bash(npm *)",
        "hooks": [
          {
            "type": "http",
            "url": "https://audit.example.com/check",
            "headers": { "Authorization": "Bearer $API_TOKEN" },
            "allowedEnvVars": ["API_TOKEN"]
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Session started at $(date)' >> ~/.claude/session.log"
          }
        ]
      }
    ]
  }
}
```

### Schema

```typescript
// schemas/hooks.ts
HooksSchema = Record<HookEvent, HookMatcher[]>

type HookMatcher = {
  matcher?: string       // 匹配模式（工具名、通配符等）
  hooks: HookCommand[]   // 要执行的 Hook 列表
}
```

## Hook 来源与优先级

```typescript
type HookSource =
  | 'policySettings'   // 企业策略（最高）
  | 'userSettings'     // 用户设置
  | 'projectSettings'  // 项目设置
  | 'localSettings'    // 本地设置
  | 'sessionHook'      // 会话 Hook
  | 'pluginHook'       // 插件 Hook
  | 'builtinHook'      // 内置 Hook
```

### 合并规则

```typescript
function getAllHooks(): MergedHooks {
  // 1. 聚合所有来源的 Hook
  // 2. 如果 allowManagedHooksOnly=true，只运行托管 Hook
  // 3. 按来源优先级排序
}
```

## Hook 执行流程

### PreToolUse 示例

```
Claude 请求使用 FileWrite 工具
     │
     ▼
匹配 PreToolUse 事件的所有 Hook
     │
     ├─► matcher: "Write" → 匹配！
     │     │
     │     ▼
     │   执行 Hook（command/prompt/http/agent）
     │     │
     │     ├─ 返回 ok=true  → 继续执行工具
     │     ├─ 返回 ok=false → 阻止工具执行
     │     └─ 超时/错误     → 根据配置处理
     │
     └─► matcher: "Bash" → 不匹配，跳过
```

### Hook 结果

```typescript
type HookResult = {
  ok: boolean        // 是否允许继续
  reason?: string    // 原因说明
}
```

## 支持文件

| 文件 | 功能 |
|------|------|
| `hooksConfigManager.ts` | Hook 配置管理器，事件定义 |
| `hooksSettings.ts` | Hook 来源管理，多源聚合 |
| `hookEvents.ts` | Hook 事件发射（started/progress/response） |
| `hookHelpers.ts` | Hook 辅助工具（参数注入、结构化输出） |
| `execPromptHook.ts` | Prompt Hook 执行器 |
| `execAgentHook.ts` | Agent Hook 执行器 |
| `execHttpHook.ts` | HTTP Hook 执行器 |
| `ssrfGuard.ts` | SSRF 防护 |
| `hooksConfigSnapshot.ts` | Hook 配置快照 |
| `registerSkillHooks.ts` | 技能前端事项 Hook 注册 |
| `sessionHooks.ts` | 会话作用域 Hook |

## 使用场景示例

### 代码质量检查

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "eslint $FILE_PATH --fix",
            "timeout": 15000
          }
        ]
      }
    ]
  }
}
```

### 安全审计

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(rm *)",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "分析此命令是否安全：{{command}}",
            "model": "haiku"
          }
        ]
      }
    ]
  }
}
```

### 会话记录

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "http",
            "url": "https://logs.example.com/sessions",
            "headers": { "Authorization": "Bearer $LOG_TOKEN" },
            "allowedEnvVars": ["LOG_TOKEN"]
          }
        ]
      }
    ]
  }
}
```
