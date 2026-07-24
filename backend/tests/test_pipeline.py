"""清洗管线测试。

测试 7 步清洗流程的每一步：
1. HTML 去标签（含 script/style 边界）
2. 文本规范化（超长截断到 5000）
3. URL hash 计算
4. SimHash 计算 + 去重（含近似标题）
5. 实体提取（含误匹配过滤）
6. 风险分类（覆盖 11 种 risk_type）
7. 风险等级评估（边界值 0.4/0.6/0.8）
8. 行业归类
"""

import os
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sentiment.db")
os.environ.setdefault("VECTOR_DB_PATH", "./test_chroma_data")

from app.agents.scanner import SentimentScannerAgent
from app.crawler.pipeline import CleanedArticle, CleaningPipeline
from app.crawler.scraper import RawNewsItem

# ------------------------------------------------------------------
# Step 1: HTML 去标签
# ------------------------------------------------------------------

class TestStripHtml:
    """测试 HTML 标签去除。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()

    def test_basic_html_tags(self):
        """测试基本 HTML 标签去除。"""
        html = "<p>这是一段<b>加粗</b>文本</p>"
        result = self.pipeline._strip_html(html)
        assert "<" not in result
        assert "加粗" in result
        assert "这是一段" in result

    def test_script_tag_removal(self):
        """测试 script 标签及其内容被完全移除。"""
        html = """
        <div>可见内容</div>
        <script>alert('恶意代码');var x = 'secret';</script>
        <p>更多内容</p>
        """
        result = self.pipeline._strip_html(html)
        assert "可见内容" in result
        assert "更多内容" in result
        assert "alert" not in result
        assert "secret" not in result

    def test_style_tag_removal(self):
        """测试 style 标签及其内容被完全移除。"""
        html = """
        <style>.hidden { display: none; color: red; }</style>
        <p>正文内容</p>
        """
        result = self.pipeline._strip_html(html)
        assert "正文内容" in result
        assert "display" not in result
        assert "color: red" not in result

    def test_nested_tags(self):
        """测试嵌套标签去除。"""
        html = "<div><p><span>嵌套<em>文本</em></span></p></div>"
        result = self.pipeline._strip_html(html)
        assert "<" not in result
        assert "嵌套" in result
        assert "文本" in result

    def test_empty_string(self):
        """测试空字符串输入。"""
        assert self.pipeline._strip_html("") == ""


# ------------------------------------------------------------------
# Step 2: 文本规范化
# ------------------------------------------------------------------

class TestNormalizeText:
    """测试文本规范化。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()

    def test_extra_whitespace(self):
        """测试多余空白被合并为单个空格。"""
        text = "这是   一段   有多余空白的文本"
        result = self.pipeline._normalize_text(text)
        assert "   " not in result
        assert result == "这是 一段 有多余空白的文本"

    def test_newlines(self):
        """测试换行符被替换为空格。"""
        text = "第一行\n第二行\n第三行"
        result = self.pipeline._normalize_text(text)
        assert "\n" not in result
        assert "第一行" in result
        assert "第二行" in result

    def test_truncation(self):
        """测试超长文本被截断到 MAX_CONTENT_LENGTH。"""
        text = "字" * 6000
        result = self.pipeline._normalize_text(text)
        assert len(result) == 5000

    def test_short_text_unchanged(self):
        """测试短文本不被修改。"""
        text = "短文本"
        result = self.pipeline._normalize_text(text)
        assert result == "短文本"

    def test_empty_string(self):
        """测试空字符串输入。"""
        assert self.pipeline._normalize_text("") == ""


# ------------------------------------------------------------------
# Step 3: URL hash 计算
# ------------------------------------------------------------------

