"""舆情数据清洗管线。

7 步清洗流程：
1. HTML 去标签（含 script/style）
2. 文本规范化（去多余空白/换行，截断 ≤5000 字符）
3. URL hash 计算（md5）
4. 去重（URL hash 精确 + SimHash 近似）
5. 实体提取（正则匹配企业名）
6. 风险分类 + 等级评估 + 行业归类
7. 标签构建 + 治理方案匹配

清洗后产出 CleanedArticle，可直接入库为 RiskCase / Enterprise / SentimentEvent。
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from app.agents.scanner import SentimentScannerAgent
from app.crawler.scraper import RawNewsItem
from app.data.playbook_knowledge import PlaybookKnowledgeBase

logger = logging.getLogger(__name__)


@dataclass
class CleanedArticle:
    """清洗后的新闻文章，包含风险分析结果。"""

    title: str
    cleaned_content: str
    source_name: str
    url: str
    url_hash: str
    entities: list[str] = field(default_factory=list)
    industry: str = "综合"
    risk_type: str = "其他"
    risk_level: str = "低"
    risk_score: float = 0.0
    tags: list[str] = field(default_factory=list)
    governance_playbook: dict[str, Any] = field(default_factory=dict)
    published_at: str = ""


class CleaningPipeline:
    """7 步清洗管线，将 RawNewsItem 转换为 CleanedArticle。"""

    # 内容最大长度（字符）
    MAX_CONTENT_LENGTH = 5000
    # SimHash 位数
    SIMHASH_BITS = 64
    # SimHash 相似度阈值（≥此值视为近似重复）
    SIMHASH_THRESHOLD = 0.85

    # 企业名正则模式（与 scanner.py 保持一致）
    ENTITY_PATTERN = re.compile(
        r"[\u4e00-\u9fa5]{2,}"
        r"(?:公司|集团|企业|平台|银行|保险|证券|基金|酒店|餐饮|科技|汽车|医药|地产|航空|物流|电商)"
    )

    def __init__(self):
        self._scanner = SentimentScannerAgent()
        self._playbook_kb = PlaybookKnowledgeBase()

    # ------------------------------------------------------------------
    # 编排入口
    # ------------------------------------------------------------------

    def clean(self, raw_items: list[RawNewsItem]) -> list[CleanedArticle]:
        """清洗管线入口：RawNewsItem → CleanedArticle。

        执行 7 步清洗，包含去重（URL hash + SimHash）。
        """
        cleaned: list[CleanedArticle] = []
        seen_url_hashes: set[str] = set()
        seen_simhashes: list[int] = []

        for raw in raw_items:
            # Step 1: HTML 去标签
            title = self._strip_html(raw.title)
            content = self._strip_html(raw.content)

            # Step 2: 文本规范化
            title = self._normalize_text(title)
            content = self._normalize_text(content)

            # 跳过空内容
            if not title or not content:
                continue

            # Step 3: URL hash 计算
            url_hash = self._compute_url_hash(raw.url or title)

            # Step 4: 去重检测
            combined_text = f"{title} {content}"
            simhash = self._simhash(combined_text)
            article_proxy = SimpleNamespace(url_hash=url_hash, simhash=simhash)

            if self._is_duplicate(article_proxy, seen_url_hashes, seen_simhashes):
                continue

            # 加入已见集合
            seen_url_hashes.add(url_hash)
            seen_simhashes.append(simhash)

            # Step 5: 实体提取
            entities = self._extract_entities(combined_text)

            # Step 6: 风险分类 + 等级评估 + 行业归类
            risk_type = self._classify_risk_type(combined_text)
            risk_level, risk_score = self._assess_risk_level(combined_text, risk_type)
            industry = self._classify_industry(combined_text)

            # Step 7: 标签构建 + 治理方案匹配
            tags = self._build_tags(risk_type, industry, entities)
            governance_playbook = self._match_playbook(risk_type)

            article = CleanedArticle(
                title=title,
                cleaned_content=content,
                source_name=raw.source_name,
                url=raw.url,
                url_hash=url_hash,
                entities=entities,
                industry=industry,
                risk_type=risk_type,
                risk_level=risk_level,
                risk_score=risk_score,
                tags=tags,
                governance_playbook=governance_playbook,
                published_at=raw.published_at,
            )
            cleaned.append(article)

        logger.info("清洗完成: 输入 %d 条, 输出 %d 条 (去重 %d 条)",
                     len(raw_items), len(cleaned), len(raw_items) - len(cleaned))
        return cleaned

    # ------------------------------------------------------------------
    # Step 1: HTML 去标签
    # ------------------------------------------------------------------

    def _strip_html(self, text: str) -> str:
        """使用 BeautifulSoup 去除 HTML 标签，包括 script/style 内容。"""
        if not text:
            return ""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(text, "html.parser")
            # 显式移除 script 和 style 标签及其内容
            for tag in soup.find_all(["script", "style"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)
        except ImportError:
            # bs4 不可用时回退到正则
            cleaned = re.sub(
                r"<(script|style)[^>]*>.*?</\1>",
                "", text, flags=re.DOTALL | re.IGNORECASE,
            )
            return re.sub(r"<[^>]+>", "", cleaned).strip()

    # ------------------------------------------------------------------
    # Step 2: 文本规范化
    # ------------------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        """去除多余空白和换行，截断到 MAX_CONTENT_LENGTH 字符。"""
        if not text:
            return ""
        # 合并连续空白（含换行、制表符）为单个空格
        normalized = re.sub(r"\s+", " ", text).strip()
        # 截断超长内容
        if len(normalized) > self.MAX_CONTENT_LENGTH:
            normalized = normalized[:self.MAX_CONTENT_LENGTH]
        return normalized

    # ------------------------------------------------------------------
    # Step 3: URL hash
    # ------------------------------------------------------------------

    def _compute_url_hash(self, url: str) -> str:
        """计算 URL 的 MD5 哈希值，用作唯一标识。"""
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Step 4a: SimHash 计算
    # ------------------------------------------------------------------

    def _tokenize_cn(self, text: str) -> list[str]:
        """中文 2-gram 分词：将连续的中文字符/字母数字按 2 字符滑动窗口切分。"""
        # 保留中文、字母、数字，去除标点和特殊符号
        cleaned = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)
        if len(cleaned) < 2:
            return [cleaned] if cleaned else []
        return [cleaned[i:i + 2] for i in range(len(cleaned) - 1)]

    def _simhash(self, text: str) -> int:
        """计算文本的 64-bit SimHash 指纹。

        算法：
        1. 中文 2-gram 分词
        2. 每个 token → md5 → 取前 64 bit
        3. 64 维累加器：bit=1 → +1, bit=0 → -1
        4. 累加器 > 0 → 该位取 1，否则取 0
        """
        tokens = self._tokenize_cn(text)
        if not tokens:
            return 0

        # 64 维累加器
        v = [0] * self.SIMHASH_BITS

        for token in tokens:
            # md5 → 取前 16 个十六进制字符 = 64 bit
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:16], 16)
            for i in range(self.SIMHASH_BITS):
                bit = (h >> i) & 1
                if bit:
                    v[i] += 1
                else:
                    v[i] -= 1

        # 生成最终指纹
        fingerprint = 0
        for i in range(self.SIMHASH_BITS):
            if v[i] > 0:
                fingerprint |= (1 << i)

        return fingerprint

    def _hamming_distance(self, h1: int, h2: int) -> int:
        """计算两个 64-bit 整数的汉明距离。"""
        return bin(h1 ^ h2).count("1")

    def _simhash_similarity(self, h1: int, h2: int) -> float:
        """计算 SimHash 相似度 = 1 - 汉明距离 / 位数。"""
        return 1.0 - self._hamming_distance(h1, h2) / self.SIMHASH_BITS

    # ------------------------------------------------------------------
    # Step 4b: 去重检测
    # ------------------------------------------------------------------

    def _is_duplicate(
        self,
        article: SimpleNamespace,
        seen_url_hashes: set[str],
        seen_simhashes: list[int],
    ) -> bool:
        """检测文章是否为重复内容。

        先检查 URL hash 精确匹配，再检查 SimHash 近似匹配。
        """
        # URL hash 精确匹配
        if article.url_hash in seen_url_hashes:
            return True

        # SimHash 近似匹配
        for seen_hash in seen_simhashes:
            similarity = self._simhash_similarity(article.simhash, seen_hash)
            if similarity >= self.SIMHASH_THRESHOLD:
                return True

        return False

    # ------------------------------------------------------------------
    # Step 5: 实体提取
    # ------------------------------------------------------------------

    def _extract_entities(self, text: str) -> list[str]:
        """正则匹配企业名称，去重后最多返回 5 个。"""
        matches = self.ENTITY_PATTERN.findall(text)
        # 去重并保持顺序
        seen: set[str] = set()
        entities: list[str] = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                entities.append(m)
        return entities[:5]

    # ------------------------------------------------------------------
    # Step 6a: 风险类型分类
    # ------------------------------------------------------------------

    def _classify_risk_type(self, text: str) -> str:
        """基于关键词匹配分类风险类型，返回命中关键词最多的类型。

        引用 SentimentScannerAgent.RISK_KEYWORDS（11 种风险类型）。
        无匹配返回 "其他"。
        """
        best_type = "其他"
        best_count = 0

        for risk_type, keywords in SentimentScannerAgent.RISK_KEYWORDS.items():
            hit_count = sum(1 for kw in keywords if kw in text)
            if hit_count > best_count:
                best_count = hit_count
                best_type = risk_type

        return best_type

    # ------------------------------------------------------------------
    # Step 6b: 风险等级评估
    # ------------------------------------------------------------------

    def _assess_risk_level(self, text: str, risk_type: str) -> tuple[str, float]:
        """评估风险等级和风险分数。

        评分规则：
        - 基础分 0.2
        - risk_type 命中（非"其他"）：+0.3
        - NEGATIVE_KEYWORDS 每命中 +0.05（上限 0.3）
        - HIGH_CONFIDENCE_KEYWORDS 每命中 +0.1（上限 0.3）

        等级映射：
        - <0.4 → 低
        - 0.4~0.6 → 中
        - 0.6~0.8 → 高
        - ≥0.8 → 极高
        """
        score = 0.2

        # risk_type 命中加分
        if risk_type != "其他":
            score += 0.3

        # NEGATIVE_KEYWORDS 命中加分（上限 0.3）
        negative_hits = sum(1 for kw in SentimentScannerAgent.NEGATIVE_KEYWORDS if kw in text)
        score += min(negative_hits * 0.05, 0.3)

        # HIGH_CONFIDENCE_KEYWORDS 命中加分（上限 0.3）
        high_conf_hits = sum(
            1 for kw in SentimentScannerAgent.HIGH_CONFIDENCE_KEYWORDS if kw in text
        )
        score += min(high_conf_hits * 0.1, 0.3)

        # 限制在 [0, 1] 范围
        score = round(min(score, 1.0), 4)

        # 等级映射
        if score < 0.4:
            level = "低"
        elif score < 0.6:
            level = "中"
        elif score < 0.8:
            level = "高"
        else:
            level = "极高"

        return (level, score)

    # ------------------------------------------------------------------
    # Step 6c: 行业归类
    # ------------------------------------------------------------------

    def _classify_industry(self, text: str) -> str:
        """基于关键词匹配归类行业，返回命中最多的行业。

        引用 SentimentScannerAgent.INDUSTRY_KEYWORDS（10 个行业）。
        无匹配返回 "综合"。
        """
        best_industry = "综合"
        best_count = 0

        for industry, keywords in SentimentScannerAgent.INDUSTRY_KEYWORDS.items():
            hit_count = sum(1 for kw in keywords if kw in text)
            if hit_count > best_count:
                best_count = hit_count
                best_industry = industry

        return best_industry

    # ------------------------------------------------------------------
    # Step 7a: 标签构建
    # ------------------------------------------------------------------

    def _build_tags(
        self, risk_type: str, industry: str, entities: list[str]
    ) -> list[str]:
        """组合风险类型、行业、实体为标签列表。"""
        tags: list[str] = []

        if risk_type and risk_type != "其他":
            tags.append(risk_type)

        if industry and industry != "综合":
            tags.append(industry)

        # 取前 2 个实体作为标签
        tags.extend(entities[:2])

        return tags

    # ------------------------------------------------------------------
    # Step 7b: 治理方案匹配
    # ------------------------------------------------------------------

    def _match_playbook(self, risk_type: str) -> dict[str, Any]:
        """根据风险类型匹配治理方案 Playbook。"""
        return self._playbook_kb.get_playbook(risk_type)
