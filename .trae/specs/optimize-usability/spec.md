# 项目实用性优化 Spec

## Why
当前项目基础功能已跑通（Ruff 0 错误、pytest 93/93 全过），但距离实际可用还有差距：缺少分析历史记录、Dashboard 数据不自动刷新、无法导出报告、企业画像缺少风险趋势。需要补齐这些"最后一公里"功能，让系统真正可用。

## What Changes
- 新增"分析历史"页面：保存每次分析结果，支持查看和对比
- Dashboard 自动刷新：统计数据定时刷新，新增高危事件实时卡片
- 数据导出：支持导出分析结果为 CSV/Excel
- 企业画像增强：关联舆情事件列表，展示风险评分趋势
- 爬虫定时采集：新增后端定时任务，每 30 分钟自动采集一次

## Impact
- Affected specs: 新增 5 个功能模块
- Affected code: `backend/app/api/routes.py`, `backend/app/models/`, `backend/app/services/`, `frontend/src/pages/`, `frontend/src/api.ts`

---

## ADDED Requirements

### Requirement: 分析历史记录
系统 SHALL 保存每次舆情分析的结果，提供历史记录查询和详情查看。

#### Scenario: 分析历史自动保存
- **WHEN** 用户通过 `/sentiment/analyze` 或 `/sentiment/analyze/stream` 完成分析
- **THEN** 分析结果自动保存到 `analysis_history` 表，包含输入文本、分析结果、时间戳

#### Scenario: 查看分析历史列表
- **WHEN** 用户访问分析历史页面
- **THEN** 显示分页列表，每条记录展示：分析时间、输入文本摘要、风险等级、风险类型

#### Scenario: 查看分析详情
- **WHEN** 用户点击某条历史记录
- **THEN** 展示完整分析结果：扫描结果、匹配案例、风险预测、治理方案

---

### Requirement: Dashboard 自动刷新
系统 SHALL 在 Dashboard 页面提供自动刷新机制，保持数据实时性。

#### Scenario: 自动刷新统计数据
- **WHEN** Dashboard 页面打开
- **THEN** 每 30 秒自动拉取最新统计数据（事件总数、风险分布、类型分布）

#### Scenario: 高危事件实时卡片
- **WHEN** Dashboard 加载
- **THEN** 展示最近 5 条高危事件卡片，包含标题、风险类型、风险评分、时间

---

### Requirement: 数据导出
系统 SHALL 支持将舆情事件列表导出为 CSV 文件。

#### Scenario: 导出事件列表
- **WHEN** 用户在事件列表页点击"导出 CSV"
- **THEN** 下载包含所有事件字段的 CSV 文件（标题、来源、风险等级、风险类型、风险评分、时间）

#### Scenario: 导出分析结果
- **WHEN** 用户在分析结果页点击"导出报告"
- **THEN** 下载包含完整分析结果的 CSV 文件

---

### Requirement: 企业风险画像增强
系统 SHALL 在企业画像页面展示关联舆情事件和风险评分趋势。

#### Scenario: 企业关联事件列表
- **WHEN** 用户查看企业详情
- **THEN** 展示该企业关联的舆情事件列表，按风险评分降序排列

#### Scenario: 企业风险趋势
- **WHEN** 用户查看企业详情
- **THEN** 展示该企业近 30 天风险评分变化趋势图

---

### Requirement: 爬虫定时采集
系统 SHALL 支持通过后端定时任务自动触发爬虫采集。

#### Scenario: 定时自动采集
- **WHEN** 系统运行中
- **THEN** 每 30 分钟自动执行一次爬虫采集，记录采集日志

#### Scenario: 采集日志查询
- **WHEN** 用户查看爬虫状态
- **THEN** 展示最近 10 次采集记录：时间、采集数、成功源数、失败源数