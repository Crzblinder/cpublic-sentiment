import json
import logging
import random
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.data.generator import generate_all_data
from app.models import (
    Company,
    Job,
    MatchResult,
    Skill,
    SkillRelation,
    UserSkillProfile,
)

logger = logging.getLogger(__name__)

# 预定义依赖关系：source -> [target]
DEPENDENCY_RULES: dict[str, list[tuple[str, float]]] = {
    "Python": [
        ("FastAPI", 0.9),
        ("Django", 0.85),
        ("Flask", 0.8),
        ("Pandas", 0.75),
        ("PyTorch", 0.7),
    ],
    "Java": [("Spring Boot", 0.95), ("MySQL", 0.7)],
    # 占位项会在后续过滤掉
    "JavaScript": [
        ("React", 0.9),
        ("Vue.js", 0.85),
        ("Angular", 0.75),
        ("Node.js后端工程师", 0.0),
    ],
    "TypeScript": [("React", 0.85), ("Vue.js", 0.8), ("Angular", 0.8), ("NestJS", 0.75)],
    "Go": [("Gin", 0.85), ("Beego", 0.7), ("Echo", 0.75)],
    "C#": [("ASP.NET Core", 0.9), ("SQL Server", 0.75)],
    "PHP": [("Laravel", 0.85), ("ThinkPHP", 0.75)],
    "Ruby": [("Ruby on Rails", 0.9)],
    "Swift": [("iOS开发工程师", 0.0)],  # 过滤
    "Kotlin": [("Android开发工程师", 0.0)],  # 过滤
    "SQL": [("MySQL", 0.8), ("PostgreSQL", 0.75)],
}

# 预定义相似关系：两两互为相似
SIMILARITY_PAIRS: list[tuple[str, str, float]] = [
    ("Vue.js", "React", 0.9),
    ("MySQL", "PostgreSQL", 0.85),
    ("Django", "Flask", 0.85),
    ("PyTorch", "TensorFlow", 0.9),
    ("Spring Boot", "Django", 0.75),
    ("Redis", "MongoDB", 0.7),
    ("Docker", "Kubernetes", 0.8),
    ("React", "Angular", 0.8),
    ("Pandas", "NumPy", 0.85),
    ("Git", "GitHub Actions", 0.75),
]


