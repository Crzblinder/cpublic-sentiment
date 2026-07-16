# ruff: noqa: E501
"""
Agent 提示词注册表 —— 用于 A/B 测试与评估。

所有提示词文本已外置到 backend/app/prompts/{agent_name}/{variant}.txt，
本模块仅维护变体元数据注册表，template 字段通过 PromptLoader 懒加载。
如需修改提示词内容，请直接编辑对应的 .txt 文件。
"""

from app.prompts.loader import PromptLoader

_loader = PromptLoader()


def _lazy_template(agent_type: str, variant_file: str) -> str:
    """从外部文件懒加载提示词模板。"""
    return _loader.load(agent_type, variant_file)


# Registry of prompt variants for A/B testing
PROMPT_VARIANTS = [
    {"name": "scanner-zero-shot", "agent_type": "scanner", "technique": "Zero-Shot", "is_baseline": 1, "variant_file": "zero_shot"},
    {"name": "scanner-cot", "agent_type": "scanner", "technique": "CoT", "is_baseline": 0, "variant_file": "cot"},
    {"name": "scanner-few-shot", "agent_type": "scanner", "technique": "Few-Shot", "is_baseline": 0, "variant_file": "few_shot"},
    {"name": "matcher-zero-shot", "agent_type": "matcher", "technique": "Zero-Shot", "is_baseline": 1, "variant_file": "zero_shot"},
    {"name": "matcher-cot", "agent_type": "matcher", "technique": "CoT", "is_baseline": 0, "variant_file": "cot"},
    {"name": "matcher-few-shot", "agent_type": "matcher", "technique": "Few-Shot", "is_baseline": 0, "variant_file": "few_shot"},
    {"name": "predictor-zero-shot", "agent_type": "predictor", "technique": "Zero-Shot", "is_baseline": 1, "variant_file": "zero_shot"},
    {"name": "predictor-cot", "agent_type": "predictor", "technique": "CoT", "is_baseline": 0, "variant_file": "cot"},
    {"name": "predictor-few-shot", "agent_type": "predictor", "technique": "Few-Shot", "is_baseline": 0, "variant_file": "few_shot"},
    {"name": "governance-zero-shot", "agent_type": "governance", "technique": "Zero-Shot", "is_baseline": 1, "variant_file": "zero_shot"},
    {"name": "governance-cot", "agent_type": "governance", "technique": "CoT", "is_baseline": 0, "variant_file": "cot"},
    {"name": "governance-few-shot", "agent_type": "governance", "technique": "Few-Shot", "is_baseline": 0, "variant_file": "few_shot"},
    {"name": "governance-roleplay", "agent_type": "governance", "technique": "RolePlay", "is_baseline": 0, "variant_file": "roleplay"},
]


def get_template(variant_name: str) -> str:
    """根据变体名称（如 'scanner-zero-shot'）获取提示词模板文本。"""
    for v in PROMPT_VARIANTS:
        if v["name"] == variant_name:
            return _lazy_template(v["agent_type"], v["variant_file"])
    raise ValueError(f"Unknown prompt variant: {variant_name}")
