# PRD — CPublic Sentiment 舆情系统全面优化

## 1. 项目信息

| 字段 | 内容 |
|------|------|
| **Language** | 中文 |
| **Programming Language** | Python 3.11 + FastAPI + LangGraph + ChromaDB（后端）；React 18 + TypeScript + Vite + Recharts（前端） |
| **Project Name** | cpublic_sentiment_optimization |
| **原始需求复述** | 全面优化 CPublic Sentiment 舆情风险预警系统，并使用爬虫从公开数据源采集真实新闻数据，经清洗后填充到系统中，替代当前全部由 Faker 生成的假数据 |

## 2. 产品定义

### 2.1 产品目标

1. **真实数据驱动**：用爬虫从中国大陆可访问的公开新闻/RSS 数据源采集真实舆情数据，经清洗管线处理后填充到 RiskCase / Enterprise / SentimentEvent 三张核心表中，彻底替代 Faker 假数据，使系统展示的内容具有真实业务参考价值。

2. **爬虫可用且可增量运行**：重写爬虫模块，使用真实的 RSS/API 端点（而非首页 URL），支持 feedparser 解析、HTML 清洗、文本去重、实体提取与风险分类，且可重复运行不产生重复入库。

3. **系统整体可用性提升**：修复后端 API 与前端在真实数据场景下的兼容性问题，优化数据质量校验与错误处理，确保从数据采集→清洗→入库→分析→展示的全链路可用。

### 2.2 用户故事

1. **作为舆情分析师**，我希望系统能自动从多个公开新闻源采集真实舆情信息，这样我无需手动录入就能看到最新的风险事件。

2. **作为风险管理者**，我希望案例库和企业画像中的数据来自真实新闻报道，这样我基于历史案例做出的风险判断才有实际参考价值。

3. **作为系统运维人员**，我希望爬虫可以重复执行而不产生重复数据，这样我可以定期增量更新数据而不用担心数据膨胀。

4. **作为产品负责人**，我希望仪表盘和各页面上展示的统计数据基于真实数据，这样在向客户演示时系统能体现真实业务价值。

5. **作为开发者**，我希望数据清洗管线能自动完成 HTML 去标签、文本规范化、去重、实体提取和风险类型分类，这样清洗后的数据可直接映射到现有数据模型。

## 3. 技术规范

### 3.1 需求池

#### P0 — Must Have（核心，阻塞发布）

| ID | 需求 | 验收标准 |
|----|------|----------|
| P0-1 | **重写数据源配置** | `sources.py` 中每个源必须配置真实的 RSS/API 端点 URL（非首页），明确标注 `type`（rss/api/html）和 `parser` 类型；至少覆盖 3 个中国大陆可访问的公开数据源 |
| P0-2 | **实现 RSS 解析** | 使用 `feedparser` 库解析 RSS/Atom feed，正确提取 title、content/summary、link、published_at 字段；替代当前猜测式的 JSON 解析逻辑 |
| P0-3 | **构建数据清洗管线** | 新建 `pipeline.py` 模块，包含：① HTML 标签去除（BeautifulSoup）② 文本规范化（去空白、统一编码、截断超长文本）③ URL 去重（基于 URL hash + 标题相似度）④ 实体提取（正则匹配企业名/机构名）⑤ 风险类型分类（基于 scanner.py 已有关键词词典） |
| P0-4 | **真实数据填充 — 案例库** | 从采集清洗后的新闻中筛选舆情相关条目，映射到 `RiskCase` 模型（title/summary/industry/risk_type/risk_level/source_url/tags/governance_playbook）；至少填充 100 条真实案例 |
| P0-5 | **真实数据填充 — 企业画像** | 从新闻实体提取中识别真实企业名称，映射到 `Enterprise` 模型（name/industry/scale/region/business_tags/risk_profile/risk_score_history）；至少填充 30 家真实企业 |
| P0-6 | **真实数据填充 — 舆情事件** | 将清洗后的新闻条目映射到 `SentimentEvent` 模型（title/content/source/url/risk_level/risk_type/risk_score/matched_case_ids/status）；至少填充 50 条真实事件 |
| P0-7 | **增量更新能力** | 爬虫可重复运行，通过 `external_id`（URL hash 或内容 hash）去重，不产生重复入库；每次运行只新增未见过的条目 |
| P0-8 | **爬虫 API 改造** | `/crawler/run` 接口改为：先采集→清洗→持久化原始数据→再选择性分析；不再只分析 top 10 条且不持久化；返回采集数、清洗数、入库数、去重数、分析数 |
| P0-9 | **数据初始化脚本** | 提供独立的初始化脚本（如 `python -m app.data.init_real_data`），一次性爬取并填充真实数据到三张表，替代当前 `seed.py` 的 Faker 逻辑；保留 `seed.py` 作为 fallback |

#### P1 — Should Have（重要，不影响核心可用但影响体验）