class TestUrlHash:
    """测试 URL hash 计算。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()

    def test_consistent_hash(self):
        """测试相同 URL 返回相同 hash。"""
        url = "https://example.com/news/123"
        hash1 = self.pipeline._compute_url_hash(url)
        hash2 = self.pipeline._compute_url_hash(url)
        assert hash1 == hash2

    def test_different_urls_different_hash(self):
        """测试不同 URL 返回不同 hash。"""
        hash1 = self.pipeline._compute_url_hash("https://example.com/1")
        hash2 = self.pipeline._compute_url_hash("https://example.com/2")
        assert hash1 != hash2

    def test_hash_is_md5(self):
        """测试 hash 为 32 位 MD5 十六进制字符串。"""
        import hashlib
        url = "https://example.com/test"
        expected = hashlib.md5(url.encode()).hexdigest()
        assert self.pipeline._compute_url_hash(url) == expected
        assert len(self.pipeline._compute_url_hash(url)) == 32


# ------------------------------------------------------------------
# Step 4: SimHash + 去重
# ------------------------------------------------------------------

class TestSimHash:
    """测试 SimHash 计算与去重。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()

    def test_same_text_same_hash(self):
        """测试相同文本返回相同 SimHash。"""
        text = "某科技公司因数据泄露被监管部门处罚"
        h1 = self.pipeline._simhash(text)
        h2 = self.pipeline._simhash(text)
        assert h1 == h2

    def test_different_text_different_hash(self):
        """测试不同文本返回不同 SimHash。"""
        h1 = self.pipeline._simhash("某公司因产品质量问题被召回")
        h2 = self.pipeline._simhash("某银行因金融违规被罚单")
        assert h1 != h2

    def test_empty_text(self):
        """测试空文本返回 0。"""
        assert self.pipeline._simhash("") == 0

    def test_hamming_distance_same(self):
        """测试相同 hash 汉明距离为 0。"""
        h = self.pipeline._simhash("测试文本")
        assert self.pipeline._hamming_distance(h, h) == 0

    def test_hamming_distance_different(self):
        """测试不同 hash 汉明距离大于 0。"""
        h1 = self.pipeline._simhash("苹果公司发布新品")
        h2 = self.pipeline._simhash("腾讯集团收购企业")
        assert self.pipeline._hamming_distance(h1, h2) > 0

    def test_similarity_same(self):
        """测试相同 hash 相似度为 1.0。"""
        h = self.pipeline._simhash("测试文本")
        assert self.pipeline._simhash_similarity(h, h) == 1.0

    def test_similarity_range(self):
        """测试相似度在 [0, 1] 范围内。"""
        h1 = self.pipeline._simhash("文本一")
        h2 = self.pipeline._simhash("文本二")
        sim = self.pipeline._simhash_similarity(h1, h2)
        assert 0.0 <= sim <= 1.0


class TestDeduplication:
    """测试去重逻辑。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()

    def test_url_hash_exact_duplicate(self):
        """测试 URL hash 精确匹配去重。"""
        url_hash = self.pipeline._compute_url_hash("https://example.com/1")
        simhash = self.pipeline._simhash("测试文本")
        article = SimpleNamespace(url_hash=url_hash, simhash=simhash)

        seen_url_hashes = {url_hash}
        seen_simhashes = [simhash]

        assert self.pipeline._is_duplicate(article, seen_url_hashes, seen_simhashes) is True

    def test_simhash_near_duplicate(self):
        """测试 SimHash 近似匹配去重（高度相似文本）。"""
        # 使用几乎相同的文本（仅末尾不同）
        text1 = "某科技公司因数据泄露被监管部门立案调查，用户隐私信息遭到大规模泄露"
        text2 = "某科技公司因数据泄露被监管部门立案调查，用户隐私信息遭到大规模泄露。"

        h1 = self.pipeline._simhash(text1)
        h2 = self.pipeline._simhash(text2)
        sim = self.pipeline._simhash_similarity(h1, h2)

        # 近似文本应该有较高相似度
        assert sim >= 0.85

        # 测试去重检测
        url_hash = self.pipeline._compute_url_hash("https://example.com/2")
        article = SimpleNamespace(url_hash=url_hash, simhash=h2)
        seen_url_hashes = set()
        seen_simhashes = [h1]

        assert self.pipeline._is_duplicate(article, seen_url_hashes, seen_simhashes) is True

    def test_non_duplicate(self):
        """测试非重复内容不被误判。"""
        text1 = "苹果公司发布了全新的iPhone手机产品"
        text2 = "建设银行因金融违规收到证监会罚单"

        h1 = self.pipeline._simhash(text1)
        h2 = self.pipeline._simhash(text2)

        url_hash = self.pipeline._compute_url_hash("https://example.com/new")
        article = SimpleNamespace(url_hash=url_hash, simhash=h2)
        seen_url_hashes = {"different_hash"}
        seen_simhashes = [h1]

        assert self.pipeline._is_duplicate(article, seen_url_hashes, seen_simhashes) is False


# ------------------------------------------------------------------
# Step 5: 实体提取
# ------------------------------------------------------------------

class TestEntityExtraction:
    """测试企业实体提取。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()

    def test_extract_company(self):
        """测试提取公司名称。"""
        text = "腾讯科技有限公司因数据泄露被处罚"
        entities = self.pipeline._extract_entities(text)
        assert "腾讯科技有限公司" in entities

    def test_extract_multiple_entities(self):
        """测试提取多个企业名称。"""
        text = "阿里巴巴集团发布了新品。腾讯科技公司参与了投资，京东电商平台负责销售。"
        entities = self.pipeline._extract_entities(text)
        assert "阿里巴巴集团" in entities
        assert "腾讯科技公司" in entities
        assert "京东电商平台" in entities

    def test_dedup_entities(self):
        """测试实体去重。"""
        text = "腾讯科技公司发布新品，腾讯科技公司股价上涨"
        entities = self.pipeline._extract_entities(text)
        assert entities.count("腾讯科技公司") == 1

    def test_max_five_entities(self):
        """测试最多返回 5 个实体。"""
        text = "甲公司、乙集团、丙企业、丁平台、戊银行、己保险、庚证券"
        entities = self.pipeline._extract_entities(text)
        assert len(entities) <= 5

    def test_no_entities(self):
        """测试无企业名时返回空列表。"""
        text = "今天天气很好，适合户外运动"
        entities = self.pipeline._extract_entities(text)
        assert len(entities) == 0

    def test_various_suffixes(self):
        """测试各种企业后缀匹配。"""
        text = "华夏银行、南方基金、方正证券、平安保险、全聚德餐饮"
        entities = self.pipeline._extract_entities(text)
        # 每个后缀都应该被匹配到
        assert len(entities) == 5


