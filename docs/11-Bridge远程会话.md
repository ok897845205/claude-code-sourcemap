# 11 - Bridge 远程会话

## 概述

Bridge 系统使 Claude Code 能够被 **claude.ai** 远程控制，实现"远程终端"体验。它包含两种运行模式和完整的认证、通信、会话管理体系。

- **核心目录**：`bridge/`（31 个文件）
- **两种模式**：Bridge 守护进程、REPL Bridge

## 架构概览

```
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│   claude.ai  │◄───────►│  Anthropic Cloud │◄───────►│  Claude Code │
│   (浏览器)   │   HTTP  │  (Session 路由)  │   HTTP  │  (本地终端)  │
└──────────────┘         └──────────────────┘         └──────────────┘
                                                              │
                                                     ┌───────┼────────┐
                                                     │                │
                                               ┌─────▼─────┐  ┌──────▼──────┐
                                               │ Bridge 守护│  │ REPL Bridge │
                                               │ 进程模式   │  │ 附加模式    │
                                               └───────────┘  └─────────────┘
```

## 两种运行模式

### ① Bridge 守护进程 (`claude remote-control`)

```
bridgeMain.ts — runBridgeLoop()
     │
     ├─► 1. 注册环境 (registerBridgeEnvironment)
     │
     ├─► 2. 轮询工作 (pollForWork)
     │        ↻ 循环等待新会话请求
     │
     ├─► 3. 接收工作项 (WorkResponse)
     │        解码 WorkSecret
     │
     ├─► 4. 派生子进程 (spawner.spawn)
     │        创建新的 claude 实例
     │
     ├─► 5. 心跳 (heartbeatWork)
     │        定期续租
     │
     └─► 6. 清理 (stopWork + archiveSession)
```

**特点**：
- 持久运行的守护进程
- 可管理多个并发会话（最大 32）
- 每个会话对应一个子 claude 进程
- 支持 Worktree 隔离

### ② REPL Bridge（附加模式）

```
replBridge.ts / initReplBridge.ts
     │
     ├─► 1. 创建会话 (createBridgeSession)
     │
     ├─► 2. 连接传输层 (Transport)
     │
     ├─► 3. 双向消息转发
     │        claude.ai ←→ 本地 REPL
     │
     └─► 4. 权限请求转发
```

**特点**：
- 附加到已运行的 REPL 会话
- 共享同一个 claude 进程
- 实时双向同步

## 核心类型

### BridgeConfig

```typescript
type BridgeConfig = {
  dir: string              // 工作目录
  machineName: string      // 机器名
  branch: string           // Git 分支
  gitRepoUrl: string | null // Git 仓库 URL
  maxSessions: number      // 最大并发会话数（默认 32）
  spawnMode: SpawnMode     // 派生模式
  verbose: boolean         // 详细日志
  sandbox: boolean         // 沙箱模式
  bridgeId: string         // Bridge ID
  workerType: string       // 工人类型
  environmentId: string    // 环境 ID
  apiBaseUrl: string       // API 基础 URL
  sessionIngressUrl: string // 会话入口 URL
  sessionTimeoutMs?: number // 会话超时
}
```

### WorkResponse

```typescript
type WorkResponse = {
  id: string               // 工作项 ID
  type: 'work'
  environment_id: string
  state: string            // 工作状态
  data: WorkData           // 工作数据（含 secret）
  secret: string           // Base64URL 编码的 WorkSecret
  created_at: string       // 创建时间
}
```

### WorkSecret

```typescript
type WorkSecret = {
  version: number                    // 版本号
  session_ingress_token: string      // 入口 Token
  api_base_url: string               // API 基础 URL
  sources: Array<{
    type: string
    git_info?: { repo_url; branch; commit }
  }>
  auth: Array<{
    type: string
    token: string                    // JWT
  }>
  claude_code_args?: Record<string, string>  // CLI 参数
  mcp_config?: unknown               // MCP 配置
  environment_variables?: Record<string, string>
  use_code_sessions?: boolean        // CCR v2 选择器
}
```