def _json_list(value: list[Any]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _persist_skills(db: Session, skills: list[dict[str, Any]]) -> dict[str, Skill]:
    existing = {s.name: s for s in db.query(Skill).all()}
    skill_map = {}
    for item in skills:
        skill = existing.get(item["name"])
        if skill is None:
            skill = Skill(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                aliases=_json_list(item.get("aliases", [])),
                definition=item["definition"],
            )
            db.add(skill)
        skill_map[item["name"]] = skill
    db.commit()
    for skill in skill_map.values():
        db.refresh(skill)
    logger.info("Persisted %s skills", len(skill_map))
    return skill_map


def _persist_companies(db: Session, companies: list[dict[str, Any]]) -> dict[int, Company]:
    existing = {c.id: c for c in db.query(Company).all()}
    company_map = {}
    for item in companies:
        company = existing.get(item["id"])
        if company is None:
            company = Company(
                id=item["id"],
                name=item["name"],
                industry=item["industry"],
                size=item["size"],
                city=item["city"],
            )
            db.add(company)
        company_map[item["id"]] = company
    db.commit()
    for company in company_map.values():
        db.refresh(company)
    logger.info("Persisted %s companies", len(company_map))
    return company_map


def _persist_jobs(db: Session, jobs: list[dict[str, Any]]) -> list[Job]:
    existing_ids = {j.id for j in db.query(Job.id).all()}
    persisted = []
    for item in jobs:
        if item["id"] in existing_ids:
            continue
        job = Job(
            id=item["id"],
            title=item["title"],
            company_id=item["company_id"],
            city=item["city"],
            salary_min=item["salary_min"],
            salary_max=item["salary_max"],
            experience_level=item["experience_level"],
            education_level=item["education_level"],
            required_skills=_json_list(item.get("required_skills", [])),
            description=item["description"],
        )
        db.add(job)
        persisted.append(job)
    db.commit()
    for job in persisted:
        db.refresh(job)
    logger.info("Persisted %s jobs", len(persisted))
    return persisted


def _build_skill_relations(
    db: Session,
    skill_map: dict[str, Skill],
    jobs: list[dict[str, Any]],
) -> int:
    """基于预定义规则与共现频率构建技能关系。"""
    relations: list[SkillRelation] = []
    relation_keys: set[tuple[int, int, str]] = set()

    def _add_relation(
        source_name: str, target_name: str, relation_type: str, weight: float
    ) -> None:
        source = skill_map.get(source_name)
        target = skill_map.get(target_name)
        if source is None or target is None:
            return
        if source.id == target.id:
            return
        key = (source.id, target.id, relation_type)
        if key in relation_keys:
            return
        relation_keys.add(key)
        relations.append(
            SkillRelation(
                source_skill_id=source.id,
                target_skill_id=target.id,
                relation_type=relation_type,
                weight=round(weight, 3),
            )
        )

    # 依赖关系
    for source_name, targets in DEPENDENCY_RULES.items():
        for target_name, weight in targets:
            _add_relation(source_name, target_name, "dependency", weight)

    # 相似关系（双向）
    for a, b, weight in SIMILARITY_PAIRS:
        _add_relation(a, b, "similarity", weight)
        _add_relation(b, a, "similarity", weight)

    # 共现关系：统计 JD 中同时出现的技能对
    pair_counter: Counter[tuple[str, str]] = Counter()
    for job in jobs:
        skills = job.get("required_skills", [])
        for i in range(len(skills)):
            for j in range(i + 1, len(skills)):
                a, b = skills[i], skills[j]
                if a not in skill_map or b not in skill_map:
                    continue
                pair = tuple(sorted([a, b]))
                pair_counter[pair] += 1

    max_count = max(pair_counter.values()) if pair_counter else 1
    for (a, b), count in pair_counter.items():
        weight = min(1.0, count / max_count)
        if weight < 0.05:
            continue
        _add_relation(a, b, "co_occurrence", weight)
        _add_relation(b, a, "co_occurrence", weight)

    # 去重写入（按 source/target/type）
    existing = {
        (r.source_skill_id, r.target_skill_id, r.relation_type)
        for r in db.query(SkillRelation).all()
    }
    new_relations = [
        r
        for r in relations
        if (r.source_skill_id, r.target_skill_id, r.relation_type) not in existing
    ]
    db.bulk_save_objects(new_relations)
    db.commit()
    logger.info("Persisted %s skill relations", len(new_relations))
    return len(new_relations)


def _seed_demo_profiles(db: Session, skill_map: dict[str, Skill]) -> list[UserSkillProfile]:
    """写入若干示例求职者画像。"""
    if db.query(UserSkillProfile).first():
        return []

    demo_profiles = [
        {
            "name": "求职者A-全栈方向",
            "skills": ["JavaScript", "TypeScript", "React", "Python", "MySQL", "Git", "Docker"],
            "experience_level": "3-5年",
            "target_job_titles": ["全栈工程师", "前端开发工程师", "Python后端工程师"],
        },
        {
            "name": "求职者B-算法方向",
            "skills": ["Python", "PyTorch", "Pandas", "NumPy", "机器学习", "自然语言处理"],
            "experience_level": "1-3年",
            "target_job_titles": ["算法工程师", "机器学习工程师", "NLP工程师"],
        },
        {
            "name": "求职者C-后端方向",
            "skills": ["Java", "Spring Boot", "MySQL", "Redis", "Kafka", "Docker"],
            "experience_level": "5-10年",
            "target_job_titles": ["Java后端工程师", "高级Java后端工程师", "Java架构师"],
        },
    ]

    profiles = []
    for item in demo_profiles:
        profile = UserSkillProfile(
            name=item["name"],
            skills=_json_list(item["skills"]),
            experience_level=item["experience_level"],
            target_job_titles=_json_list(item["target_job_titles"]),
        )
        db.add(profile)
        profiles.append(profile)
    db.commit()
    for profile in profiles:
        db.refresh(profile)
    logger.info("Persisted %s demo user profiles", len(profiles))
    return profiles


def _seed_demo_matches(
    db: Session,
    profiles: list[UserSkillProfile],
    jobs: list[Job],
    skill_map: dict[str, Skill],
) -> int:
    """为示例画像生成简单匹配结果。"""
    if db.query(MatchResult).first():
        return 0

    matches = []
    for profile in profiles:
        profile_skills = set(json.loads(profile.skills))
        candidate_jobs = [j for j in jobs if j.title in json.loads(profile.target_job_titles)]
        if not candidate_jobs:
            candidate_jobs = random.sample(jobs, min(5, len(jobs)))
        for job in candidate_jobs[:3]:
            required = set(json.loads(job.required_skills))
            matched = list(profile_skills & required)
            missing = list(required - profile_skills)
            # 可迁移技能：通过相似关系查找
            transferable: list[str] = []
            for miss in missing:
                miss_skill = skill_map.get(miss)
                if miss_skill is None:
                    continue
                similar = db.query(SkillRelation).filter_by(
                    source_skill_id=miss_skill.id,
                    relation_type="similarity",
                ).all()
                for rel in similar:
                    target = db.query(Skill).get(rel.target_skill_id)
                    if target and target.name in profile_skills:
                        transferable.append(f"{target.name}->{miss_skill.name}")
                        break
            score = len(matched) / max(len(required), 1)
            matches.append(
                MatchResult(
                    user_profile_id=profile.id,
                    job_id=job.id,
                    match_score=round(score, 3),
                    matched_skills=_json_list(matched),
                    missing_skills=_json_list(missing),
                    transferable_skills=_json_list(transferable),
                    analysis_summary=(
                        f"匹配度 {score:.1%}，掌握 {len(matched)} 项核心技能，"
                        f"缺失 {len(missing)} 项。"
                    ),
                )
            )

    db.bulk_save_objects(matches)
    db.commit()
    logger.info("Persisted %s demo match results", len(matches))
    return len(matches)


def seed_database(
    db: Session,
    n_skills: int = 80,
    n_companies: int = 40,
    n_jobs: int = 250,
) -> dict[str, Any]:
    """生成新版结构化数据并持久化到数据库。"""
    logger.info("Generating seed data for skill-map and talent-matching engine...")
    data = generate_all_data(
        n_skills=n_skills,
        n_companies=n_companies,
        n_jobs=n_jobs,
    )

    skill_map = _persist_skills(db, data["skills"])
    _persist_companies(db, data["companies"])
    jobs = _persist_jobs(db, data["jobs"])
    relation_count = _build_skill_relations(db, skill_map, data["jobs"])
    profiles = _seed_demo_profiles(db, skill_map)
    match_count = _seed_demo_matches(db, profiles, jobs, skill_map)

    logger.info(
        "Seeded %s skills, %s companies, %s jobs, %s relations, %s profiles, %s matches",
        len(skill_map),
        len(data["companies"]),
        len(jobs),
        relation_count,
        len(profiles),
        match_count,
    )
    return {
        "skills": len(skill_map),
        "companies": len(data["companies"]),
        "jobs": len(jobs),
        "relations": relation_count,
        "profiles": len(profiles),
        "matches": match_count,
    }
