# CPublic Sentiment — 企业舆情风险预警 Multi-Agent 系统（LangGraph 编排）

[![CI](https://github.com/Crzblinder/cpublic-sentiment/actions/workflows/ci.yml/badge.svg)](https://github.com/Crzblinder/cpublic-sentiment/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 从"舆情被动响应"重构为"主动风险预警"的开源智能体项目，基于 LangGraph 有状态图编排。

CPublic Sentiment 面向企业风控场景，构建 **LangGraph Multi-Agent 协同架构**：舆情扫描 → 条件路由分流 → 案例匹配 → 风险预测 → 治理方案生成，极高危事件自动触发专家审核节点。系统采用 LangGraph StateGraph 实现有状态工作流，支持条件路由（低置信度快速通道 / 高危专家审核 / 常规全链路）、SSE 实时流式推送每个 Agent 执行进度到前端。内置 520+ 历史风险案例、220+ 企业画像，采用 MySQL + Chroma 向量库的混合检索方案，支持 14 组 Prompt 模板的 A/B 测试与 CoT/Few-Shot 行为链迭代。

---

## 核心能力

| 模块 | 说明 |
|------|------|
| 舆情扫描 Agent | 识别企业实体、行业、风险类型、情绪倾向与置信度 |
| 案例匹配 Agent | 基于向量检索 + SQL 过滤的混合 RAG，匹配历史相似案例 |
| 风险预测 Agent | 结合企业画像与历史案例，输出风险等级、评分与时间窗口 |
| 治理方案 Agent | 生成即时/短期/长期行动、发言人话术与监测计划 |
| 专家审核 Agent | 极高危事件综合评估：审核意见、是否升级处理、建议时间线 |
| 智能路由 | 条件分流：低置信度快速通道 / 高危专家审核 / 常规全链路 |
| SSE 流式输出 | 每个 Agent 执行进度通过 Server-Sent Events 实时推送到前端 |
| 效果评估 | 准确率 / 召回率 / 响应时间三位一体指标，支持 A/B Prompt 测试（默认走 LangGraph 工作流） |

---

## 技术栈

- **后端**：Python 3.11、FastAPI、SQLAlchemy、Pydantic
- **智能体**：LangGraph + LangChain — 有状态图编排、条件路由分流、SSE 流式输出，支持 OpenAI-compatible LLM + 本地 Ollama 双模式 + 确定性降级
- **RAG**：ChromaDB + `BAAI/bge-small-zh-v1.5` 中文 Embedding
- **数据库**：MySQL 8（默认 Docker）/ SQLite（本地快速启动）
- **前端**：React 18 + TypeScript + Vite + Recharts（图表可视化）
- **部署**：Docker Compose 一键启动（云端 API / 本地 Ollama 双轨制）
- **测试**：pytest + Playwright

---

## 快速开始

> 系统支持两种大模型运行模式，请根据你的环境选择：

### 路线 A：云端 API 模式（有 API Key）

适用场景：有 OpenAI 或兼容 API Key，追求最高推理质量。

```bash
# 1. 复制环境变量并填入 API Key
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY（留空则自动使用确定性降级，仍可运行）

# 2. 一键启动
docker compose up --build -d

# 3. 初始化数据（首次运行）
docker exec sentiment_backend python scripts/init_db.py
docker exec sentiment_backend python scripts/seed_data.py

# 4. 访问
# 前端：http://localhost:5173
# API 文档：http://localhost:8000/docs
```

### 路线 B：本地 Ollama 模式（零成本免密）

适用场景：无 API Key、内网环境、希望完全本地化运行。

```bash
# 1. 复制环境变量并开启本地模式
cp .env.example .env
# 编辑 .env，取消注释 USE_LOCAL_LLM=true

# 2. 一键启动（含 Ollama 服务 + 自动拉取中文模型 qwen2.5:7b）
make docker-up-ollama
# 或直接执行：
# docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build -d

# 3. 等待 Ollama 拉取模型完成（首次约 4-5 GB），访问同上
```

> 推荐模型：`qwen2.5:7b`（中文能力强，7B 参数量适合消费级 GPU）。如需更换模型，修改 `docker-compose.ollama.yml` 中的 `OLLAMA_MODEL` 环境变量。

### 本地开发（不使用 Docker）

```bash
# 后端
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_data.py
uvicorn app.main:app --reload --port 8000

# 前端（新终端）
cd frontend
npm install
npm run dev
```

或使用快捷脚本：

```bash
# Linux / macOS
bash scripts/start_local.sh

# Windows PowerShell
.\scripts\start_local.ps1
```

---

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── agents/          # 5 agents + LangGraph 工作流
│   │   │   ├── base.py          # BaseAgent 基类
│   │   │   ├── scanner.py       # 舆情扫描 Agent
│   │   │   ├── matcher.py       # 案例匹配 Agent
│   │   │   ├── predictor.py     # 风险预测 Agent
│   │   │   ├── governance.py    # 治理方案 Agent
│   │   │   ├── expert.py        # 专家审核 Agent（极高危事件）
│   │   │   ├── graph_state.py   # SentimentState 工作流状态定义
│   │   │   ├── graph_nodes.py   # 10 个图节点函数 + 条件路由
│   │   │   ├── workflow.py      # LangGraph StateGraph 构建与编译
│   │   │   └── orchestrator.py  # 旧版线性流水线（fallback）
│   │   ├── api/             # REST API（含 SSE 流式端点）
│   │   ├── data/            # 220 企业 / 520 案例生成器
│   │   ├── llm/             # LangChain LLM 工厂（OpenAI / Ollama 双模式）
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── prompts/         # 外置提示词模板（.txt，可直接编辑定制）
│   │   ├── rag/             # Embedding / Chroma / 混合检索
│   │   └── services/        # 业务逻辑（LangGraph 适配）
│   ├── scripts/             # init_db / seed_data / export_graph（Mermaid 导出）
│   └── tests/               # pytest 测试
├── frontend/                # React + Vite 仪表盘 + Recharts 图表 + SSE 流式
├── e2e/                     # Playwright 端到端冒烟测试
├── docker-compose.yml       # MySQL + Backend + Frontend（云端 API 模式）
├── docker-compose.ollama.yml # Ollama 叠加编排（本地免密模式）
├── Makefile                 # 常用命令
└── .github/workflows/ci.yml # GitHub Actions CI
```

---

## LangGraph 智能体工作流

系统基于 LangGraph `StateGraph` 构建有状态图，通过 `add_conditional_edges` 实现条件路由分流：

```
                    ┌──────────┐
                    │ Scanner  │  ← 舆情扫描 Agent
                    └────┬─────┘
                         │
                  ┌──────▼──────┐
                  │ route_scan  │  ← 条件路由
                  └──┬───┬───┬──┘
                     │   │   │
     ┌───────────────┘   │   └──────────────┐
     │  低置信度+非核心    │    高危关键词       │
     │  (confidence<0.3)  │   (暴雷/监管/...)   │
     │                   │                   │
     ▼                   ▼                   ▼
┌──────────┐    ┌───────────┐       ┌──────────────┐
│fast_exit │    │  RAG 检索  │       │ 专家审核      │
│ 快速通道  │    │ + Matcher │       │ ExpertReview │
│ 轻量治理  │    │ + Predict │       │ 综合评估      │
└────┬─────┘    │ + Govern  │       └──────┬───────┘
     │          └─────┬─────┘              │
     │                │             ┌──────▼───────┐
     │                │             │ Governance   │
     │                │             │ (紧急模式)    │
     │                │             └──────┬───────┘
     │                │                    │
     ▼                ▼                    ▼
   ┌─────────────────────────────────────────┐
   │              finalize                   │
   │   汇总输出 + 推理链 + 持久化事件         │
   └─────────────────────────────────────────┘
```

**三条执行路径**：

| 路径 | 触发条件 | 流程 |
|------|----------|------|
| 常规（normal） | 默认路径 | Scanner → RAG → Matcher → Predictor → Governance → 输出 |
| 快速通道（fast_exit） | 置信度 < 0.3 且风险类型为"其他" | Scanner → 轻量治理方案 → 输出 |
| 专家审核（expert_review） | 文本包含高危关键词（暴雷/监管/重大/死亡等） | Scanner → ExpertReview → 紧急 Governance → 输出 |

> **向后兼容**：旧版 `AgentOrchestrator` 线性流水线保留为 fallback，设置 `USE_LANGGRAPH=false` 即可无缝切换。

---

## 数据与 RAG

- **520+ 风险案例**：覆盖 9 大风险类型、10 个行业，每条案例附带治理预案。
- **220+ 企业画像**：包含行业、规模、地区、业务标签、风险画像。
- **混合检索**：
  1. SQL 先按行业/风险类型过滤，限定候选集在 200 条以内；
  2. Chroma 向量库对候选集做语义相似度重排；
  3. 平均检索延迟控制在 200ms 以内。

---

## 效果评估与 A/B 测试

系统内置 14 组 Prompt 变体（A/B 测试默认走 LangGraph 工作流）：

- Scanner：Zero-Shot / CoT / Few-Shot
- Matcher：Zero-Shot / CoT / Few-Shot
- Predictor：Zero-Shot / CoT / Few-Shot
- Governance：Zero-Shot / CoT / Few-Shot / RolePlay
- Expert：Zero-Shot

通过 API 触发 A/B 测试：

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/ab-test \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "scanner",
    "dataset": [
      {"text": "...", "true_risk_level": "高", "true_risk_type": "食品安全"}
    ]
  }'
```

返回指标：

- `accuracy_level`：风险等级准确率
- `accuracy_type`：风险类型准确率
- `recall_relevant`：相关舆情召回率
- `avg_latency_ms`：平均响应时间

---

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/sentiment/analyze` | 分析舆情 |
| POST | `/api/v1/sentiment/analyze/stream` | SSE 流式分析（实时推送每个 Agent 进度） |
| GET  | `/api/v1/sentiment/events` | 舆情事件列表 |
| GET  | `/api/v1/sentiment/events/{id}` | 事件详情 |
| POST | `/api/v1/sentiment/label` | 人工标注 |
| GET  | `/api/v1/cases` | 案例库（分页：`{total, items}`） |
| GET  | `/api/v1/enterprises` | 企业画像（分页：`{total, items}`） |
| POST | `/api/v1/evaluation/ab-test` | A/B 测试 |
| GET  | `/api/v1/evaluation/metrics` | 整体指标 |

完整文档见：`http://localhost:8000/docs`

---

## 配置

复制 `.env.example` 为 `.env`，根据所选运行模式配置对应区块：

```env
# 通用参数（两种模式均需配置）
DATABASE_URL=mysql+pymysql://sentiment:sentiment@mysql:3306/sentiment?charset=utf8mb4
VECTOR_DB_PATH=./chroma_data

# LangGraph 工作流（默认启用，设为 false 可回退旧版线性流水线）
USE_LANGGRAPH=true

# 路线 A：云端 API 模式
USE_LOCAL_LLM=false          # 默认值，可省略
OPENAI_API_KEY=sk-xxx        # 留空则使用确定性降级
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 路线 B：本地 Ollama 模式
USE_LOCAL_LLM=true           # 开启本地模式
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

> 未配置任何 LLM 时，系统仍可通过内置规则引擎正常运行（确定性降级），方便本地体验与 CI。

---

## 提示词定制

所有 Agent 的系统提示词已完全外置为独立文本文件，存放在 `backend/app/prompts/` 目录：

```
backend/app/prompts/
├── scanner/      # 舆情扫描 Agent
│   ├── zero_shot.txt
│   ├── cot.txt
│   └── few_shot.txt
├── matcher/      # 案例匹配 Agent
├── predictor/    # 风险预测 Agent
├── governance/   # 治理方案 Agent
└── expert/       # 专家审核 Agent（极高危事件综合评估）
    └── zero_shot.txt
```

如需调整某个 Agent 的推理逻辑或输出格式，**直接编辑对应的 `.txt` 文件即可**，无需修改任何 Python 源码。修改后重启后端服务即可生效。

---

## 测试

```bash
# 后端单元测试
cd backend
pytest -q

# 导出 LangGraph 工作流 Mermaid 图
cd backend
py scripts/export_graph.py
# 输出 Mermaid 源码到 backend/docs/workflow.mmd

# 前端构建
cd frontend
npm run build

# 端到端冒烟测试（首次运行会下载 Playwright Chromium，见 .playwright-browsers）
cd e2e
python test_analyze_flow.py
```

> 提示：`seed_data.py` 首次执行时会从 Hugging Face 下载 Embedding 模型到本地缓存（`backend/models_cache/`），属于一次性初始化。若只想快速验证页面连通性，可使用 `e2e/seed_minimal.py` 插入少量样本数据。
>
> **中国大陆网络**：若 Hugging Face 下载缓慢或 SSL 报错，可在 `.env` 中设置镜像源后重新运行：
> ```env
> HF_ENDPOINT=https://hf-mirror.com
> ```

---

## LangGraph 工作流可视化

项目提供 `scripts/export_graph.py` 脚本，可一键导出当前工作流的 Mermaid 图和 ASCII 图：

```bash
cd backend
py scripts/export_graph.py
```

输出内容：
- **Mermaid 源码**：可粘贴到 [Mermaid Live Editor](https://mermaid.live) 在线渲染，或直接嵌入 Markdown 文档
- **ASCII 图**：终端直接预览工作流拓扑
- **自动保存**：`backend/docs/workflow.mmd`

> 前端分析页面（Analyze.tsx）在分析进行中时，会通过 SSE 流式接收每个 Agent 的执行进度，实时高亮工作流中正在执行的节点路径。

---

## 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/xxx`
3. 提交变更：`git commit -m "feat: xxx"`
4. 推送分支：`git push origin feature/xxx`
5. 创建 Pull Request

---

## 许可证

[MIT](LICENSE)

---

## 致谢

- Embedding 模型：[BAAI/bge-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5)
- 前端脚手架：[Vite](https://vitejs.dev/)
- UI 组件：原生 CSS，避免 AI 同质化风格