### SessionHandle

```typescript
type SessionHandle = {
  sessionId: string
  done: Promise<SessionDoneStatus>   // 完成 Promise
  kill(): void                       // 正常终止
  forceKill(): void                  // 强制终止
  activities: SessionActivity[]      // 活动记录
  currentActivity: SessionActivity | null
  accessToken: string                // 访问令牌
  lastStderr: string[]              // 最后的 stderr
  writeStdin(data: string): void    // 写入 stdin
  updateAccessToken(token: string): void
}
```

## Bridge API 客户端

```typescript
type BridgeApiClient = {
  // 注册环境
  registerBridgeEnvironment(config)
    : Promise<{ environment_id, environment_secret }>

  // 轮询工作
  pollForWork(environmentId, secret, signal?, reclaimMs?)
    : Promise<WorkResponse | null>

  // 确认工作
  acknowledgeWork(environmentId, workId, sessionToken)
    : Promise<void>

  // 停止工作
  stopWork(environmentId, workId, force)
    : Promise<void>

  // 注销环境
  deregisterEnvironment(environmentId)
    : Promise<void>

  // 发送权限响应
  sendPermissionResponseEvent(sessionId, event, token)
    : Promise<void>

  // 归档会话
  archiveSession(sessionId)
    : Promise<void>

  // 重连会话
  reconnectSession(environmentId, sessionId)
    : Promise<void>

  // 心跳
  heartbeatWork(environmentId, workId, token)
    : Promise<{ lease_extended, state }>
}
```

### 安全措施

```typescript
// ID 验证 — 防止路径遍历
const SAFE_ID_PATTERN = /^[a-zA-Z0-9_-]+$/

// OAuth 重试
async function withOAuthRetry(fn) {
  // 401 时单次刷新 Token 重试
}

// Beta 版本头
'anthropic-beta: environments-2025-11-01'
```

## 传输层

### V1 传输：WebSocket + HTTP POST

```typescript
// HybridTransport
// 读取：WebSocket 连接到 Session Ingress
// 写入：HTTP POST 到 Session Ingress

function createV1ReplTransport(hybrid: HybridTransport): ReplBridgeTransport
```

### V2 传输：SSE + CCR Client

```typescript
// 读取：Server-Sent Events (SSE)
// 写入：CCR v2 /worker/* HTTP API

async function createV2ReplTransport(opts: {
  sessionUrl: string           // 会话 URL
  ingressToken: string         // 入口 Token
  sessionId: string
  initialSequenceNum?: number  // 初始序列号
  epoch?: number               // 时代号（重连）
  heartbeatIntervalMs?: number
  heartbeatJitterFraction?: number
  outboundOnly?: boolean       // 仅出站
  getAuthToken?: () => string | undefined
}): Promise<ReplBridgeTransport>
```

### 传输接口

```typescript
type ReplBridgeTransport = {
  // 写入
  write(message: StdoutMessage): Promise<void>
  writeBatch(messages: StdoutMessage[]): Promise<void>
  flush(): Promise<void>

  // 连接管理
  connect(): void
  close(): void
  isConnectedStatus(): boolean
  getStateLabel(): string

  // 事件回调
  setOnData(callback: (data: string) => void): void
  setOnClose(callback: (closeCode?: number) => void): void
  setOnConnect(callback: () => void): void

  // 序列号与投递
  getLastSequenceNum(): number
  readonly droppedBatchCount: number
  reportState(state: SessionState): void
  reportMetadata(metadata: Record<string, unknown>): void
  reportDelivery(eventId, status: 'processing' | 'processed'): void
}
```

## REPL Bridge Handle

```typescript
type ReplBridgeHandle = {
  bridgeSessionId: string
  environmentId: string
  sessionIngressUrl: string

  // 消息发送
  writeMessages(messages: Message[]): void
  writeSdkMessages(messages: SDKMessage[]): void

  // 控制请求
  sendControlRequest(request: SDKControlRequest): void
  sendControlResponse(response: SDKControlResponse): void
  sendControlCancelRequest(requestId: string): void

  // 结果与拆卸
  sendResult(): void
  teardown(): Promise<void>
}

type BridgeState = 'ready' | 'connected' | 'reconnecting' | 'failed'
```

