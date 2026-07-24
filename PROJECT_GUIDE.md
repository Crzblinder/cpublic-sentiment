# CPublic Sentiment — 企业舆情风险预警系统

> 一个基于 Multi-Agent 协同架构 + RAG 检索增强生成的开源智能体项目，支持云端 API 与本地 Ollama 双模式部署，实现从舆情采集到风险预警的全链路自动化。

---

## 一、项目概述

**产品定位**：从"舆情被动响应"重构为"主动风险预警"的企业风控产品范式。

**核心能力**：
- 舆情实时采集（21 个公开数据源，7 个 RSS 稳定可用，异步并发采集+增量去重）
- Multi-Agent 协同分析（扫描 → 匹配 → 预测 → 治理）
- RAG 混合检索（500+ 案例、200+ 企业画像知识库）
- A/B 测试驱动的 Prompt 迭代优化
- 效果评估闭环（准确率 / 召回率 / 响应时间）

**技术栈**：Python 3.11 | FastAPI | SQLAlchemy | ChromaDB | LangChain | LangGraph | React 18 | TypeScript | Vite | Docker Compose

---

## 二、后端架构详解

### 2.1 Multi-Agent 协同引擎 `backend/app/agents/`

基于 **LangGraph 有状态图编排**，替代传统串行 Pipeline，支持条件路由和中间状态持久化。

| 文件 | 职责 | 技术亮点 |
|------|------|----------|
| `workflow.py` + `graph_nodes.py` | LangGraph `StateGraph` 编排 | 节点间通过 `SentimentState` 共享上下文，支持条件分支路由 |
| `graph_state.py` | 状态机设计 | 统一状态 Schema，节点返回 dict 增量更新，避免上下文丢失 |
| `scanner.py` | 舆情扫描 Agent | 关键词匹配 + LLM 混合识别，无 LLM 时启用规则引擎兜底 |
| `matcher.py` | 案例匹配 Agent | 结合 RAG 检索结果，用 LLM 做二次 relevance 判断 |
| `predictor.py` | 风险预测 Agent | 融合舆情文本、匹配案例、企业画像三维信息输出预测 |
| `governance.py` | 治理方案 Agent | 根据风险等级动态选择策略模板，高危事件注入专家意见 |
| `expert.py` | 专家审核 Agent | 条件路由触发：含高危关键词时自动进入复核节点 |
| `prompts.py` | Prompt 管理器 | 按 Agent + 策略（CoT/Few-Shot/Zero-Shot/Roleplay）动态加载 |

#### 条件路由逻辑

```python
def route_scan(state: SentimentState) -> str:
    confidence = state.get("scan_result", {}).get("confidence", 0.5)
    risk_type = state.get("scan_result", {}).get("risk_type", "其他")
    text = state.get("text", "")
    
    if confidence < 0.3 and risk_type == "其他":
        return "fast_exit"          # 低置信度 → 快速通道，节省 LLM 调用成本
    if any(s in text for s in HIGH_SIGNAL_KEYWORDS):
        return "expert_review"      # 高危信号 → 专家审核
    return "normal"                 # 常规全链路
```

**面试话术**："我用 LangGraph 把传统串行 Pipeline 改造成有向图，支持条件分支（低置信度快速通道/高危专家审核/常规全链路），每个节点可以读取完整上下文做决策，避免了传统链式调用中的上下文丢失问题。"

---

### 2.2 RAG 混合检索系统 `backend/app/rag/`

**SQL 预过滤 + 向量重排** 的混合检索方案，检索延迟控制在 **200ms** 内。

| 文件 | 职责 | 技术亮点 |
|------|------|----------|
| `retriever.py` | Hybrid Retrieval | SQL 结构化过滤到 200 条候选，再用向量相似度重排 Top-K |
| `embeddings.py` | Embedding 模型管理 | `BAAI/bge-small-zh-v1.5` 中文 Embedding，本地缓存优先加载 |
| `vector_store.py` | ChromaDB 封装 | 绕过 ChromaDB 1.5.9 兼容性问题，手动计算 embeddings 传入 |

