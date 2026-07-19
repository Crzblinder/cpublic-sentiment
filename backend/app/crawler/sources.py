"""公开新闻数据源配置。

每个源定义包含：
- name: 数据源名称
- type: 采集类型 (rss / api / html)
- url: 请求地址
- parser: 解析方式
"""

SOURCES = [
    {
        "name": "sina_finance_rss",
        "type": "rss",
        "url": "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=30&page=1",
        "parser": "json_api",
        "description": "新浪财经滚动新闻（公开 API）",
    },
    {
        "name": "36kr_news",
        "type": "api",
        "url": "https://36kr.com/newsflashes",
        "parser": "html_parse",
        "description": "36氪快讯",
    },
    {
        "name": "cls_telegraph",
        "type": "api",
        "url": "https://www.cls.cn/nodeapi/updateTelegraph",
        "parser": "json_api",
        "description": "财联社电报",
    },
]
