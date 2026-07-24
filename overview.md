# CPublic Sentiment 舆情系统优化 — 交付概览

## TL;DR
对 CPublic Sentiment 企业舆情风险预警系统进行全面优化，重写爬虫采集真实新闻数据，新建7步数据清洗管线，将 469 条真实新闻清洗后填充到系统中，替代原有全部 Faker 假数据。

## 交付概览

| 指标 | 结果 |
|------|------|
| 交付状态 | ✅ 完成 |
| 测试通过率 | 93/93 (100%) |
| 已知问题数 | 2（36kr/财联社 API 不可用，已通过 RSS 替代方案覆盖） |
| 工作流 | 标准 SOP（PM → Architect → Engineer → QA） |

## 数据填充结果

| 数据类型 | 数量 |
|----------|------|
| 采集新闻 | 469 条（7 个稳定 RSS 源 × 多次采集） |
| 清洗后入库 | 469 条事件 |
| 案例生成 | 18 条 |
| 企业匹配 | 47 家 |
| 向量索引同步 | 65 条 |

## 核心改动

### 后端
- **爬虫重写**：`app/crawler/sources.py` + `scraper.py` — 21 个真实数据源（7 个 RSS 稳定可用），asyncio 并发采集，feedparser 标准化解析，单源 try/except 隔离
- **数据清洗管线**：`app/crawler/pipeline.py` — 7步模块化清洗（HTML去标签→文本规范化→SimHash去重→实体提取→风险分类→等级评估→行业归类+Playbook匹配）
- **真实数据初始化**：`app/data/init_real_data.py` — 编排器串联采集→清洗→持久化→向量同步，支持增量去重（external_id = URL MD5 hash）
- **Playbook 知识库**：`app/data/playbook_knowledge.py` — 11种风险类型的真实治理方案
- **API 优化**：`/crawler/run` 持久化+增量去重+选择性分析；`/cases` 全文搜索；空数据库降级处理

### 前端
- Dashboard 新增数据源状态卡片（各源采集数/成功失败）
- 事件列表增加「来源」列
- 空状态引导提示

### 测试
- `test_crawler.py`：19项（数据源配置、RSS/API解析、单源隔离）
- `test_pipeline.py`：59项（7步清洗每步独立测试）
- `test_api.py`：15项（含 /crawler/run 集成、增量去重、空数据库、全文搜索）

## 文件清单

### 新建文件
- `backend/app/crawler/pipeline.py`
- `backend/app/data/init_real_data.py`
- `backend/app/data/playbook_knowledge.py`
- `backend/tests/test_crawler.py`
- `backend/tests/test_pipeline.py`
- `deliverables/software-company/prd-cpublic-optimization.md`
- `deliverables/software-company/architecture-cpublic-optimization.md`

### 修改文件
- `backend/app/crawler/sources.py`（扩展至 21 源，7 个稳定可用）
- `backend/app/crawler/scraper.py`（重写）
- `backend/app/api/routes.py`
- `backend/app/api/schemas.py`
- `backend/app/services/sentiment_service.py`
- `backend/app/data/seed.py`
- `backend/scripts/seed_data.py`
- `frontend/src/types.ts`
- `frontend/src/api.ts`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Cases.tsx`
- `backend/tests/test_api.py`

## 已知限制
1. **2个API源不可用**：36kr API 返回 500、财联社 API 返回 404，已通过 RSS 替代方案（36kr_rss 稳定可用）覆盖
2. **案例量未达目标**：当前 18 案例（目标 ≥100），后续可扩展

## 用户下一步建议
1. **多次运行爬虫累积数据**：`POST http://localhost:8000/api/v1/crawler/run`（增量去重，可安全重复执行）
2. **扩展数据源**：在 `app/crawler/sources.py` 中添加更多可用 RSS 源
3. **启动系统查看效果**：后端 `uvicorn app.main:app --reload`，前端 `npm run dev`