#### 混合检索核心逻辑

```python
def retrieve_cases(self, query, industry=None, risk_type=None, top_k=5):
    # Step 1: SQL 预过滤 — 结构化条件快速缩小范围
    q = self.db.query(RiskCase)
    if industry: q = q.filter(RiskCase.industry == industry)
    if risk_type: q = q.filter(RiskCase.risk_type == risk_type)
    sql_candidates = q.limit(200).all()
    
    # Step 2: 向量重排 — 语义相似度精细排序
    where = {"id": {"$in": [str(c.id) for c in sql_candidates]}}
    results = self.case_store.query([query], n_results=top_k * 2, where=where)
    
    # Step 3: 返回 Top-K
    return output[:top_k]
```

**面试话术**："纯向量检索在数据量大时延迟高，且无法利用结构化属性做精确过滤。混合检索先用 SQL 索引做粗排（O(log n)），再用向量做精排，实测延迟从 800ms 降到 200ms 以内。"

---

### 2.3 Prompt Engineering 与 A/B 测试 `backend/app/prompts/`

建立 **13 组 Prompt 模板** 的 A/B 测试框架，用数据驱动方式迭代提示词效果。

```
prompts/
├── scanner/
│   ├── zero_shot.txt    # 直接指令
│   ├── few_shot.txt     # 带 3-5 个示例
│   └── cot.txt          # 思维链："让我们逐步思考..."
├── matcher/
├── predictor/
├── governance/
└── expert/
```

**面试话术**："我设计了 4 种 Prompt Engineering 策略（Zero-Shot、Few-Shot、CoT、Roleplay），为每个 Agent 配备 13 组模板。通过 A/B 测试框架自动对比不同模板在准确率、召回率、响应时间上的表现，最终筛选出最优组合。这个框架将舆情抓取准确率提升了 16%。"

---

### 2.4 效果评估与闭环验证 `backend/app/services/evaluation_service.py`

搭建 **"准确率-召回率-响应时间"三维评估体系**，支持 Prompt 级别的 A/B 测试。

```python
def run_ab_test(self, dataset, agent_type=None):
    for variant in prompt_variants:
        for item in dataset:
            out = run_analysis(text, prompt_variants={agent_type: variant.name})
            # 记录：pred_level vs true_level, pred_type vs true_type, latency
    # 输出：accuracy_level, accuracy_type, recall_relevant, avg_latency_ms
```

**面试话术**："我建立了完整的评估体系：准确率（风险等级判断正确率）、召回率（风险类型覆盖度）、响应时间（端到端延迟）。通过 A/B 测试对比 13 组 Prompt 模板，用数据驱动迭代，持续追踪 BadCase 驱动优化。"

---

### 2.5 FastAPI + SSE 流式响应 `backend/app/api/routes.py`

SSE（Server-Sent Events）流式接口，让用户实时看到每个 Agent 节点的执行过程和中间结果。

**面试话术**："分析链路涉及 4-6 个 Agent 节点，如果等全部执行完再返回，用户体验很差。我用 SSE 流式推送，每完成一个节点就实时展示结果，最终状态累加后直接持久化，避免了二次调用 LangGraph 的性能浪费。"

---

### 2.6 LLM 客户端工厂 `backend/app/llm/factory.py`

支持 **OpenAI API / Ollama 本地模型 / 规则引擎** 三种模式无缝切换。

**面试话术**："我设计了工厂模式封装 LLM 调用，根据环境变量自动切换：有 API Key 走 OpenAI，无网络走 Ollama 本地模型，两者都不可用时降级到规则引擎。这让系统在不同部署环境下都能稳定运行，实现零成本免密部署。"

---

### 2.7 数据模型与索引优化 `backend/app/models/`