# ------------------------------------------------------------------
# Step 6a: 风险类型分类
# ------------------------------------------------------------------

class TestRiskTypeClassification:
    """测试风险类型分类（覆盖 11 种 risk_type）。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()
        self.all_risk_types = list(SentimentScannerAgent.RISK_KEYWORDS.keys())
        assert len(self.all_risk_types) == 11  # 确认有 11 种风险类型

    def test_product_quality(self):
        """测试产品质量风险识别。"""
        text = "某汽车公司因刹车缺陷宣布召回，产品质量存在严重问题"
        result = self.pipeline._classify_risk_type(text)
        assert result == "产品质量"

    def test_food_safety(self):
        """测试食品安全风险识别。"""
        text = "某餐饮企业被查出食品过期，消费者吃出异物后呕吐腹泻"
        result = self.pipeline._classify_risk_type(text)
        assert result == "食品安全"

    def test_data_breach(self):
        """测试数据泄露风险识别。"""
        text = "某平台发生数据泄露事件，用户隐私信息被黑客窃取"
        result = self.pipeline._classify_risk_type(text)
        assert result == "数据泄露"

    def test_labor_dispute(self):
        """测试劳资纠纷风险识别。"""
        text = "某公司大规模裁员，员工因欠薪和加班问题发起罢工"
        result = self.pipeline._classify_risk_type(text)
        assert result == "劳资纠纷"

    def test_executive_scandal(self):
        """测试高管丑闻风险识别。"""
        text = "某公司CEO因贪腐被捕，高管涉嫌行贿受贿被拘留"
        result = self.pipeline._classify_risk_type(text)
        assert result == "高管丑闻"

    def test_environmental_penalty(self):
        """测试环保处罚风险识别。"""
        text = "某企业因废水排放超标被环保督察处罚，废气污染严重"
        result = self.pipeline._classify_risk_type(text)
        assert result == "环保处罚"

    def test_false_advertising(self):
        """测试虚假宣传风险识别。"""
        text = "某公司因虚假宣传被处罚，广告违法夸大功效误导消费者"
        result = self.pipeline._classify_risk_type(text)
        assert result == "虚假宣传"

    def test_service_outage(self):
        """测试服务中断风险识别。"""
        text = "某平台系统故障导致宕机崩溃，用户无法登录，服务中断"
        result = self.pipeline._classify_risk_type(text)
        assert result == "服务中断"

    def test_financial_violation(self):
        """测试金融违规风险识别。"""
        text = "某银行因金融违规收到证监会罚单，涉嫌内幕交易操纵股价"
        result = self.pipeline._classify_risk_type(text)
        assert result == "金融违规"

    def test_intellectual_property(self):
        """测试知识产权风险识别。"""
        text = "某公司因专利侵权被起诉，涉嫌抄袭盗版商标版权"
        result = self.pipeline._classify_risk_type(text)
        assert result == "知识产权"

    def test_tax_issue(self):
        """测试税务问题风险识别。"""
        text = "某企业因偷税漏税被税务稽查，涉嫌虚开发票逃税"
        result = self.pipeline._classify_risk_type(text)
        assert result == "税务问题"

    def test_no_match_returns_other(self):
        """测试无匹配关键词时返回'其他'。"""
        text = "今天阳光明媚，适合户外散步和运动"
        result = self.pipeline._classify_risk_type(text)
        assert result == "其他"

    def test_most_hits_wins(self):
        """测试命中关键词最多的类型胜出。"""
        # 同时包含产品质量和食品安全关键词，但食品安全命中更多
        text = "食品过期添加剂农药残留吃出异物发霉变质拉肚子，产品质量有缺陷"
        result = self.pipeline._classify_risk_type(text)
        assert result == "食品安全"


# ------------------------------------------------------------------
# Step 6b: 风险等级评估
# ------------------------------------------------------------------

class TestRiskLevelAssessment:
    """测试风险等级评估（边界值 0.4/0.6/0.8）。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()

    def test_base_score_low(self):
        """测试基础分 0.2 映射为'低'（<0.4）。"""
        text = "今天天气不错"
        level, score = self.pipeline._assess_risk_level(text, "其他")
        assert level == "低"
        assert score == 0.2

    def test_risk_type_hit_medium(self):
        """测试 risk_type 命中 +0.3 → 0.5 映射为'中'（0.4-0.6）。"""
        text = "某公司存在产品质量问题"  # 只有 risk_type 命中，无额外负面词
        level, score = self.pipeline._assess_risk_level(text, "产品质量")
        assert level == "中"
        assert 0.4 <= score < 0.6

    def test_negative_keywords_high(self):
        """测试负面词命中推高到'高'（0.6-0.8）。"""
        # 基础 0.2 + risk_type 0.3 + 多个负面词
        text = "某公司丑闻曝光处罚下降亏损裁员暴雷"
        level, score = self.pipeline._assess_risk_level(text, "高管丑闻")
        assert score >= 0.6
        assert level in ("高", "极高")

    def test_high_confidence_extreme(self):
        """测试高危信号词推高到'极高'（≥0.8）。"""
        # 基础 0.2 + risk_type 0.3 + 负面词 + 高危词
        text = "某公司被监管处罚立案逮捕死亡爆炸大规模全国性丑闻曝光亏损"
        level, score = self.pipeline._assess_risk_level(text, "金融违规")
        assert score >= 0.8
        assert level == "极高"

    def test_score_capped_at_1(self):
        """测试分数上限为 1.0。"""
        # 大量负面词和高危词
        text = " ".join(SentimentScannerAgent.NEGATIVE_KEYWORDS * 5)
        text += " " + " ".join(SentimentScannerAgent.HIGH_CONFIDENCE_KEYWORDS * 5)
        level, score = self.pipeline._assess_risk_level(text, "金融违规")
        assert score <= 1.0

    def test_boundary_0_4(self):
        """测试边界值 0.4：score=0.4 应为'中'。"""
        # 基础 0.2 + risk_type 0.3 = 0.5（>0.4）
        text = "某企业存在税务问题"
        level, score = self.pipeline._assess_risk_level(text, "税务问题")
        assert score >= 0.4
        assert level != "低"

    def test_no_risk_type_low(self):
        """测试无风险类型命中时为'低'。"""
        text = "某公司发布了新产品，市场反应良好"
        level, score = self.pipeline._assess_risk_level(text, "其他")
        assert level == "低"


