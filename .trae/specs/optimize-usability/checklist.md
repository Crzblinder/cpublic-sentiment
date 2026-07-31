# Checklist

- [x] 分析历史自动保存：完成分析后 `AnalysisHistory` 表有记录
- [x] 分析历史列表：`GET /api/v1/analysis/history` 返回分页数据
- [x] 分析历史详情：`GET /api/v1/analysis/history/{id}` 返回完整分析结果
- [x] 前端分析历史页面：`/history` 可访问，展示分页列表
- [x] 前端分析历史详情：点击可展开完整分析结果
- [x] Dashboard 自动刷新：页面每 30 秒自动更新统计数据
- [x] 高危事件实时卡片：Dashboard 展示最近 5 条高危事件
- [x] 事件导出 CSV：`GET /api/v1/sentiment/events/export/csv` 返回 CSV 文件
- [x] 前端导出按钮：Dashboard 页面有"导出 CSV"按钮，点击触发下载
- [x] 企业风险趋势：`GET /api/v1/enterprises/{id}/trend` 返回 30 天趋势数据
- [x] 前端企业趋势图：企业详情页展示风险评分折线图
- [x] 前端企业关联事件：企业详情页展示关联舆情事件列表
- [x] 爬虫定时采集：后端每 30 分钟自动执行采集
- [x] 采集日志：`GET /api/v1/crawler/logs` 返回最近 10 次记录
- [x] Ruff lint：`python -m ruff check app tests` 0 错误
- [x] Pytest：`pytest -q` 全部通过
- [x] 前端构建：`npm run build` 成功