## 消息路由

```typescript
// bridgeMessaging.ts

// 类型守卫
function isSDKMessage(value: unknown): value is SDKMessage
function isSDKControlResponse(value): value is SDKControlResponse
function isSDKControlRequest(value): value is SDKControlRequest

// Bridge 消息过滤
function isEligibleBridgeMessage(m: Message): boolean
// 只有 user、assistant（非虚拟）、system local_command 消息

// 入站消息处理（含去重）
function handleIngressMessage(
  data, recentPostedUUIDs, recentInboundUUIDs,
  onInboundMessage?, onPermissionResponse?, onControlRequest?
): void
```

## 认证体系

### OAuth 认证

标准 OAuth 2.0 PKCE 流程获取访问令牌。

### 可信设备 (Trusted Device)

```typescript
// bridge/trustedDevice.ts

// 门控：tengu_sessions_elevated_auth_enforcement
function getTrustedDeviceToken(): string | undefined
function clearTrustedDeviceTokenCache(): void
function clearTrustedDeviceToken(): void
async function enrollTrustedDevice(): Promise<void>
```

**注册流程**：

```
1. 用户执行 /login
                │
2. POST /api/auth/trusted_devices
   Body: { display_name: "Claude Code on {hostname} · {platform}" }
                │
3. 服务器验证 account_session.created_at < 10min
   （必须在登录后 10 分钟内注册）
                │
4. 返回设备令牌
                │
5. 存储到 OS 密钥链 (secureStorage)
                │
6. 后续请求：X-Trusted-Device-Token 头
```

### Token 刷新

```typescript
// createTokenRefreshScheduler
// JWT 过期前 5 分钟自动刷新

// V1：直接 OAuth 刷新
// V2：调用 reconnectSession 由服务器重新分发
```

## 会话生命周期

```
┌─ 创建 ──────────────────────────────────────────────────┐
│                                                         │
│  POST /v1/sessions                                      │
│  Body: { environment_id, title, events, git_info, ... } │
│  Response: { session_id }                               │
│                                                         │
├─ 活跃 ──────────────────────────────────────────────────┤
│                                                         │
│  双向消息交换（通过传输层）                                 │
│  定期心跳（heartbeatWork）                                │
│  权限请求转发                                             │
│  活动跟踪（tool_use, text, result）                       │
│                                                         │
├─ 完成 ──────────────────────────────────────────────────┤
│                                                         │
│  stopWork(environmentId, workId, force)                  │
│  archiveSession(sessionId)                               │
│  清理 Worktree（如有）                                    │
│                                                         │
├─ 重连 ──────────────────────────────────────────────────┤
│                                                         │
│  reconnectSession(environmentId, sessionId)              │
│  恢复传输连接                                             │
│  从 lastSequenceNum 续传                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 退避策略

```typescript
type BackoffConfig = {
  connInitialMs: 2000     // 初始等待 2 秒
  connCapMs: 120000       // 最大等待 120 秒
  connGiveUpMs: 600000    // 放弃时间 600 秒
}
```

指数退避，在轮询工作时遇到错误后逐渐增加等待时间。

## 会话派生

```typescript
// bridge/sessionRunner.ts
type SessionSpawnerDeps = {
  execPath: string            // 可执行路径
  scriptArgs: string[]        // 脚本参数
  env: NodeJS.ProcessEnv      // 环境变量
  verbose: boolean
  sandbox: boolean
  debugFile?: string          // 调试日志文件
  permissionMode?: string     // 权限模式
  onDebug: (msg) => void
  onActivity?: (sessionId, activity) => void
  onPermissionRequest?: (sessionId, request, accessToken) => void
}
```

子进程的 stdout 被解析为活动事件（tool_use、text、result）和权限请求。