| ID | 需求 | 验收标准 |
|----|------|----------|
| P1-1 | **数据源扩展** | 在 P0 的 3 个源基础上，增加至 5+ 个数据源，覆盖不同行业（财经、科技、消费、食品等），提升数据覆盖面 |
| P1-2 | **风险等级自动评估** | 清洗管线中基于关键词权重 + 传播指标，为每条新闻自动分配 risk_level（低/中/高/极高），而非随机生成 |
| P1-3 | **RAG 向量索引同步** | 真实数据入库后，自动调用 `HybridRetriever.index_case()` / `index_enterprise()` 同步向量索引，确保分析功能可检索到真实案例 |
| P1-4 | **API 错误处理增强** | 所有 API 增加数据为空时的友好响应（非 500 错误）；爬虫接口增加超时处理与分源错误隔离（单源失败不影响其他源） |
| P1-5 | **数据质量校验** | 入库前校验必填字段（title/content/source 非空）、字段长度合规、risk_level 枚举值合法；不合格数据记录到日志并跳过 |
| P1-6 | **governance_playbook 真实化** | 案例的治理方案不再使用模板填空，改为基于 risk_type 从预置治理知识库中匹配，并结合新闻内容生成摘要 |
| P1-7 | **企业风险评分历史** | Enterprise 的 `risk_score_history` 基于该企业关联的真实事件计算，而非随机 uniform 生成 |

#### P2 — Nice to Have（优化体验）

| ID | 需求 | 验收标准 |
|----|------|----------|
| P2-1 | **前端数据源标识** | 仪表盘最近事件列表增加「数据来源」列，展示新闻源名称（如"新浪财经""36氪"），让用户明确数据出处 |
| P2-2 | **爬虫状态面板** | 前端新增或在仪表盘增加爬虫运行状态展示：最近运行时间、各源采集数、成功/失败源列表，替代当前仅 API 返回的状态 |
| P2-3 | **案例库搜索增强** | Cases 页面搜索支持全文检索（title + summary），而非仅 title.contains |
| P2-4 | **事件详情页优化** | 事件详情展示原始新闻 URL（可点击跳转），让用户可追溯信息来源 |
| P2-5 | **空状态优化** | 各页面在无数据时展示引导性空状态（如"暂无数据，请运行爬虫采集"），并提供快捷操作按钮 |
| P2-6 | **加载状态优化** | 长耗时操作（爬虫运行、数据分析）增加 loading 骨架屏或进度提示 |

### 3.2 UI 设计稿

本次优化以前端**适配真实数据**为主，不涉及大规模 UI 重构。关键改进点：

#### 仪表盘 Dashboard
- 顶部指标卡片：数据来源不变，但数值将基于真实数据计算
- 新增「数据源状态」卡片（P2-2）：展示最近爬虫运行时间、各源采集条数、成功/失败状态
- 最近舆情事件列表：增加「来源」列，展示 `source` 字段对应的新闻源名称
- 所有图表（饼图/柱状图/折线图）：数据自动反映真实分布

#### 舆情分析 Analyze
- 功能不变，但 RAG 检索将命中真实案例而非 Faker 生成的模板案例
- 匹配案例展示的 title/summary 将是真实新闻内容
- 推理链中的 entities 将包含从新闻中提取的真实企业名

#### 案例库 Cases
- 列表展示真实新闻标题和摘要
- 搜索支持全文检索（P2-3）
- 治理方案展示真实匹配的 playbook

#### 企业画像 Enterprises
- 列表展示从新闻中识别的真实企业名称
- 企业详情页的风险评分趋势基于真实关联事件计算
- 企业关联事件列表展示真实舆情事件

#### 效果评估 Evaluation
- A/B 测试和准确率指标基于真实标注数据计算
- 当前假数据中约 40% 带标注，真实数据初期无标注，需适配空标注场景

### 3.3 待确认问题

