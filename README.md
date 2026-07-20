# TalentMatch Engine — 岗位技能图谱与人才匹配引擎

[![CI](https://github.com/Crzblinder/talentmatch-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/Crzblinder/talentmatch-engine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 面向 2026 届及以后求职者的智能化求职助手：从“海投简历”到“精准匹配”，让每一次投递都有据可依。

TalentMatch Engine 是一个基于 **LangGraph Multi-Agent 编排**的岗位技能图谱与人才匹配引擎。它针对当前毕业生和职场新人面临的真实痛点——网申系统重复填写、简历被 AI 初筛过滤、海投低效、岗位需求与个人技能难以对齐——提供了一套可解释、可量化的匹配方案。

系统通过 5 个核心 Agent 协同工作：

1. **JD 解析 Agent**：将岗位描述自动解析为结构化技能、经验、学历要求；
2. **人才匹配 Agent**：基于技能覆盖度、缺失技能与可迁移技能计算匹配分数；
3. **趋势预测 Agent**：聚合岗位数据，输出热门技能、主流薪资与岗位趋势；
4. **学习路径规划 Agent**：根据缺失技能与技能图谱依赖关系生成学习路径；
5. **技能顾问 Agent**：给出简历优化、技能补强与求职策略建议。

LangGraph 工作流将上述 Agent 串联为 `parse → match → predict → plan → advise` 的有状态图，并通过 SSE 实时推送每个节点的执行进度到前端。系统在无 LLM Key 时自动降级为规则引擎，确保本地体验与 CI 环境可直接运行。

---

## 核心能力

| 模块 | 说明 |
|------|------|
| JD 解析 Agent | 从原始 JD 中提取岗位名称、公司、核心技能、经验、学历与隐含需求 |
| 人才匹配 Agent | 计算匹配分数、匹配技能、缺失技能与可迁移技能 |
| 趋势预测 Agent | 基于岗位聚合数据输出热门技能、主流薪资、热门岗位 |
| 学习路径规划 Agent | 基于技能图谱依赖/相似关系生成可执行的学习路径 |
| 技能顾问 Agent | 输出简历优化、技能补强与求职策略建议 |
| 技能知识图谱 | 技能之间的依赖、相似、共现关系，支撑可迁移技能与学习路径 |
| SSE 流式输出 | LangGraph 每个节点完成时通过 Server-Sent Events 实时推送 |
| 混合检索 | 支持基于关键词与向量的岗位检索（可选） |

---

## 真实痛点与解决方案

| 痛点 | 解决方案 |
|------|----------|
| 2026 届毕业生求职竞争激烈，简历难以脱颖而出 | 简历优化建议 + 岗位关键词对齐 |
| 网申系统重复填写，海投效率低 | 统一的技能画像，一次填写多次匹配 |
| 企业使用 AI 初筛简历，关键词不匹配即被过滤 | JD 解析 + 匹配结果直观展示岗位需求与个人技能差距 |
| 不知道岗位需要哪些技能，学习方向模糊 | 学习路径规划基于技能图谱生成 |
| 投递后无反馈，难以评估自身竞争力 | 量化匹配分数与可迁移技能，明确提升方向 |

---

## 技术栈

- **后端**：Python 3.11、FastAPI、SQLAlchemy、Pydantic
- **智能体**：LangGraph + LangChain — 有状态图编排、SSE 流式输出，支持 OpenAI-compatible LLM + 本地 Ollama 双模式 + 确定性降级
- **RAG**：ChromaDB + `BAAI/bge-small-zh-v1.5` 中文 Embedding（可选）
- **数据库**：MySQL 8（默认 Docker）/ SQLite（本地快速启动）
- **前端**：React 18 + TypeScript + Vite + Recharts（图表可视化）
- **部署**：Docker Compose 一键启动（云端 API / 本地 Ollama 双轨制）
- **测试**：pytest + Playwright

---

## 快速开始

> 系统支持两种大模型运行模式，请根据你的环境选择：

### 路线 A：云端 API 模式（有 API Key）

适用场景：有 OpenAI 或兼容 API Key，追求更高推理质量。

```bash
# 1. 复制环境变量并填入 API Key
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY（留空则自动使用确定性降级，仍可运行）

# 2. 一键启动
docker compose up --build -d

# 3. 初始化数据（首次运行）
docker exec talentmatch_backend python scripts/init_db.py
docker exec talentmatch_backend python scripts/seed_data.py

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
│   │   ├── agents/          # 5 个新版 Agent + LangGraph 工作流
│   │   │   ├── base.py          # BaseAgent 基类
│   │   │   ├── jd_parser.py     # JD 解析 Agent
│   │   │   ├── talent_matcher.py# 人才匹配 Agent
│   │   │   ├── trend_predictor.py # 趋势预测 Agent
│   │   │   ├── learning_planner.py # 学习路径规划 Agent
│   │   │   ├── skill_advisor.py # 技能顾问 Agent
│   │   │   ├── graph_state.py   # JobMatchState 工作流状态定义
│   │   │   ├── graph_nodes.py   # 5 个图节点函数
│   │   │   ├── workflow.py      # LangGraph StateGraph 构建与编译
│   │   │   └── orchestrator.py  # 工作流编排器封装
│   │   ├── api/             # REST API（含 SSE 流式端点）
│   │   ├── data/            # 样例岗位 / 企业 / 技能生成器
│   │   ├── graph/           # 技能图谱构建与查询
│   │   ├── llm/             # LangChain LLM 工厂（OpenAI / Ollama 双模式）
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── prompts/         # 外置提示词模板（.txt，可直接编辑定制）
│   │   ├── rag/             # Embedding / Chroma / 混合检索
│   │   └── services/        # 业务逻辑服务
│   ├── scripts/             # init_db / seed_data / export_graph / with_server
│   └── tests/               # pytest 单元与集成测试
├── frontend/                # React + Vite 仪表盘 + Recharts 图表 + SSE 流式
├── e2e/                     # Playwright 端到端冒烟测试
├── docker-compose.yml       # MySQL + Backend + Frontend（云端 API 模式）
├── docker-compose.ollama.yml # Ollama 叠加编排（本地免密模式）
├── Makefile                 # 常用命令
└── .github/workflows/ci.yml # GitHub Actions CI
```

---

## LangGraph 智能体工作流

系统基于 LangGraph `StateGraph` 构建有状态图，节点顺序执行：

```
┌──────────┐     ┌─────────────┐     ┌─────────────────┐
│  parse   │ --> │    match    │ --> │    predict      │
│ JD 解析   │     │  人才匹配    │     │   趋势预测       │
└──────────┘     └─────────────┘     └─────────────────┘
                                              |
                                              v
┌──────────┐     ┌─────────────┐
│  advise  │ <-- │    plan     │
│ 综合建议  │     │ 学习路径规划 │
└──────────┘     └─────────────┘
```

**执行流程**：

1. `parse`：解析 JD 文本，输出结构化岗位信息；
2. `match`：将用户画像与目标岗位匹配，输出匹配分数与技能差距；
3. `predict`：基于岗位库聚合数据输出市场趋势；
4. `plan`：根据缺失技能与技能图谱生成学习路径；
5. `advise`：综合以上结果给出简历优化与求职策略建议。

每个节点完成时生成 SSE 事件，前端可实时展示执行进度。

---

## 数据与技能图谱

- **岗位数据**：覆盖多个行业与城市，包含薪资、经验、学历、技能要求等字段；
- **技能知识图谱**：技能之间的依赖、相似、共现关系，用于：
  - 计算可迁移技能（例如会 MySQL 可迁移到 PostgreSQL）；
  - 生成有前置依赖的学习路径；
- **求职者画像**：存储个人技能、经验、目标岗位，用于多次匹配。

---

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/health` | 服务健康检查 |
| GET  | `/api/v1/jobs/health` | 业务健康检查 |
| GET  | `/api/v1/jobs` | 岗位列表（分页） |
| GET  | `/api/v1/jobs/{id}` | 岗位详情 |
| GET  | `/api/v1/jobs/search` | 岗位混合检索 |
| POST | `/api/v1/jobs/parse` | 解析 JD |
| GET  | `/api/v1/skills` | 技能列表 |
| GET  | `/api/v1/skills/{id}` | 技能详情 |
| GET  | `/api/v1/skills/{id}/related` | 关联技能 |
| GET  | `/api/v1/profiles` | 求职者画像列表 |
| POST | `/api/v1/profiles` | 创建求职者画像 |
| POST | `/api/v1/matches` | 执行人岗匹配 |
| GET  | `/api/v1/matches` | 匹配结果列表 |
| GET  | `/api/v1/matches/{id}` | 匹配结果详情 |
| POST | `/api/v1/matches/learning-path` | 生成学习路径 |
| POST | `/api/v1/matches/stream` | SSE 流式匹配分析 |
| GET  | `/api/v1/trends` | 岗位趋势分析 |
| GET  | `/api/v1/dashboard` | 仪表盘聚合数据 |

完整文档见：`http://localhost:8000/docs`

---

## 配置

复制 `.env.example` 为 `.env`，根据所选运行模式配置对应区块：

```env
# 通用参数（两种模式均需配置）
DATABASE_URL=mysql+pymysql://talentmatch:talentmatch@mysql:3306/talentmatch?charset=utf8mb4
VECTOR_DB_PATH=./chroma_data

# 前端
VITE_API_BASE_URL=http://localhost:8000

# 应用
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=change-me-in-production

# 路线 A：云端 API 模式
USE_LOCAL_LLM=false
OPENAI_API_KEY=sk-xxx        # 留空则使用确定性降级
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 路线 B：本地 Ollama 模式
USE_LOCAL_LLM=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

> 未配置任何 LLM 时，系统仍可通过内置规则引擎正常运行（确定性降级），方便本地体验与 CI。

---

## 提示词定制

所有 Agent 的系统提示词已外置为独立文本文件，存放在 `backend/app/prompts/` 目录：

```
backend/app/prompts/
├── jd_parser/      # JD 解析 Agent
├── talent_matcher/ # 人才匹配 Agent
├── trend_predictor/# 趋势预测 Agent
├── learning_planner/ # 学习路径规划 Agent
└── skill_advisor/  # 技能顾问 Agent
```

如需调整某个 Agent 的推理逻辑或输出格式，**直接编辑对应的 `.txt` 文件即可**，无需修改 Python 源码。修改后重启后端服务即可生效。

---

## 测试

```bash
# 后端单元测试
cd backend
pytest -q

# 导出 LangGraph 工作流 Mermaid 图
cd backend
python scripts/export_graph.py
# 输出 Mermaid 源码到 backend/docs/workflow.mmd

# 前端构建
cd frontend
npm run build

# 端到端冒烟测试（首次运行会下载 Playwright Chromium，见 .playwright-browsers）
cd /workspace
python e2e/test_job_match_flow.py
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
python scripts/export_graph.py
```

输出内容：
- **Mermaid 源码**：可粘贴到 [Mermaid Live Editor](https://mermaid.live) 在线渲染，或直接嵌入 Markdown 文档
- **ASCII 图**：终端直接预览工作流拓扑
- **自动保存**：`backend/docs/workflow.mmd`

> 前端岗位匹配页面在流式分析进行中时，会通过 SSE 实时接收每个 Agent 的执行进度，并展示当前执行节点。

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
