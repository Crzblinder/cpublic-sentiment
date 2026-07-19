# CPublic Sentiment — 企业舆情风险预警 Multi-Agent 系统

[![CI](https://github.com/Crzblinder/cpublic-sentiment/actions/workflows/ci.yml/badge.svg)](https://github.com/Crzblinder/cpublic-sentiment/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 从"舆情被动响应"重构为"主动风险预警"的开源智能体项目。

CPublic Sentiment 面向企业风控场景，构建 **Multi-Agent 协同架构**：舆情扫描 → 案例匹配 → 风险预测 → 治理方案生成。系统内置 520+ 历史风险案例、220+ 企业画像，采用 MySQL + Chroma 向量库的混合检索方案，支持 13 组 Prompt 模板的 A/B 测试与 CoT/Few-Shot 行为链迭代。

---

## 核心能力

| 模块 | 说明 |
|------|------|
| 舆情扫描 Agent | 识别企业实体、行业、风险类型、情绪倾向与置信度 |
| 案例匹配 Agent | 基于向量检索 + SQL 过滤的混合 RAG，匹配历史相似案例 |
| 风险预测 Agent | 结合企业画像与历史案例，输出风险等级、评分与时间窗口 |
| 治理方案 Agent | 生成即时/短期/长期行动、发言人话术与监测计划 |
| 效果评估 | 准确率 / 召回率 / 响应时间三位一体指标，支持 A/B Prompt 测试 |

---

## 技术栈

- **后端**：Python 3.11、FastAPI、SQLAlchemy、Pydantic
- **智能体**：LangChain 统一调用层，支持 OpenAI-compatible LLM + 本地 Ollama 双模式 + 确定性降级
- **RAG**：ChromaDB + `BAAI/bge-small-zh-v1.5` 中文 Embedding
- **数据库**：MySQL 8（默认 Docker）/ SQLite（本地快速启动）
- **前端**：React 18 + TypeScript + Vite
- **部署**：Docker Compose 一键启动（云端 API / 本地 Ollama 双轨制）
- **测试**：pytest + Playwright

---

## 快速开始

> 系统支持两种大模型运行模式，请根据你的环境选择：

### 路线 A：云端 API 模式（有 API Key）

适用场景：有 OpenAI 或兼容 API Key，追求最高推理质量。

```bash
# 1. 复制环境变量并填入 API Key
cp .env .env
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
cp .env .env
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
│   │   ├── agents/          # 四 agents + orchestrator
│   │   ├── api/             # REST API
│   │   ├── data/            # 220 企业 / 520 案例生成器
│   │   ├── llm/             # LangChain LLM 工厂（OpenAI / Ollama 双模式）
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── prompts/         # 外置提示词模板（.txt，可直接编辑定制）
│   │   ├── rag/             # Embedding / Chroma / 混合检索
│   │   └── services/        # 业务逻辑
│   ├── scripts/             # init_db / seed_data
│   └── tests/               # pytest 测试
├── frontend/                # React + Vite 仪表盘
├── e2e/                     # Playwright 端到端冒烟测试
├── docker-compose.yml       # MySQL + Backend + Frontend（云端 API 模式）
├── docker-compose.ollama.yml # Ollama 叠加编排（本地免密模式）
├── Makefile                 # 常用命令
└── .github/workflows/ci.yml # GitHub Actions CI
```

---

## Multi-Agent 架构

```
输入舆情文本
    │
    ▼
┌─────────────────┐
│  舆情扫描 Agent  │  ← Zero-Shot / CoT / Few-Shot Prompt
│  SentimentScanner│
└────────┬────────┘
         │ 行业 / 风险类型 / 实体
         ▼
┌─────────────────┐
│   混合检索 RAG   │  ← MySQL 过滤 + Chroma 向量排序
│  HybridRetriever │
└────────┬────────┘
         │ 候选案例 + 企业画像
         ▼
┌─────────────────┐
│  案例匹配 Agent  │
│   CaseMatcher    │
└────────┬────────┘
         │ 匹配案例 IDs
         ▼
┌─────────────────┐
│  风险预测 Agent  │
│  RiskPredictor   │
└────────┬────────┘
         │ 风险等级 / 评分 / 时间窗口
         ▼
┌─────────────────┐
│ 治理方案 Agent   │
│   GovernanceAgent│
└─────────────────┘
         │
         ▼
    结构化治理方案 + 推理链
```

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

系统内置 13 组 Prompt 变体：

- Scanner：Zero-Shot / CoT / Few-Shot
- Matcher：Zero-Shot / CoT / Few-Shot
- Predictor：Zero-Shot / CoT / Few-Shot
- Governance：Zero-Shot / CoT / Few-Shot / RolePlay

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
| GET  | `/api/v1/sentiment/events` | 舆情事件列表 |
| GET  | `/api/v1/sentiment/events/{id}` | 事件详情 |
| POST | `/api/v1/sentiment/label` | 人工标注 |
| GET  | `/api/v1/cases` | 案例库 |
| GET  | `/api/v1/enterprises` | 企业画像 |
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
└── governance/   # 治理方案 Agent
```

如需调整某个 Agent 的推理逻辑或输出格式，**直接编辑对应的 `.txt` 文件即可**，无需修改任何 Python 源码。修改后重启后端服务即可生效。

---

## 测试

```bash
# 后端单元测试
cd backend
pytest -q

# 前端构建
cd frontend
npm run build

# 端到端冒烟测试（首次运行会下载 Playwright Chromium，见 .playwright-browsers）
cd e2e
python test_analyze_flow.py
```

> 提示：`seed_data.py` 首次执行时会从 Hugging Face / Chroma CDN 下载 Embedding 模型到本地缓存，属于一次性初始化。若只想快速验证页面连通性，可使用 `e2e/seed_minimal.py` 插入少量样本数据。

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
