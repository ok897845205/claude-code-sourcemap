# 🎮 AI 游戏创造平台

> 只需用自然语言描述想要的游戏，AI 自动帮你 **生成 → 构建 → 测试 → 部署**。

## ✨ 功能特性

- **自然语言输入** — 描述你想要的游戏，AI 自动理解并设计
- **双引擎支持** — Phaser 2D（经典 2D 游戏）和 Three.js 3D
- **完整流水线** — 分析 → 规划 → 代码生成 → 组装 → 构建 → 测试 → 自动修复
- **多 LLM 支持** — Anthropic Claude、Kimi、MiniMax、DeepSeek、GLM 等
- **实时预览** — 一键预览生成的游戏
- **迭代修改** — "加个双跳功能" — AI 增量修改
- **Web UI + CLI** — 浏览器前端或命令行均可使用

## 🏗️ 架构

```
用户描述: "做一个太空射击游戏"
     │
     ▼
┌─ Analyzer ─┐    解析需求 → GameAnalysis
└─────┬──────┘
      ▼
┌─ Planner ──┐    规划文件结构 → GamePlan
└─────┬──────┘
      ▼
┌─ CodeGen ──┐    并行生成每个 JS 文件（含精灵、音效）
└─────┬──────┘
      ▼
┌─ Assembler ┐    复制模板 + 覆盖生成文件
└─────┬──────┘
      ▼
┌─ Builder ──┐    npm install → validate → vite build → runtime test
└─────┬──────┘
      ▼
┌─ Fixer ────┐    失败时 AI 自动修复（最多 3 轮）
└─────┬──────┘
      ▼
  🎮 可玩的游戏！
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd game-AI-platform

# Python 依赖
pip install -r requirements.txt

# Node.js 依赖（Playwright 用于自动化测试）
npx playwright install chromium
```

### 2. 配置 API Key

```bash
cp config/.env.example config/.env
# 编辑 config/.env，填入你的 API Key
```

支持的 LLM 提供商：

| 提供商 | MODEL_ID | SDK |
|--------|----------|-----|
| Anthropic Claude | claude-sonnet-4-6 | Anthropic |
| MiniMax | MiniMax-M2.5 | Anthropic |
| GLM (智谱) | glm-5 | Anthropic |
| Kimi (月之暗面) | kimi-k2.5 | OpenAI |
| DeepSeek | deepseek-chat | OpenAI |

### 3. 启动

**方式一：Web 界面**

```bash
python run.py
# 打开浏览器访问 http://localhost:8000
```

**方式二：命令行**

```bash
# 创建游戏
python run.py create "贪吃蛇游戏，复古像素风，有排行榜"

# 创建 3D 游戏
python run.py create "第一人称迷宫探索" --engine threejs3d

# 迭代修改
python run.py iterate <project_id> "加快蛇的移动速度"

# 列出项目
python run.py list
```

## 📁 项目结构

```
game-AI-platform/
├── run.py                    # 启动入口
├── requirements.txt          # Python 依赖
├── config/
│   ├── .env                  # 环境变量（API Key 等）
│   └── .env.example          # 配置模板
├── src/
│   ├── config.py             # 配置加载
│   ├── models.py             # 数据模型（Pydantic）
│   ├── logger.py             # 日志
│   ├── cli.py                # CLI 命令
│   ├── llm/
│   │   ├── client.py         # LLM 客户端（OpenAI / Anthropic 双 SDK）
│   │   └── prompts.py        # 提示词模板
│   ├── pipeline/
│   │   ├── orchestrator.py   # 流水线编排
│   │   ├── analyzer.py       # 分析用户需求
│   │   ├── planner.py        # 规划文件结构
│   │   ├── code_gen.py       # 代码生成
│   │   ├── assembler.py      # 项目组装
│   │   ├── builder.py        # 构建 & 测试
│   │   └── fixer.py          # 自动修复
│   ├── server/
│   │   ├── app.py            # FastAPI 应用
│   │   ├── store.py          # 项目存储
│   │   └── preview.py        # 预览服务器管理
│   ├── static/
│   │   └── index.html        # Web 前端
│   └── templates/
│       └── web_game/
│           ├── phaser2d/     # Phaser 2D 模板
│           └── threejs3d/    # Three.js 3D 模板
└── data/
    └── projects/             # 生成的游戏项目
```

## 🎮 模板架构

每个游戏模板遵循严格的架构约束，确保 AI 生成的代码质量：

| 规则 | 说明 |
|------|------|
| EventBus | 所有模块间通信通过事件总线 |
| GameState | 所有共享状态集中管理 |
| Constants | 所有数字常量统一定义，禁止魔法数字 |
| 场景隔离 | 场景不能直接导入其他场景 |
| 实体独立 | 实体不能导入场景 |

## 🔧 配置项

在 `config/.env` 中可配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MODEL_ID` | LLM 模型 ID | claude-sonnet-4-6 |
| `LLM_MAX_TOKENS` | 默认最大 token | 8192 |
| `LLM_CODE_MAX_TOKENS` | 代码生成最大 token | 8192 |
| `LLM_PLAN_MAX_TOKENS` | 规划阶段最大 token | 4096 |
| `LLM_PARALLEL_FILES` | 并行文件生成数 | 3 |
| `LLM_TEMPERATURE` | 采样温度 | 0.2 |
| `LOG_LEVEL` | 日志级别 | INFO |

## 📡 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/games` | 创建新游戏 |
| GET | `/api/v1/games` | 列出所有项目 |
| GET | `/api/v1/games/{id}` | 获取项目详情 |
| POST | `/api/v1/games/{id}/iterate` | 迭代修改 |
| POST | `/api/v1/games/{id}/preview` | 启动预览 |
| DELETE | `/api/v1/games/{id}/preview` | 停止预览 |
| DELETE | `/api/v1/games/{id}` | 删除项目 |
| GET | `/api/v1/games/{id}/events` | SSE 实时状态 |

## 🎯 示例

```bash
# 经典 2D 游戏
python run.py create "贪吃蛇，复古绿色像素风，有计分和排行榜"
python run.py create "太空射击游戏，有3种敌人和Boss战"
python run.py create "打砖块，有随机道具掉落"
python run.py create "Flappy Bird 克隆"

# 3D 游戏
python run.py create "第一人称迷宫探索，有宝箱收集" --engine threejs3d
python run.py create "3D 赛车游戏" --engine threejs3d
```
