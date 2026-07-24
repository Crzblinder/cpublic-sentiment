"""公开新闻数据源配置。

每个源定义包含：
- name: 数据源名称 (snake_case)
- type: 采集类型 (rss / api)
- url: 请求地址
- parser: 解析方式 (feedparser / json_api)
- description: 数据源描述
- fields_map: API 源字段映射（可选，仅 json_api 类型需要）
"""

SOURCES = [
    # ────────── RSS 源 ──────────
    {
        "name": "chinanews_rss",
        "type": "rss",
        "url": "http://www.chinanews.com.cn/rss/scroll-news.xml",
        "parser": "feedparser",
        "description": "中国新闻网滚动新闻 RSS",
    },
    {
        "name": "people_rss",
        "type": "rss",
        "url": "http://www.people.com.cn/rss/politics.xml",
        "parser": "feedparser",
        "description": "人民网时政新闻 RSS",
    },
    {
        "name": "xinhua_rss",
        "type": "rss",
        "url": "http://www.xinhuanet.com/politics/news_politics.xml",
        "parser": "feedparser",
        "description": "新华网时政新闻 RSS",
    },
    {
        "name": "netease_rss",
        "type": "rss",
        "url": "https://www.163.com/feed/rss",
        "parser": "feedparser",
        "description": "网易新闻 RSS",
    },
    {
        "name": "sina_rss",
        "type": "rss",
        "url": "https://rss.sina.com.cn/news/allnews/headline.xml",
        "parser": "feedparser",
        "description": "新浪新闻中心 RSS",
    },
    {
        "name": "huanqiu_rss",
        "type": "rss",
        "url": "https://rss.huanqiu.com/world/feed.xml",
        "parser": "feedparser",
        "description": "环球网国际新闻 RSS",
    },
    {
        "name": "ifeng_rss",
        "type": "rss",
        "url": "https://news.ifeng.com/rss/index.xml",
        "parser": "feedparser",
        "description": "凤凰网要闻 RSS",
    },
    {
        "name": "thepaper_rss",
        "type": "rss",
        "url": "https://www.thepaper.cn/feeds",
        "parser": "feedparser",
        "description": "澎湃新闻 RSS",
    },
    {
        "name": "china_news_rss",
        "type": "rss",
        "url": "http://www.china.com.cn/rss/rss.xml",
        "parser": "feedparser",
        "description": "中国网新闻 RSS",
    },
    {
        "name": "ce_cn_rss",
        "type": "rss",
        "url": "http://www.ce.cn/rss/",
        "parser": "feedparser",
        "description": "中国经济网新闻 RSS",
    },
    {
        "name": "huxiu_rss",
        "type": "rss",
        "url": "https://www.huxiu.com/rss/0.xml",
        "parser": "feedparser",
        "description": "虎嗅网 RSS",
    },
    {
        "name": "sspai_rss",
        "type": "rss",
        "url": "https://sspai.com/feed",
        "parser": "feedparser",
        "description": "少数派 RSS",
    },
    {
        "name": "ithome_rss",
        "type": "rss",
        "url": "https://www.ithome.com/rss/",
        "parser": "feedparser",
        "description": "IT之家 RSS",
    },
    {
        "name": "pingwest_rss",
        "type": "rss",
        "url": "https://www.pingwest.com/feed",
        "parser": "feedparser",
        "description": "品玩 RSS",
    },
    {
        "name": "ftchinese_rss",
        "type": "rss",
        "url": "https://www.ftchinese.com/rss/feed",
        "parser": "feedparser",
        "description": "FT中文网 RSS",
    },
    {
        "name": "jiemian_rss",
        "type": "rss",
        "url": "https://a.jiemian.com/index.php?m=article&a=rss",
        "parser": "feedparser",
        "description": "界面新闻 RSS",
    },
    {
        "name": "36kr_rss",
        "type": "rss",
        "url": "https://36kr.com/feed",
        "parser": "feedparser",
        "description": "36氪 RSS（替代 API）",
    },
    {
        "name": "cls_rss",
        "type": "rss",
        "url": "https://www.cls.cn/rss/telegraph",
        "parser": "feedparser",
        "description": "财联社电报 RSS（替代 API）",
    },
    {
        "name": "sohu_rss",
        "type": "rss",
        "url": "http://news.sohu.com/rss/",
        "parser": "feedparser",
        "description": "搜狐新闻 RSS",
    },
    # ────────── API 源 ──────────
    {
        "name": "36kr_api",
        "type": "api",
        "url": "https://gateway.36kr.com/api/missive/newsflash",
        "parser": "json_api",
        "fields_map": {
            "title": "title",
            "content": "summary",
            "url": "news_url",
            "published_at": "published_at",
        },
        "description": "36氪快讯 API",
    },
    {
        "name": "cls_api",
        "type": "api",
        "url": "https://www.cls.cn/nodeapi/updateTelegraphList",
        "parser": "json_api",
        "fields_map": {
            "title": "title",
            "content": "content",
            "url": "shareurl",
            "published_at": "ctime",
        },
        "description": "财联社电报 API",
    },
]