# ------------------------------------------------------------------
# Step 6c: 行业归类
# ------------------------------------------------------------------

class TestIndustryClassification:
    """测试行业归类。"""

    def setup_method(self):
        self.pipeline = CleaningPipeline()

    def test_internet(self):
        """测试互联网行业识别。"""
        text = "某平台App电商直播外卖网约车"
        result = self.pipeline._classify_industry(text)
        assert result == "互联网"

    def test_finance(self):
        """测试金融行业识别。"""
        text = "某银行保险证券基金贷款理财"
        result = self.pipeline._classify_industry(text)
        assert result == "金融"

    def test_automotive(self):
        """测试汽车行业识别。"""
        text = "某汽车新能源电动车车企动力电池"
        result = self.pipeline._classify_industry(text)
        assert result == "汽车"

    def test_no_match_returns_general(self):
        """测试无匹配时返回'综合'。"""
        text = "今天阳光明媚"
        result = self.pipeline._classify_industry(text)
        assert result == "综合"

    def test_most_hits_wins(self):
        """测试命中关键词最多的行业胜出。"""
        text = "银行保险证券基金贷款理财信托支付"  # 金融命中 8 个
        result = self.pipeline._classify_industry(text)
        assert result == "金融"


# ------------------------------------------------------------------
# 完整管线集成测试
# ------------------------------------------------------------------