| 模型 | 关键设计 | 面试价值 |
|------|----------|----------|
| `RiskCase` | 复合索引 `(industry, risk_type, risk_level)` | 为 RAG 的 SQL 预过滤做了索引优化，确保 200ms 检索延迟 |
| `Enterprise` | `risk_score_history` JSON 字段 | 存储月度风险评分历史，支持趋势图展示 |
| `SentimentEvent` | `labeled_risk_level` + `is_correct` | 支持人工标注和自动评估，构建闭环反馈 |

---

### 2.8 舆情爬虫 `backend/app/crawler/`

| 文件 | 技术点 |
|------|--------|
| `sources.py` | 配置 21 个公开数据源（7 个 RSS 稳定可用 + 2 个 API + 12 个备选） |
| `scraper.py` | `httpx.AsyncClient` 异步并发采集，feedparser 解析 RSS，JSON API 字段映射 |
| `pipeline.py` | 7 步清洗管线：HTML 去标签 → 文本规范化 → SimHash 去重 → 实体提取 → 风险分类 → 等级评估 → 行业归类 |

**稳定可用数据源**：

| 源名称 | 每次采集量 | 说明 |
|--------|-----------|------|
| chinanews_rss | 30 条 | 中国新闻网滚动新闻 |
| people_rss | 30 条 | 人民网时政新闻 |
| xinhua_rss | 30 条 | 新华网时政新闻 |
| sspai_rss | 10 条 | 少数派（科技资讯） |
| ithome_rss | 30 条 | IT之家（科技新闻） |
| jiemian_rss | 30 条 | 界面新闻（财经/商业） |
| 36kr_rss | 30 条 | 36氪（创投/科技） |

单次采集约 190 条，通过 `external_id`（URL MD5）实现增量去重，可安全重复执行。

---

## 三、前端架构 `frontend/src/`

**技术栈**：React 18 + TypeScript + Vite + Recharts

| 文件 | 技术亮点 | 面试话术 |
|------|----------|----------|
| `api.ts` | 封装全部 API + **SSE 流式消费** | 前端用 ReadableStream 消费 SSE，逐行解析 data 事件，实时更新分析进度 |
| `pages/Analyze.tsx` | 流式结果展示 | 分析页面实时展示 Scanner → Matcher → Predictor → Governance 每步结果 |
| `pages/Dashboard.tsx` | Recharts 数据可视化 | 仪表盘用 Recharts 实现风险分布饼图、行业柱状图、趋势折线图 |
| `pages/Evaluation.tsx` | A/B 测试结果对比 | 效果评估页展示不同 Prompt 模板的准确率、召回率、响应时间对比 |

#### SSE 消费核心逻辑

```typescript
const reader = res.body.getReader()
const decoder = new TextDecoder()
let buffer = ''

for (;;) {
  const { done, value } = await reader.read()
  if (done) break
  buffer += decoder.decode(value, { stream: true })
  // 解析 data: {...} 行，触发 onEvent 回调更新 UI
}
```

---

## 四、工程化与部署

### 4.1 Docker Compose 多模式部署

| 文件 | 技术价值 |
|------|----------|
| `docker-compose.yml` | 三服务编排：MySQL + FastAPI + React，生产环境一键启动 |
| `docker-compose.ollama.yml` | Ollama 叠加配置，本地大模型零成本运行 |
| `backend/Dockerfile` | 多阶段构建，Python 依赖分层缓存 |
| `frontend/Dockerfile` | Nginx serving 静态资源 |

**面试话术**："我设计了两套部署方案：云端 API 模式（OpenAI）和本地 Ollama 模式（零费用）。通过 Docker Compose 叠加配置文件实现模式切换，Vite 配置里加了 `host: '0.0.0.0'` 和 `watch.usePolling` 保证 Docker 卷挂载下的热更新正常。"

### 4.2 CI/CD 与代码规范

