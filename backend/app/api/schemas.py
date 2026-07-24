from pydantic import BaseModel, ConfigDict, Field


class SentimentAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=5000, description="舆情文本内容")
    source: str = Field(default="manual", description="来源标识")
    enterprise_hint: str | None = Field(default=None, description="企业名称提示")
    prompt_variants: dict[str, str] | None = Field(
        default=None, description="Agent prompt 变体选择"
    )


class AbTestRequest(BaseModel):
    agent_type: str | None = Field(default=None, description="限定测试的 Agent 类型")
    dataset: list[dict] = Field(..., min_length=1, description="带标签的测试集")


class LabelRequest(BaseModel):
    event_id: int
    true_risk_level: str


class EventResponse(BaseModel):
    id: int
    title: str
    risk_level: str | None
    risk_type: str | None
    risk_score: float
    source: str | None = None
    status: str
    created_at: str | None

    model_config = ConfigDict(from_attributes=True)


class CrawlerRunResponse(BaseModel):
    """爬虫运行结果响应。"""

    fetched: int
    cleaned: int
    persisted: int
    deduped: int
    analyzed: int
    status: dict
