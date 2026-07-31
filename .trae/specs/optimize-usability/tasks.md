# Tasks

## Task 1: 分析历史记录（后端）
- [x] 1.1 新增 `AnalysisHistory` 数据模型（`backend/app/models/`），字段：id, text, scan_result(JSON), matched_cases(JSON), prediction(JSON), governance(JSON), risk_level, risk_type, created_at
- [x] 1.2 新增 API：`GET /api/v1/analysis/history`（分页列表）、`GET /api/v1/analysis/history/{id}`（详情）
- [x] 1.3 在 `sentiment_service.py` 分析完成后自动保存到 `AnalysisHistory` 表
- [x] 1.4 在 `routes.py` 注册新路由

## Task 2: 分析历史记录（前端）
- [x] 2.1 新增 `History.tsx` 页面，展示分析历史分页列表（时间、文本摘要、风险等级、风险类型）
- [x] 2.2 支持点击查看详情，展示完整分析结果（扫描、匹配、预测、治理方案）
- [x] 2.3 在 `api.ts` 新增对应的 API 函数和类型定义
- [x] 2.4 在导航栏添加"分析历史"入口

## Task 3: Dashboard 自动刷新
- [x] 3.1 在 `Dashboard.tsx` 添加 `useEffect` + `setInterval` 每 30 秒自动拉取 `/dashboard/stats`
- [x] 3.2 新增"高危事件实时卡片"区域，展示最近 5 条高风险事件（标题、类型、评分、时间）
- [x] 3.3 API 新增 `GET /dashboard/recent-high-risk` 端点，返回最近 5 条高危事件

## Task 4: 数据导出
- [x] 4.1 后端新增 `GET /api/v1/sentiment/events/export/csv` 端点，返回 CSV 文件流
- [x] 4.2 前端 Dashboard 页面添加"导出 CSV"按钮，触发下载
- [x] 4.3 前端分析结果页添加"导出报告"按钮

## Task 5: 企业风险画像增强
- [x] 5.1 后端新增 `GET /api/v1/enterprises/{id}/trend` 端点，返回近 30 天风险评分趋势
- [x] 5.2 前端 `Enterprises.tsx` 企业详情页新增关联事件列表和风险趋势折线图

## Task 6: 爬虫定时采集
- [x] 6.1 后端新增 `app/crawler/scheduler.py`，使用 `asyncio` 实现每 30 分钟定时采集
- [x] 6.2 新增 `crawler_logs` 表，记录每次采集的时间、采集数、成功/失败源
- [x] 6.3 新增 `GET /api/v1/crawler/logs` 端点，返回最近 10 次采集日志
- [x] 6.4 在 `app/main.py` 的 lifespan 中启动定时任务

## Task 7: 全量验证
- [x] 7.1 Ruff lint 全量通过（app + tests）
- [x] 7.2 Pytest 全量通过（含新增测试）
- [x] 7.3 前端 `npm run build` 通过
- [x] 7.4 手动测试：分析历史 → Dashboard 刷新 → 导出 CSV → 企业趋势 → 定时采集

# Task Dependencies
- Task 2 依赖 Task 1（前端需要后端 API 就绪）
- Task 3.3 依赖 Task 3.1（API 端点需要先有）
- Task 5.2 依赖 Task 5.1
- Task 6.4 依赖 Task 6.1/6.2/6.3
- Task 7 依赖所有任务完成
- Task 1, 3, 4, 5, 6 后端部分可并行开发