class TestPipelineIntegration:
    """测试完整清洗管线集成。"""

    def test_clean_basic(self):
        """测试 clean() 基本流程。"""
        pipeline = CleaningPipeline()
        raw_items = [
            RawNewsItem(
                title="<p>某科技公司因数据泄露被处罚</p>",
                content="<div>某科技有限公司因用户数据泄露被监管部门处罚，黑客窃取了大量用户信息。</div>",
                source_name="test_source",
                url="https://example.com/news/1",
                published_at="2024-01-01",
            ),
        ]
        articles = pipeline.clean(raw_items)

        assert len(articles) == 1
        article = articles[0]
        assert isinstance(article, CleanedArticle)
        assert "<" not in article.title  # HTML 已去除
        assert "<" not in article.cleaned_content
        assert article.source_name == "test_source"
        assert article.url == "https://example.com/news/1"
        assert len(article.url_hash) == 32  # MD5
        assert article.risk_type == "数据泄露"
        assert article.risk_level in ("低", "中", "高", "极高")
        assert article.industry in ("互联网", "金融", "综合")
        assert isinstance(article.entities, list)
        assert isinstance(article.tags, list)
        assert isinstance(article.governance_playbook, dict)

    def test_clean_deduplication(self):
        """测试 clean() 去重：相同 URL 的条目只保留一条。"""
        pipeline = CleaningPipeline()
        raw_items = [
            RawNewsItem(
                title="某公司因数据泄露被处罚",
                content="某科技有限公司因用户数据泄露被监管部门处罚",
                source_name="test",
                url="https://example.com/dup",
            ),
            RawNewsItem(
                title="某公司因数据泄露被处罚",
                content="某科技有限公司因用户数据泄露被监管部门处罚",
                source_name="test",
                url="https://example.com/dup",  # 相同 URL
            ),
        ]
        articles = pipeline.clean(raw_items)
        assert len(articles) == 1  # 第二条被去重

    def test_clean_empty_input(self):
        """测试空输入返回空列表。"""
        pipeline = CleaningPipeline()
        articles = pipeline.clean([])
        assert len(articles) == 0

    def test_clean_strips_html_in_content(self):
        """测试清洗后内容不含 HTML 标签。"""
        pipeline = CleaningPipeline()
        raw_items = [
            RawNewsItem(
                title="<script>alert(1)</script>正常标题",
                content="<style>.x{}</style><p>正常内容</p><script>var x=1</script>",
                source_name="test",
                url="https://example.com/html",
            ),
        ]
        articles = pipeline.clean(raw_items)
        assert len(articles) == 1
        assert "alert" not in articles[0].title
        assert "alert" not in articles[0].cleaned_content
        assert "var x" not in articles[0].cleaned_content
        assert "正常标题" in articles[0].title
        assert "正常内容" in articles[0].cleaned_content

    def test_governance_playbook_populated(self):
        """测试有风险类型时 governance_playbook 被填充。"""
        pipeline = CleaningPipeline()
        raw_items = [
            RawNewsItem(
                title="某公司因食品过期被查处",
                content="某餐饮企业被查出食品过期添加剂超标，消费者吃出异物后呕吐腹泻",
                source_name="test",
                url="https://example.com/food",
            ),
        ]
        articles = pipeline.clean(raw_items)
        assert len(articles) == 1
        article = articles[0]
        assert article.risk_type == "食品安全"
        assert len(article.governance_playbook) > 0
        assert "summary" in article.governance_playbook
        assert "immediate_actions" in article.governance_playbook
        assert "spokesperson_message" in article.governance_playbook