| # | 问题 | 影响 | 默认建议 |
|---|------|------|----------|
| 1 | **数据源选择**：是否使用以下公开 RSS/API 源？① 中国新闻网 RSS ② 人民网 RSS ③ 新华网 RSS ④ 36氪 API ⑤ 百度新闻 RSS。如有其他偏好数据源请指定 | 决定 P0-1 数据源配置 | 默认使用 ①②③ + 36氪快讯 API + 财联社电报 API，共 5 个源 |
| 2 | **数据库策略**：当前使用 SQLite（`sentiment.db`）。真实数据填充后是否切换到 MySQL？还是继续用 SQLite？ | 影响 P0-9 初始化脚本和并发性能 | 默认继续用 SQLite（开发阶段足够），保留 MySQL 配置 |
| 3 | **LLM 依赖**：清洗管线中的风险分类和实体提取，是使用 LLM（需配置 OpenAI/Ollama）还是纯规则引擎？当前系统支持 fallback 规则引擎模式 | 影响 P0-3 清洗管线设计 | 默认纯规则引擎（基于 scanner.py 已有关键词词典），不依赖 LLM，确保离线可用 |
| 4 | **数据量预期**：首次初始化需要采集多少条数据？当前假数据规模为 520 案例 + 220 企业 + 80 事件 | 影响 P0-4/5/6 的采集轮次和时间 | 默认目标：≥100 案例 + ≥30 企业 + ≥50 事件，可多次运行爬虫累积 |
| 5 | **是否保留 Faker 假数据**：真实数据填充后，是否完全删除 `generator.py`？还是保留作为开发/测试 fallback？ | 影响 P0-9 和代码清理 | 默认保留 `generator.py` 但不再在初始化中使用，仅作为测试 fixture |
| 6 | **爬虫运行频率**：是否需要配置定时任务自动运行爬虫？还是仅手动触发？ | 影响 P1 架构设计 | 默认仅手动触发（通过 API 或脚本），后续可扩展定时任务 |
| 7 | **新闻内容抓取深度**：RSS 通常只提供摘要。是否需要进一步抓取新闻全文（访问详情页）？还是用摘要即可？ | 影响 P0-3 清洗管线和 P0-4 案例内容质量 | 默认使用 RSS 摘要 + 标题，如有需要可对部分源增加全文抓取 |

## 4. 数据源候选清单（中国大陆可访问）

以下为候选公开数据源，需在实现阶段验证可用性：

| 数据源 | 类型 | URL 候选 | 说明 |
|--------|------|----------|------|
| 中国新闻网 | RSS | `http://www.chinanews.com.cn/rss/scroll-news.xml` | 综合新闻滚动播报 |
| 人民网 | RSS | `http://www.people.com.cn/rss/politics.xml` | 时政社会新闻 |
| 新华网 | RSS | `http://www.xinhuanet.com/politics/news_politics.xml` | 时政财经新闻 |
| 36氪 | API | `https://gateway.36kr.com/api/missive/newsflash` | 科技创投快讯（需验证 API 格式） |
| 财联社 | API | `https://www.cls.cn/nodeapi/updateTelegraphList` | 财经电报快讯（需验证 API 格式） |

> **注意**：RSS 源优先（结构稳定、无需逆向工程），API 源需验证接口可用性与频率限制。实现时应做好单源失败隔离。

## 5. 数据清洗管线设计

```
原始新闻条目
    │
    ▼
[1] HTML 标签去除 ──── BeautifulSoup 清洗 content 字段
    │
    ▼
[2] 文本规范化 ──────── 去除多余空白/换行、统一全半角、截断超长文本（content ≤ 5000 字符）
    │
    ▼
[3] 去重 ────────────── 基于 URL hash 去重 + 标题 SimHash 相似度去重（阈值 0.85）
    │
    ▼
[4] 实体提取 ────────── 正则匹配企业名（XX公司/集团/科技/银行等后缀），输出 entities 列表
    │
    ▼
[5] 风险类型分类 ────── 基于 scanner.py RISK_KEYWORDS 词典匹配，输出 risk_type
    │                   无匹配则标记为"其他"，不入库为案例
    ▼
[6] 风险等级评估 ────── 基于 HIGH_CONFIDENCE_KEYWORDS + NEGATIVE_KEYWORDS 权重计算
    │                   输出 risk_level（低/中/高/极高）
    ▼
[7] 行业归类 ────────── 基于 INDUSTRY_KEYWORDS 词典匹配，输出 industry
    │
    ▼
清洗后结构化数据 → 映射到 RiskCase / Enterprise / SentimentEvent
```

## 6. 数据模型映射关系

| 爬虫清洗字段 | RiskCase | Enterprise | SentimentEvent |
|-------------|----------|------------|----------------|
| title | title | — | title |
| cleaned_content | summary | — | content |
| source_name | — | — | source |
| url | source_url | — | url |
| url_hash | — | — | external_id |
| entities[0] | — | name | enterprise_name |
| industry | industry | industry | — |
| risk_type | risk_type | risk_profile.primary_risk | risk_type |
| risk_level | risk_level | — | risk_level |
| risk_score | — | — | risk_score |
| tags | tags | — | — |
| governance_playbook | governance_playbook | — | — |
| — | — | business_tags, risk_score_history | matched_case_ids, governance_plan, reasoning_chain, status |

## 7. 技术约束

- **网络环境**：数据源必须在中国大陆网络环境下可直接访问（无需代理）
- **依赖最小化**：优先使用 `requirements.txt` 中已有的库（feedparser、beautifulsoup4、httpx），不引入新的重型依赖
- **离线可用**：清洗管线不依赖 LLM，纯规则引擎模式可工作
- **向后兼容**：不修改现有数据模型的表结构（不新增列），仅修改数据填充逻辑
- **数据库兼容**：同时支持 SQLite（开发）和 MySQL（生产），SQL 语句不使用 SQLite 专有语法
