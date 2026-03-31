# 10 - 多 Agent 协调

## 概述

Claude Code 支持**多 Agent 协调模式（Coordinator Mode）**，允许一个主 Agent（协调器）派生多个子 Agent（工人）并行执行任务。

- **协调器逻辑**：`coordinator/coordinatorMode.ts`
- **Agent 工具**：`tools/AgentTool/`
- **任务管理**：`tools/task/`
- **状态管理**：`state/` 中的 tasks 和 agentNameRegistry

## 架构

```
┌───────────────────────────────────────────────┐
│                用户                            │
│                  │                             │
│                  ▼                             │
│            ┌──────────┐                        │
│            │ 协调器    │                        │
│            │(Coordinator)                      │
│            │          │                        │
│            │ 规划任务  │                        │
│            │ 分配工人  │                        │
│            │ 综合结果  │                        │
│            └──┬───┬───┘                        │
│               │   │                            │
│         ┌─────┘   └─────┐                      │
│         ▼               ▼                      │
│    ┌─────────┐    ┌─────────┐                  │
│    │ 工人 A  │    │ 工人 B  │    ┌─────────┐   │
│    │(Worker) │    │(Worker) │    │ 工人 C  │   │
│    │         │    │         │    │(Worker) │   │
│    │ Bash    │    │ Search  │    │         │   │
│    │ Edit    │    │ Read    │    │ Edit    │   │
│    │ Search  │    │ LSP     │    │ Test    │   │
│    └─────────┘    └─────────┘    └─────────┘   │
│         │               │              │       │
│         └───────┬───────┘              │       │
│                 ▼                      │       │
│         <task-notification>            │       │
│         返回给协调器                    │       │
└───────────────────────────────────────────────┘
```

## 激活方式

### 特性门控 + 环境变量

```typescript
function isCoordinatorMode(): boolean {
  // 需要同时满足：
  // 1. 编译时特性开关 COORDINATOR_MODE
  // 2. 环境变量 CLAUDE_CODE_COORDINATOR_MODE=true
  if (feature('COORDINATOR_MODE')) {
    return isEnvTruthy(process.env.CLAUDE_CODE_COORDINATOR_MODE)
  }
  return false
}
```

### 会话恢复匹配

```typescript
// 恢复会话时，自动匹配之前的模式
function matchSessionMode(
  sessionMode: 'coordinator' | 'normal' | undefined
): string | undefined {
  // 如果之前是 coordinator 模式，恢复时自动设置环境变量
}
```

## 协调器系统提示

协调器获得**完全不同的系统提示**：

```
角色：你是一个协调器。你的工作是指导工人、综合结果、与用户沟通。

可用工具：
  • Agent      — 派生新工人
  • SendMessage — 向现有工人发送消息
  • TaskStop   — 停止运行中的工人
  • subscribe_pr_activity   — 订阅 GitHub PR 事件
  • unsubscribe_pr_activity — 取消订阅

工作流阶段：
  1. 研究 (Research)     — 调查和信息收集
  2. 综合 (Synthesis)    — 分析和规划
  3. 实施 (Implementation) — 执行变更
  4. 验证 (Verification)  — 测试和审查
```

## Agent 工具

### AgentTool 参数

```typescript
type AgentToolInput = {
  description: string        // 3-5 词任务描述
  prompt: string             // 完整任务描述
  subagent_type?: string     // Agent 类型
  model?: 'sonnet' | 'opus' | 'haiku'  // 模型选择
  run_in_background?: boolean // 后台运行
  name?: string              // 多 Agent 命名
  team_name?: string         // 团队上下文
  mode?: string              // 权限模式
  isolation?: 'worktree' | 'remote'  // 隔离方式
  cwd?: string               // 工作目录
}
```

### 隔离模式

#### Worktree 隔离

每个工人在独立的 Git Worktree 中工作：

```
项目根目录/
  ├── .git/                    ← 共享 Git 仓库
  ├── 主工作区/                 ← 协调器
  ├── .git-worktrees/
  │     ├── worker-A/          ← 工人 A 的独立工作树
  │     │     └── (完整代码副本)
  │     └── worker-B/          ← 工人 B 的独立工作树
  │           └── (完整代码副本)
```

