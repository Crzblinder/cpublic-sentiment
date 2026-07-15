import random
from typing import Any

from faker import Faker

fake = Faker("zh_CN")
Faker.seed(42)
random.seed(42)

INDUSTRIES = [
    "互联网",
    "金融",
    "食品餐饮",
    "汽车",
    "医药",
    "房地产",
    "消费品",
    "能源化工",
    "物流运输",
    "教育培训",
]

REGIONS = [
    "北京",
    "上海",
    "广东",
    "浙江",
    "江苏",
    "四川",
    "湖北",
    "山东",
    "福建",
    "河南",
]

RISK_TYPES = {
    "产品质量": {
        "keywords": ["质量缺陷", "产品召回", "爆炸", "起火", "漏油"],
        "level_dist": ["中", "高", "高", "极高"],
    },
    "食品安全": {
        "keywords": ["过期原料", "添加剂", "吃出异物", "食物中毒"],
        "level_dist": ["高", "高", "极高", "中"],
    },
    "数据泄露": {
        "keywords": ["用户信息泄露", "数据库脱库", "黑客攻击", "隐私侵权"],
        "level_dist": ["中", "高", "高", "极高"],
    },
    "劳资纠纷": {
        "keywords": ["员工讨薪", "大规模裁员", "加班争议", "工会抗议"],
        "level_dist": ["中", "中", "高", "高"],
    },
    "高管丑闻": {
        "keywords": ["高管被调查", "创始人被捕", "性侵丑闻", "内幕交易"],
        "level_dist": ["高", "高", "极高", "中"],
    },
    "环保处罚": {
        "keywords": ["污染排放", "环保督察", "罚款", "停产整顿"],
        "level_dist": ["中", "中", "高", "高"],
    },
    "虚假宣传": {
        "keywords": ["夸大宣传", "广告违法", "误导消费者", "刷单炒信"],
        "level_dist": ["中", "中", "高", "高"],
    },
    "服务中断": {
        "keywords": ["系统宕机", "App崩溃", "支付故障", "无法登录"],
        "level_dist": ["中", "中", "高", "高"],
    },
    "金融违规": {
        "keywords": ["违规放贷", "资金挪用", "暴雷", "罚单"],
        "level_dist": ["高", "高", "极高", "中"],
    },
}

SCALE_DIST = ["大型", "大型", "中型", "中型", "中型", "小型"]


def _pick_risk_type_and_level() -> tuple[str, str]:
    risk_type = random.choice(list(RISK_TYPES.keys()))
    level = random.choice(RISK_TYPES[risk_type]["level_dist"])
    return risk_type, level


def generate_enterprises(n: int = 220) -> list[dict[str, Any]]:
    enterprises = []
    industry_templates = {
        "互联网": ["{name}科技", "{name}网络", "{name}信息"],
        "金融": ["{name}银行", "{name}保险", "{name}证券", "{name}基金"],
        "食品餐饮": ["{name}食品", "{name}餐饮", "{name}乳业"],
        "汽车": ["{name}汽车", "{name}新能源", "{name}出行"],
        "医药": ["{name}医药", "{name}生物科技", "{name}医疗"],
        "房地产": ["{name}地产", "{name}置业", "{name}物业"],
        "消费品": ["{name}家居", "{name}服饰", "{name}日化"],
        "能源化工": ["{name}能源", "{name}化工", "{name}电力"],
        "物流运输": ["{name}物流", "{name}快递", "{name}航运"],
        "教育培训": ["{name}教育", "{name}培训", "{name}在线"],
    }

    used_names = set()
    while len(enterprises) < n:
        industry = random.choice(INDUSTRIES)
        prefix = fake.company_prefix()
        name = random.choice(industry_templates[industry]).format(name=prefix)
        if name in used_names:
            continue
        used_names.add(name)

        scale = random.choice(SCALE_DIST)
        region = random.choice(REGIONS)
        tag_pool = [
            "上市公司",
            "独角兽",
            "国企",
            "外资",
            "民营",
            "集团化",
            "出海业务",
            "ToB",
            "ToC",
            "平台型",
        ]
        tags = random.sample(tag_pool, k=random.randint(2, 4))
        risk_type, _ = _pick_risk_type_and_level()
        risk_profile = {
            "primary_risk": risk_type,
            "history": random.choice(["无重大负面", "曾有1次危机", "曾有多次危机"]),
            "media_exposure": random.choice(["高", "中", "低"]),
            "social_sensitivity": random.choice(["高", "中", "低"]),
        }
        enterprises.append(
            {
                "name": name,
                "industry": industry,
                "scale": scale,
                "region": region,
                "business_tags": tags,
                "risk_profile": risk_profile,
            }
        )
    return enterprises