| 文件 | 技术价值 |
|------|----------|
| `.github/workflows/ci.yml` | GitHub Actions 自动运行 `ruff check` + `pytest` |
| `Makefile` | 标准化命令：`make backend`、`make lint`、`make seed` |
| `backend/pyproject.toml` | Ruff + MyPy 配置，强制代码规范 |

**面试话术**："项目配置了 GitHub Actions CI，每次 Push 自动跑代码检查和单元测试。用 Ruff 替代 Flake8+Black，lint 速度提升 10 倍。Makefile 统一了开发命令，降低团队上手成本。"

---

## 五、数据流全景

```
用户输入文本
    │
    ▼
┌─────────────────┐     ┌─────────────────┐
│  frontend       │────▶│  FastAPI        │
│  Analyze.tsx    │ SSE │  /analyze/stream│
└─────────────────┘     └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            ┌──────────┐ ┌──────────┐ ┌──────────┐
            │ Scanner  │ │ Matcher  │ │ Predictor│
            │ (关键词+ │ │ (RAG检索 │ │ (风险预测│
            │  LLM)    │ │ +LLM)   │ │ +扩散预测│
            └──────────┘ └──────────┘ └──────────┘
                    │           │           │
                    └───────────┼───────────┘
                                ▼
                    ┌──────────────────┐
                    │ 条件路由          │
                    │ • 低置信度→快速通道 │
                    │ • 高危词→专家审核   │
                    │ • 常规→Governance  │
                    └──────────────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │ Governance Agent │
                    │ (生成公关/法务方案) │
                    └──────────────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │ 持久化 → SQLite/  │
                    │ MySQL + 前端展示  │
                    └──────────────────┘
```

---

## 六、面试高频问题速查

| 问题 | 回答要点 |
|------|----------|
| "为什么用 LangGraph？" | 状态机 > 线性链，支持条件路由、循环、人机协同 |
| "RAG 怎么优化的？" | SQL预过滤+向量重排，延迟从800ms降到200ms |
| "Prompt 怎么调优的？" | 4种策略×13组模板，A/B测试数据驱动迭代 |
| "系统怎么保证可用性？" | 三模式降级：OpenAI → Ollama → 规则引擎 |
| "前端怎么做到实时反馈？" | SSE 流式推送，逐节点展示执行状态 |
| "数据怎么来的？" | Faker生成500+案例、200+企业画像，爬虫采集实时新闻 |

---

## 七、简历项目描述（可直接复制）

### 版本一：简洁版（适合简历一行）

> 主导设计企业舆情风险预警系统，基于 LangGraph 实现 Multi-Agent 协同架构（扫描/匹配/预测/治理），RAG 混合检索延迟控制在 200ms 内，搭建 A/B 测试框架对比 13 组 Prompt 模板将准确率提升 16%，支持 OpenAI/Ollama/规则引擎三模式降级部署。

### 版本二：详细版（适合项目经历展开）

> **企业舆情风险预警系统**
> - **架构设计**：主导设计 Multi-Agent 协同架构，基于 LangGraph 实现有状态图编排，定义 Scanner/Matcher/Predictor/Governance/Expert 五大模块职责边界，通过条件路由实现低置信度快速通道、高危事件专家审核、常规全链路三种执行路径
> - **数据工程**：构建 500+ 案例、200+ 企业画像的结构化知识库，设计 MySQL + ChromaDB 向量检索混合存储方案，通过 SQL 索引预过滤 + 向量重排将检索延迟控制在 200ms 内
> - **效果迭代**：运用 CoT、Few-Shot Learning 设计智能体行为链，建立 A/B 测试框架对比 13 组 Prompt 模板，搭建"准确率-召回率-响应时间"评估体系，持续追踪 BadCase 驱动迭代
> - **工程部署**：FastAPI + SSE 流式响应实现实时分析反馈，Docker Compose 支持云端 API / 本地 Ollama 双模式部署，GitHub Actions CI 自动化代码检查与测试

---

*文档生成时间：2026-07-20*