**优点**：
- 工人可以修改不同文件而不冲突
- 每个工人可以在不同分支上工作
- 完成后合并回主分支

#### Remote 隔离

工人在 CCR（Claude Code Remote）环境中运行。

#### Same-Dir 模式

工人共享同一目录（默认，需要小心文件冲突）。

```typescript
type SpawnMode = 'single-session' | 'worktree' | 'same-dir'
```

## 任务状态管理

### AppState 中的任务字段

```typescript
// state/AppStateStore.ts
{
  tasks: Record<string, TaskState>,     // 所有任务
  agentNameRegistry: Map<string, AgentId>,  // 名称 → ID
  foregroundedTaskId: string | undefined,   // 前台任务
  viewingAgentTaskId: string | undefined,   // 正在查看的
  coordinatorTaskIndex: number | undefined, // 协调器索引
}
```

### 任务类型

```typescript
type TaskState =
  | InProcessTeammateTaskState    // 同进程队友任务
  | LocalAgentTaskState           // 本地 Agent 任务

type InProcessTeammateTaskState = {
  type: 'in-process'
  taskId: string
  agentName: string
  status: 'running' | 'completed' | 'failed' | 'stopped'
  messages: Message[]      // 任务对话历史
  summary?: string         // 任务摘要
}
```

### 队友视图

```typescript
// state/teammateViewHelpers.ts

// 进入队友视图（查看工人的对话）
function enterTeammateView(taskId: string): void

// 退出队友视图
function exitTeammateView(): void

// 生命周期：retain / release
```

## 工人结果通知

工人完成或更新时，结果以 XML 格式注入到协调器的用户消息中：

```xml
<task-notification>
  <task-id>worker-abc-123</task-id>
  <status>completed</status>
  <summary>完成了 API endpoint 的实现</summary>
  <result>
    创建了 3 个新文件：
    - src/api/users.ts
    - src/api/middleware.ts
    - test/api/users.test.ts
    所有测试通过。
  </result>
  <usage>
    Token 使用: 15,234 输入 / 3,456 输出
  </usage>
</task-notification>
```

## 工人上下文

### 工人可用工具

工人获得标准工具集（`ASYNC_AGENT_ALLOWED_TOOLS`），但**排除**协调器专用工具：

```
排除的工具：
  • TeamCreate    — 创建团队
  • TeamDelete    — 删除团队
  • SendMessage   — Agent 间通信
  • SyntheticOutput — 合成输出
```

### 共享 Scratchpad

当 `tengu_scratch` 门控启用时，工人可以使用共享便签本：

```typescript
function getCoordinatorUserContext(
  mcpClients: ReadonlyArray<{ name: string }>,
  scratchpadDir?: string
): { [k: string]: string } {
  // 返回工人可见的上下文
  // 包括 MCP 服务器列表和便签本路径
}
```

## 团队工具

### TeamCreate

创建命名团队，用于组织多个工人。

### TeamDelete

删除团队及其所有工人。

### SendMessage

向现有工人发送后续指令：

```typescript
type SendMessageInput = {
  agentId: string    // 目标工人 ID
  message: string    // 消息内容
}
```

## 并发管理

### 最大会话数

```typescript
config.maxSessions  // 默认 32
```

### 容量唤醒

```typescript
// bridge/capacityWake.ts
// 当工人完成时，唤醒等待容量的协调器
```

### 心跳

协调器定期向活跃工人发送心跳，检测工人是否存活。

## 使用流程

```
1. 用户请求复杂任务
     │
2. 协调器分析任务并制定计划
     │
3. 协调器使用 Agent 工具派生多个工人
     │ Agent(prompt="搜索所有 API endpoint", name="researcher")
     │ Agent(prompt="编写测试用例", name="tester")
     │
4. 工人并行执行
     │ researcher → GrepTool, FileReadTool
     │ tester → FileWriteTool, BashTool
     │
5. 工人完成后通过 <task-notification> 通知协调器
     │
6. 协调器综合结果
     │
7. 需要时，协调器通过 SendMessage 向工人发送后续指令
     │
8. 协调器向用户汇报最终结果
```