def generate_cases(n: int = 520) -> list[dict[str, Any]]:
    cases = []
    industries_cycle = INDUSTRIES * ((n // len(INDUSTRIES)) + 1)
    random.shuffle(industries_cycle)

    templates = {
        "产品质量": [
            "{company}{product}因{issue}被消费者大量投诉，部分用户晒出{evidence}。",
            "{company}宣布召回部分批次{product}，原因是{issue}。",
            "媒体曝光{company}{product}存在{issue}，引发行业关注。",
        ],
        "食品安全": [
            "有网友在{company}门店吃出{issue}，视频在社交平台迅速传播。",
            "{company}被曝使用{issue}，监管部门已介入调查。",
            "消费者反映在食用{company}产品后出现{issue}，舆论持续发酵。",
        ],
        "数据泄露": [
            "{company}疑似发生{issue}，大量用户信息在暗网流通。",
            "安全团队监测到{company}数据库存在{issue}，客户隐私面临风险。",
            "{company}App被曝{issue}，用户数据可被第三方获取。",
        ],
        "劳资纠纷": [
            "{company}员工在社交平台爆料{issue}，引发公众对劳动权益的讨论。",
            "{company}被曝{issue}，部分员工发起劳动仲裁。",
            "媒体报道{company}{issue}，涉及人数众多。",
        ],
        "高管丑闻": [
            "{company}{executive}涉嫌{issue}，已被相关部门带走调查。",
            "{company}创始人被曝{issue}，公司股价应声下跌。",
            "{company}高管卷入{issue}，董事会发表声明称将配合调查。",
        ],
        "环保处罚": [
            "{company}因{issue}被环保部门处罚，罚款金额超百万元。",
            "当地居民投诉{company}{issue}，要求停产整改。",
            "{company}工厂因{issue}被责令限产，产能受到影响。",
        ],
        "虚假宣传": [
            "{company}因{issue}被市场监管部门点名批评。",
            "消费者质疑{company}{issue}，认为广告存在误导。",
            "{company}直播带货被曝{issue}，主播承诺与实际不符。",
        ],
        "服务中断": [
            "{company}系统出现{issue}，大量用户无法正常使用服务。",
            "{company}App突发{issue}，官方致歉并承诺修复。",
            "因{issue}，{company}支付服务中断数小时，影响范围广泛。",
        ],
        "金融违规": [
            "{company}因{issue}收到监管罚单，被罚没金额巨大。",
            "{company}被曝{issue}，投资者信心受挫。",
            "监管部门通报{company}{issue}，要求限期整改。",
        ],
    }

    issue_pool = {
        "产品质量": ["电池过热", "刹车失灵", "屏幕碎裂", "材质不合格", "设计缺陷"],
        "食品安全": ["过期原料", "异物", "添加剂超标", "霉变", "农药残留"],
        "数据泄露": ["数据库未加密", "API漏洞", "内部人员泄露", "第三方接口被攻击"],
        "劳资纠纷": ["拖欠工资", "强制加班", "暴力裁员", "社保缴纳不足"],
        "高管丑闻": ["内幕交易", "职务侵占", "性骚扰", "行贿受贿"],
        "环保处罚": ["超标排放", "非法倾倒", "环评造假", "噪音扰民"],
        "虚假宣传": ["夸大功效", "刷单炒信", "虚假折扣", "伪造资质"],
        "服务中断": ["服务器宕机", "数据库故障", "网络攻击", "版本回滚失败"],
        "金融违规": ["违规放贷", "资金池运作", "信息披露不实", "挪用客户资金"],
    }

    product_pool = {
        "互联网": ["App", "云平台", "支付系统", "直播产品"],
        "金融": ["理财产品", "信贷业务", "保险条款", "基金销售"],
        "食品餐饮": ["预制菜", "奶茶", "烘焙产品", "婴幼儿食品"],
        "汽车": ["电动汽车", "动力电池", "自动驾驶系统", "制动系统"],
        "医药": ["疫苗", "处方药", "医疗器械", "保健品"],
        "房地产": ["商品房", "长租公寓", "物业管理", "商业地产"],
        "消费品": ["化妆品", "家电", "服装", "母婴用品"],
        "能源化工": ["成品油", "化工原料", "锂电池", "光伏组件"],
        "物流运输": ["快递服务", "冷链运输", "同城配送", "跨境物流"],
        "教育培训": ["在线课程", "少儿培训", "职业资格课", "留学服务"],
    }

    playbook_templates = {
        "产品质量": {
            "summary": "迅速启动产品召回，第三方检测，公布结果，补偿用户。",
            "steps": ["启动召回", "第三方检测", "公开道歉", "用户补偿"],
        },
        "食品安全": {
            "summary": "封存问题原料，配合监管，透明溯源，整改供应链。",
            "steps": ["封存原料", "配合调查", "透明溯源", "供应链整改"],
        },
        "数据泄露": {
            "summary": "封堵漏洞，通知用户，第三方审计，加强安全合规。",
            "steps": ["封堵漏洞", "通知用户", "第三方审计", "安全加固"],
        },
        "劳资纠纷": {
            "summary": "与员工代表沟通，依法补偿，完善劳动制度。",
            "steps": ["员工沟通", "依法补偿", "制度完善", "第三方调解"],
        },
        "高管丑闻": {
            "summary": "切割个人行为，配合司法，启动内部治理审查。",
            "steps": ["配合调查", "内部审查", "权力制衡", "对外说明"],
        },
        "环保处罚": {
            "summary": "立即整改，接受处罚，引入环保技改，公开整改进度。",
            "steps": ["停产整改", "环保技改", "公开进度", "第三方验收"],
        },
        "虚假宣传": {
            "summary": "下架违规广告，更正声明，接受处罚，建立广告审核机制。",
            "steps": ["下架广告", "更正声明", "接受处罚", "审核机制"],
        },
        "服务中断": {
            "summary": "快速恢复服务，事故复盘，用户补偿，架构优化。",
            "steps": ["恢复服务", "事故复盘", "用户补偿", "架构优化"],
        },
        "金融违规": {
            "summary": "暂停相关业务，配合监管，清退违规资金，合规整改。",
            "steps": ["暂停业务", "配合监管", "资金清退", "合规整改"],
        },
    }

    while len(cases) < n:
        industry = industries_cycle[len(cases)]
        risk_type, risk_level = _pick_risk_type_and_level()
        issue = random.choice(issue_pool[risk_type])
        product = random.choice(product_pool.get(industry, ["产品"]))
        company = fake.company_prefix()
        executive = random.choice(["董事长", "CEO", "创始人", "财务总监"])
        evidence = random.choice(["照片", "视频", "检测报告", "聊天记录"])

        template = random.choice(templates[risk_type])
        summary = template.format(
            company=company,
            product=product,
            issue=issue,
            evidence=evidence,
            executive=executive,
        )

        title = f"{company}{issue}引发{risk_type}舆情"
        playbook = playbook_templates[risk_type]
        cases.append(
            {
                "title": title,
                "summary": summary,
                "industry": industry,
                "risk_type": risk_type,
                "risk_level": risk_level,
                "source_url": fake.uri(),
                "tags": [risk_type, industry, issue],
                "governance_playbook": playbook,
            }
        )
    return cases
