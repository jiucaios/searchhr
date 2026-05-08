"""Prompts and schema definitions for company profile extraction."""

from __future__ import annotations

from typing import Any, Dict


COMPANY_PROFILE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "website": {"type": ["string", "null"]},
        "industry": {"type": ["string", "null"]},
        "business": {"type": ["string", "null"]},
        "business_model": {"type": ["string", "null"]},
        "company_stage": {"type": ["string", "null"]},
        "company_size": {"type": ["string", "null"]},
        "main_products": {"type": "array", "items": {"type": "string"}},
        "tech_stack": {"type": "array", "items": {"type": "string"}},
        "hiring_positions": {"type": "array", "items": {"type": "string"}},
        "candidate_preferences": {"type": "array", "items": {"type": "string"}},
        "risk_signals": {"type": "array", "items": {"type": "string"}},
        "missing_info": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": ["string", "null"]},
        "raw_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "claim": {"type": "string"},
                    "source_title": {"type": "string"},
                    "source_url": {"type": "string"},
                    "snippet": {"type": "string"},
                },
                "required": ["field", "claim", "source_title", "source_url", "snippet"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "company_name",
        "website",
        "industry",
        "business",
        "business_model",
        "company_stage",
        "company_size",
        "main_products",
        "tech_stack",
        "hiring_positions",
        "candidate_preferences",
        "risk_signals",
        "missing_info",
        "summary",
        "raw_evidence",
    ],
    "additionalProperties": False,
}


EXTRACTION_SYSTEM_PROMPT = """
你是一个用于招聘智能体的公司画像信息抽取器。

必须遵守：
1. 只输出一个稳定 JSON 对象，不要 Markdown，不要解释文字，不要代码块。
2. 只能基于用户提供的 evidence 抽取信息，不允许编造。
3. 公司规模、融资阶段、技术栈、风险信号必须有明确证据；没有证据就写 null 或 []。
4. 每个关键结论尽量在 raw_evidence 中保留来源，包括 field、claim、source_title、source_url、snippet。
5. 不确定或缺失的信息写入 missing_info。
6. candidate_preferences 可以基于岗位需求和证据做谨慎推断，但必须说明依据，不要泛泛而谈。
7. risk_signals 只记录负面新闻、裁员、诉讼、融资困难、业务收缩等证据明确的信息。
8. 最终 JSON 中除 source_url 外，所有可读文本尽量使用中文输出。
9. 如果 evidence 是英文，也要将 claim、snippet、summary、candidate_preferences 等字段翻译或概括为中文。
10. raw_evidence.source_title 可以保留原网页标题，但 claim 和 snippet 必须尽量中文化。
""".strip()


def build_extraction_user_prompt(
    company_name: str,
    company_website: str,
    job_description: str,
    evidence: str,
) -> Dict[str, Any]:
    return {
        "task": "extract_company_profile",
        "company_name": company_name,
        "company_website": company_website,
        "job_description": job_description,
        "json_schema": COMPANY_PROFILE_SCHEMA,
        "field_guidance": {
            "industry": "所属行业",
            "business": "主营业务、核心客户、业务介绍",
            "business_model": "ToB / ToC / SaaS / 平台 / 外包 / 硬件等",
            "company_stage": "初创 / 成长期 / 快速扩张 / 成熟期 / 上市公司 / 融资阶段",
            "company_size": "员工人数、团队规模、分支机构等",
            "main_products": "核心产品或服务",
            "tech_stack": "后端、前端、数据库、云服务、AI、大数据、推荐、搜索、高并发关键词",
            "hiring_positions": "当前招聘岗位、招聘城市、岗位级别",
            "candidate_preferences": "适合的人才背景、行业经验、技术经验、稳定性或冲劲偏好",
            "risk_signals": "裁员、负面舆情、融资困难、业务收缩、诉讼等",
        },
        "evidence": evidence,
    }
