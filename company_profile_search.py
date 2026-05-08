"""Demo LangGraph tool for evidence-based company profile search."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, TypedDict, cast

import requests

# 修改日志配置部分 - Vercel 环境中只能写入 /tmp 目录
log_file_path = "/tmp/company_profile.log" if os.getenv("VERCEL") else "company_profile.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 加载.env文件
try:
    from dotenv import load_dotenv
    load_dotenv()  # 读取.env文件中的环境变量
except ImportError:
    pass  # 如果没有安装python-dotenv，使用系统环境变量
from langgraph.graph import END, START, StateGraph
from prompts import COMPANY_PROFILE_SCHEMA, EXTRACTION_SYSTEM_PROMPT, build_extraction_user_prompt


# 从环境变量读取配置，优先使用环境变量，其次使用默认值
DEMO_SERPER_API_KEY = os.getenv("SERPER_API_KEY", "52ff43c1b1c84ad2a3307929704e2cae80be2eef")
DEMO_DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-b4a5eb3d904c4e31876054ff8465102a")
DEMO_LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-flash")
MAX_TOTAL_SEARCHES = int(os.getenv("MAX_TOTAL_SEARCHES", "6"))
SERPER_TIMEOUT_SECONDS = int(os.getenv("SERPER_TIMEOUT_SECONDS", "15"))
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

PROFILE_FIELDS = [
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
]

DASHSCOPE_API_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")


class CompanyProfileState(TypedDict, total=False):
    company_name: str
    company_website: str
    job_description: str
    max_iterations: int
    iteration: int
    queries: List[str]
    searched_queries: List[str]
    search_results: List[Dict[str, Any]]
    evidence_summary: str
    company_profile: Dict[str, Any]
    missing_info: List[str]
    is_complete: bool
    errors: List[str]


def _empty_profile(company_name: str, company_website: str = "") -> Dict[str, Any]:
    return {
        "company_name": company_name,
        "website": company_website,
        "industry": None,
        "business": None,
        "business_model": None,
        "company_stage": None,
        "company_size": None,
        "main_products": [],
        "tech_stack": [],
        "hiring_positions": [],
        "candidate_preferences": [],
        "risk_signals": [],
        "summary": None,
        "raw_evidence": [],
        "missing_info": PROFILE_FIELDS.copy(),
    }


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _dedupe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for item in results:
        url = item.get("url") or item.get("link") or item.get("title")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped


def _normalize_profile(profile: Dict[str, Any], state: CompanyProfileState) -> Dict[str, Any]:
    normalized = _empty_profile(
        state["company_name"],
        state.get("company_website", ""),
    )
    normalized.update({key: profile.get(key) for key in normalized if key in profile})
    if profile.get("company_website") and not profile.get("website"):
        normalized["website"] = profile.get("company_website")
    if profile.get("products") and not profile.get("main_products"):
        normalized["main_products"] = profile.get("products")
    if profile.get("hiring_roles") and not profile.get("hiring_positions"):
        normalized["hiring_positions"] = profile.get("hiring_roles")

    for key in ["main_products", "tech_stack", "hiring_positions", "candidate_preferences", "risk_signals", "raw_evidence"]:
        if not isinstance(normalized.get(key), list):
            normalized[key] = []

    missing = profile.get("missing_info")
    normalized["missing_info"] = missing if isinstance(missing, list) else []
    return normalized


def _website_domain(website: str) -> str:
    cleaned = (website or "").replace("https://", "").replace("http://", "").strip("/")
    return cleaned.split("/")[0]


def _fetch_website_content(url: str, timeout: int = 10) -> Optional[Dict[str, str]]:
    """抓取网页内容"""
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        if response.status_code == 200:
            content = response.text
            
            # 提取标题
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ""
            
            # 提取meta描述
            desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', content, re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else ""
            
            # 提取正文文本（简单方式）
            text_content = re.sub(r'<[^>]+>', ' ', content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            return {
                "url": url,
                "title": title,
                "description": description,
                "content": text_content[:3000]  # 限制长度
            }
        else:
            logger.debug(f"[_fetch_website_content] 抓取失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        logger.debug(f"[_fetch_website_content] 抓取异常: {e}")
        return None


def _find_careers_page(website: str) -> Optional[str]:
    """查找公司官网的招聘页面"""
    if not website:
        return None
    
    base_url = website.rstrip("/")
    
    for path in CAREERS_PATHS:
        url = f"{base_url}{path}"
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                logger.info(f"[_find_careers_page] 找到招聘页面: {url}")
                return url
        except Exception:
            continue
    
    return None


def _filter_boss_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """过滤和清洗招聘平台的搜索结果（支持Boss直聘、智联招聘、前程无忧等）"""
    job_results = []
    
    # 招聘平台列表
    job_platforms = {
        "zhipin.com": "Boss直聘",
        "boss直聘": "Boss直聘",
        "zhaopin.com": "智联招聘",
        "51job.com": "前程无忧",
        "liepin.com": "猎聘",
        "lagou.com": "拉勾网",
        "jobui.com": "看准网",
        "linkedin.com": "LinkedIn",
        "joinbytedance.com": "公司官网招聘",
        "jobs.bytedance.com": "公司官网招聘",
    }
    
    for item in results:
        url = item.get("url", "").lower()
        title = item.get("title", "")
        content = item.get("content", "")
        
        # 判断是否来自招聘平台
        source = None
        for domain, platform_name in job_platforms.items():
            if domain in url or domain in title.lower() or domain in content.lower():
                source = platform_name
                break
        
        # 如果不是招聘平台，检查标题是否包含招聘相关关键词
        if not source:
            job_keywords = ["招聘", "job", "career", "职位", "岗位", "hiring"]
            if any(keyword in title.lower() for keyword in job_keywords) or \
               any(keyword in content.lower() for keyword in job_keywords):
                source = "招聘信息"
        
        if source:
            # 提取薪资
            salary_pattern = r"(\d+)[Kk]-(\d+)[Kk]"
            salary_match = re.search(salary_pattern, content)
            salary = f"{salary_match.group(1)}K-{salary_match.group(2)}K" if salary_match else ""
            
            # 提取地点
            location_pattern = r"(北京|上海|广州|深圳|杭州|成都|武汉|西安|南京|苏州)"
            location_match = re.search(location_pattern, content)
            location = location_match.group(1) if location_match else ""
            
            # 提取经验
            exp_pattern = r"(\d+)-(\d+)\s*年经验|(\d+)\s*年以上|应届|不限经验"
            exp_match = re.search(exp_pattern, content)
            experience = exp_match.group(0) if exp_match else ""
            
            # 提取学历
            edu_pattern = r"本科|硕士|大专|博士|高中"
            edu_match = re.search(edu_pattern, content)
            education = edu_match.group(0) if edu_match else ""
            
            # 构建清洗结果
            cleaned = {
                "title": title,
                "url": item.get("url", ""),
                "content": content,
                "salary": salary,
                "location": location,
                "experience": experience,
                "education": education,
                "source": source,
            }
            job_results.append(cleaned)
    
    logger.info(f"[_filter_boss_results] 过滤出 {len(job_results)} 条招聘平台结果")
    return job_results


def _llm_config() -> Dict[str, Optional[str]]:
    return {
        "api_key": DEMO_DASHSCOPE_API_KEY,
        "api_url": DASHSCOPE_API_URL,
        "model": DEMO_LLM_MODEL,
    }


def _generate_boss_search_query(company_name: str, job_description: str) -> str:
    """使用LLM生成Boss直聘搜索关键词"""
    llm = _llm_config()
    api_key = llm["api_key"]
    api_url = llm["api_url"]
    
    if not api_key:
        logger.warning("[_generate_boss_search_query] LLM API key未配置，使用默认搜索词")
        return f"{company_name} 招聘"
    
    try:
        prompt = f"""
        请帮我生成一个用于Boss直聘搜索的关键词。
        
        公司名称：{company_name}
        岗位需求：{job_description}
        
        请分析公司名称和岗位需求，生成一个简短的搜索关键词（不超过20个字符），用于在Boss直聘上搜索相关职位。
        
        输出格式：直接输出搜索关键词，不要加引号。
        """
        
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": llm["model"],
                "messages": [
                    {"role": "system", "content": "你是一个搜索关键词生成专家。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 50,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        
        search_query = payload.get("choices", [])[0].get("message", {}).get("content", "").strip()
        if not search_query:
            search_query = f"{company_name} 招聘"
        
        logger.info(f"[_generate_boss_search_query] 生成搜索关键词: {search_query}")
        return search_query
        
    except Exception as exc:
        logger.error(f"[_generate_boss_search_query] LLM调用失败: {exc}")
        return f"{company_name} 招聘"


def generate_queries_node(state: CompanyProfileState) -> CompanyProfileState:
    company_name = state["company_name"]
    website = state.get("company_website", "")
    missing = state.get("missing_info", [])
    iteration = state.get("iteration", 0)
    
    logger.info(f"[GenerateQueries] 第{iteration}轮 - 公司: {company_name}, 网站: {website}, 缺失字段: {missing}")

    domain = _website_domain(website)
    search_name = company_name
    base = [search_name]
    if website:
        base.append(f"site:{domain}")

    if iteration == 0:
        # 使用LLM生成Boss直聘搜索关键词
        job_description = state.get("job_description", "")
        boss_search_query = _generate_boss_search_query(search_name, job_description)
        
        queries = [
            " ".join(base + ["official website business products about"]),
            f"{search_name} careers jobs engineering tech stack",
            f"{search_name} funding news layoffs lawsuit risk",
            # 增加多个招聘平台搜索（不带site限定，类似智联招聘的获取方式）
            f"{boss_search_query} 招聘",
            f"{search_name} 招聘 岗位",
            f"{search_name} jobs careers",
        ]
    else:
        query_by_field = {
            "industry": f"{search_name} industry business overview",
            "business": f"{search_name} business products customers official website",
            "business_model": f"{search_name} business model customers pricing revenue",
            "company_stage": f"{search_name} funding stage investors IPO founded",
            "company_size": f"{search_name} employees headcount company size",
            "main_products": f"{search_name} products platform services solutions",
            "tech_stack": f"{search_name} engineering tech stack jobs",
            "hiring_positions": f"{search_name} careers jobs openings levels locations",
            "candidate_preferences": f"{search_name} job requirements culture values candidates",
            "risk_signals": f"{search_name} news risk layoffs lawsuit funding difficulty",
        }
        queries = [query_by_field[field] for field in missing if field in query_by_field]
        queries = queries[:4] or [f"{search_name} company profile latest news"]

    searched = set(state.get("searched_queries", []))
    remaining_searches = max(0, MAX_TOTAL_SEARCHES - len(state.get("searched_queries", [])))
    # 第一轮搜索时执行更多查询，确保招聘搜索被执行
    max_queries = 4 if iteration == 0 else 2
    state["queries"] = [query for query in queries if query not in searched][: min(max_queries, remaining_searches)]
    
    logger.info(f"[GenerateQueries] 生成查询: {state['queries']}")
    return state


def serper_search_node(state: CompanyProfileState) -> CompanyProfileState:
    api_key = DEMO_SERPER_API_KEY
    errors = state.get("errors", [])
    state["searched_queries"] = state.get("searched_queries", []) + state.get("queries", [])
    state["iteration"] = state.get("iteration", 0) + 1
    
    logger.info(f"[SerperSearch] 开始搜索 - 查询数: {len(state.get('queries', []))}, 迭代: {state['iteration']}")

    # 如果提供了官网，先抓取官网内容作为辅助（锦上添花）
    website = state.get("company_website", "")
    if website and state["iteration"] == 1:
        logger.info(f"[SerperSearch] 检测到官网，开始抓取内容: {website}")
        
        # 抓取主站内容
        main_content = _fetch_website_content(website)
        if main_content:
            state["search_results"] = state.get("search_results", []) + [{
                "query": "website_content",
                "title": main_content.get("title", ""),
                "url": main_content.get("url", ""),
                "content": main_content.get("description", "") + " " + main_content.get("content", "")[:1000],
                "score": 0,
            }]
            logger.info(f"[SerperSearch] 成功抓取官网内容")
        
        # 查找并抓取招聘页面
        careers_url = _find_careers_page(website)
        if careers_url:
            careers_content = _fetch_website_content(careers_url)
            if careers_content:
                state["search_results"] = state.get("search_results", []) + [{
                    "query": "careers_page",
                    "title": careers_content.get("title", ""),
                    "url": careers_content.get("url", ""),
                    "content": careers_content.get("description", "") + " " + careers_content.get("content", "")[:1000],
                    "score": 0,
                }]
                logger.info(f"[SerperSearch] 成功抓取招聘页面内容")
    elif not website:
        logger.info(f"[SerperSearch] 未提供官网，跳过官网抓取")

    if not api_key:
        errors.append("Serper API key is not configured; live web search was skipped.")
        state["errors"] = errors
        logger.warning("[SerperSearch] API key未配置，跳过搜索")
        return state

    results = state.get("search_results", [])
    start_time = time.time()
    max_retries = 2
    
    for query in state.get("queries", []):
        success = False
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"[SerperSearch] 执行查询 (第{attempt+1}次尝试): {query}")
                response = requests.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "q": query,
                    "num": 5,
                    "hl": "zh-cn",
                    "gl": "cn",
                    "sort_by": "date",  # 按时间排序
                    "tbm": "nws",       # 优先新闻内容
                },
                timeout=SERPER_TIMEOUT_SECONDS,
            )
                response.raise_for_status()
                payload = response.json()
                
                organic_results = payload.get("organic", [])
                logger.debug(f"[SerperSearch] 查询'{query}'返回 {len(organic_results)} 条结果")
                
                for item in organic_results:
                    results.append(
                        {
                            "query": query,
                            "title": item.get("title"),
                            "url": item.get("link"),
                            "content": item.get("snippet"),
                            "score": item.get("position"),
                        }
                    )
                knowledge_graph = payload.get("knowledgeGraph")
                if knowledge_graph:
                    company_name = state.get("company_name", "")
                    results.append(
                        {
                            "query": query,
                            "title": knowledge_graph.get("title") or company_name or "Knowledge Graph",
                            "url": knowledge_graph.get("website") or "",
                            "content": knowledge_graph.get("description") or "",
                            "score": 0,
                        }
                    )
                
                success = True
                break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    logger.warning(f"[SerperSearch] 查询'{query}'第{attempt+1}次失败，准备重试: {exc}")
                    time.sleep(1)
        
        if not success:
            errors.append(f"Serper search failed for query={query!r} after {max_retries} attempts: {last_error}")
            logger.error(f"[SerperSearch] 查询'{query}'失败 ({max_retries}次尝试): {last_error}")

    state["search_results"] = _dedupe_results(results)
    
    # 处理Boss直聘结果，提取结构化信息
    boss_results = _filter_boss_results(state["search_results"])
    if boss_results:
        logger.info(f"[SerperSearch] Boss直聘结果已处理 - {len(boss_results)}条")
        # 将处理后的Boss结果添加回state，供后续LLM匹配使用
        state["boss_results"] = boss_results
    
    state["errors"] = errors
    
    elapsed = time.time() - start_time
    logger.info(f"[SerperSearch] 搜索完成 - 总结果数: {len(state['search_results'])}, 耗时: {elapsed:.2f}秒")
    return state


def summarize_results_node(state: CompanyProfileState) -> CompanyProfileState:
    snippets = []
    
    # 普通搜索结果
    for idx, item in enumerate(state.get("search_results", [])[:30], start=1):
        snippets.append(
            "\n".join(
                [
                    f"[{idx}] title: {item.get('title') or ''}",
                    f"url: {item.get('url') or ''}",
                    f"query: {item.get('query') or ''}",
                    f"snippet: {(item.get('content') or '')[:900]}",
                ]
            )
        )
    
    # Boss直聘清洗后的结果
    boss_results = state.get("boss_results", [])
    if boss_results:
        snippets.append("\n--- Boss直聘招聘信息 ---")
        for idx, item in enumerate(boss_results, start=1):
            boss_info = [
                f"Boss职位{idx}: {item.get('title', '')}",
                f"薪资: {item.get('salary', '')}",
                f"地点: {item.get('location', '')}",
                f"经验: {item.get('experience', '')}",
                f"学历: {item.get('education', '')}",
                f"链接: {item.get('url', '')}",
                f"描述: {(item.get('content', '') or '')[:500]}",
            ]
            snippets.append("\n".join(boss_info))
    
    state["evidence_summary"] = "\n\n".join(snippets)
    return state


def _create_fallback_profile(state: CompanyProfileState) -> Dict[str, Any]:
    """基于搜索结果生成兜底画像"""
    profile = _empty_profile(
        state["company_name"],
        state.get("company_website", ""),
    )
    profile["raw_evidence"] = state.get("search_results", [])[:10]
    
    # 优先使用Boss直聘结果填充招聘岗位
    boss_results = state.get("boss_results", [])
    if boss_results:
        logger.info(f"[_create_fallback_profile] 使用Boss直聘结果填充招聘岗位: {len(boss_results)}条")
        for boss_item in boss_results[:5]:
            title = boss_item.get("title", "")
            if title and title not in profile["hiring_positions"]:
                profile["hiring_positions"].append(title)
    
    results = state.get("search_results", [])
    seen_products = set()
    seen_tech = set()
    
    for item in results[:10]:
        title = item.get("title", item.get("source", item.get("name", ""))).strip()
        content = (item.get("content", item.get("snippet", "")) or "").lower()
        url = item.get("url", item.get("link", ""))
        
        if not profile["industry"]:
            if any(keyword in content for keyword in ["ai", "人工智能", "大模型", "machine learning", "llm"]):
                profile["industry"] = "人工智能"
            elif any(keyword in content for keyword in ["云计算", "云服务", "cloud"]):
                profile["industry"] = "云计算"
            elif any(keyword in content for keyword in ["电商", "电子商务", "e-commerce", "online shopping"]):
                profile["industry"] = "电子商务"
            elif any(keyword in content for keyword in ["互联网", "internet", "technology", "tech"]):
                profile["industry"] = "互联网"
            elif any(keyword in content for keyword in ["金融", "银行", "revenue", "fintech"]):
                profile["industry"] = "金融科技"
            elif any(keyword in content for keyword in ["医疗", "健康", "health", "medical"]):
                profile["industry"] = "医疗健康"
            elif any(keyword in content for keyword in ["教育", "education"]):
                profile["industry"] = "教育"
            elif any(keyword in content for keyword in ["数据", "data", "analytics", "分析"]):
                profile["industry"] = "数据服务"
        
        if not profile["business"]:
            business_text = (item.get("content", item.get("snippet", "")) or "")[:300]
            if business_text and len(business_text) > 10:
                profile["business"] = business_text
        
        if not profile["company_stage"]:
            if any(keyword in content for keyword in ["上市", "ipo", "listed"]):
                profile["company_stage"] = "上市公司"
            elif any(keyword in content for keyword in ["融资", "funding", "估值", "billion", "investment"]):
                profile["company_stage"] = "融资阶段"
        
        if not profile["company_size"]:
            if any(keyword in content for keyword in ["500人", "千人", "thousand", "large"]):
                profile["company_size"] = "大型企业"
            elif any(keyword in content for keyword in ["100人", "medium"]):
                profile["company_size"] = "中型企业"
            else:
                profile["company_size"] = "大型企业"
        
        if title and len(profile["main_products"]) < 5 and title not in seen_products:
            if not any(keyword in title.lower() for keyword in ["招聘", "职位", "jobs", "careers", "job"]):
                profile["main_products"].append(title)
                seen_products.add(title)
        
        tech_keywords = ["Python", "Java", "Go", "React", "Vue", "AWS", "Kubernetes", "云原生", "大数据", "机器学习", "LLM", "AI", "computer vision", "data analytics", "fullstack", "backend", "frontend"]
        for keyword in tech_keywords:
            if keyword.lower() in content and keyword not in seen_tech:
                profile["tech_stack"].append(keyword)
                seen_tech.add(keyword)
                if len(profile["tech_stack"]) >= 5:
                    break
        
        if any(keyword in content for keyword in ["招聘", "职位", "jobs", "careers", "job opening"]):
            if title and len(profile["hiring_positions"]) < 5:
                profile["hiring_positions"].append(title)
    
    if not profile["industry"]:
        profile["industry"] = "互联网科技"
    if not profile["business"]:
        profile["business"] = f"{state['company_name']}是一家知名的科技公司，提供多元化的产品和服务。"
    if not profile["company_stage"]:
        profile["company_stage"] = "发展阶段"
    if not profile["company_size"]:
        profile["company_size"] = "大型企业"
    
    profile["summary"] = f"基于搜索结果整理的{state['company_name']}公司信息"
    return profile


def llm_extract_node(state: CompanyProfileState) -> CompanyProfileState:
    llm = _llm_config()
    api_key = llm["api_key"]
    api_url = llm.get("api_url") or DASHSCOPE_API_URL
    errors = state.get("errors", [])
    
    logger.info(f"[LLMExtract] 开始提取 - 公司: {state['company_name']}, 模型: {llm['model']}")

    if not api_key:
        profile = _create_fallback_profile(state)
        state["company_profile"] = profile
        errors.append("Qwen API key is not configured; using fallback profile.")
        state["errors"] = errors
        logger.warning("[LLMExtract] API key未配置，使用兜底画像")
        return state

    user_prompt = build_extraction_user_prompt(
        company_name=state["company_name"],
        company_website=state.get("company_website", ""),
        job_description=state.get("job_description", ""),
        evidence=state.get("evidence_summary", ""),
    )

    try:
        start_time = time.time()
        logger.debug(f"[LLMExtract] 调用LLM API - 超时时间: {LLM_TIMEOUT_SECONDS}秒")
        
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": llm["model"],
                "messages": [
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
                ],
                "temperature": 0,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"},
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        
        elapsed = time.time() - start_time
        logger.debug(f"[LLMExtract] LLM响应耗时: {elapsed:.2f}秒")
        
        if "choices" in payload and payload["choices"]:
            raw_text = payload["choices"][0]["message"]["content"] or "{}"
            state["company_profile"] = _normalize_profile(_extract_json(raw_text), state)
            logger.info(f"[LLMExtract] LLM提取成功")
        else:
            raise ValueError(f"Unexpected response format: {payload}")
            
    except Exception as exc:
        errors.append(f"Qwen extraction failed: {exc}")
        fallback = _create_fallback_profile(state)
        state["company_profile"] = fallback
        logger.error(f"[LLMExtract] LLM提取失败: {exc}, 使用兜底画像")

    state["errors"] = errors
    return state


def completeness_eval_node(state: CompanyProfileState) -> CompanyProfileState:
    profile = state.get("company_profile") or _empty_profile(
        state["company_name"],
        state.get("company_website", ""),
    )
    missing = []
    for field in PROFILE_FIELDS:
        value = profile.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)

    # Risk evidence is often absent for healthy companies; do not block completion on it
    # after at least two search rounds, but keep it visible for downstream users.
    if state.get("iteration", 0) >= 2 and "risk_signals" in missing:
        missing.remove("risk_signals")

    profile["missing_info"] = sorted(set(profile.get("missing_info", []) + missing))
    state["company_profile"] = profile
    state["missing_info"] = profile["missing_info"]
    state["is_complete"] = not missing
    return state


def loop_control_node(state: CompanyProfileState) -> str:
    if state.get("is_complete"):
        return "done"
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return "done"
    if len(state.get("searched_queries", [])) >= MAX_TOTAL_SEARCHES:
        return "done"
    if not state.get("missing_info"):
        return "done"
    return "continue"


def build_company_profile_graph():
    workflow = StateGraph(CompanyProfileState)
    workflow.add_node("generate_queries", generate_queries_node)
    workflow.add_node("serper_search", serper_search_node)
    workflow.add_node("summarize_results", summarize_results_node)
    workflow.add_node("llm_extract", llm_extract_node)
    workflow.add_node("completeness_eval", completeness_eval_node)

    workflow.add_edge(START, "generate_queries")
    workflow.add_edge("generate_queries", "serper_search")
    workflow.add_edge("serper_search", "summarize_results")
    workflow.add_edge("summarize_results", "llm_extract")
    workflow.add_edge("llm_extract", "completeness_eval")
    workflow.add_conditional_edges(
        "completeness_eval",
        loop_control_node,
        {
            "continue": "generate_queries",
            "done": END,
        },
    )
    return workflow.compile()


def _public_raw_evidence(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = []
    for item in profile.get("raw_evidence", []):
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "source": item.get("source") or item.get("source_title") or item.get("title") or item.get("field") or "搜索结果",
                "url": item.get("url") or item.get("source_url") or "",
                "content": item.get("content") or item.get("snippet") or item.get("claim") or "",
            }
        )
    return evidence


def _public_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "company_name": profile.get("company_name"),
        "website": profile.get("website"),
        "industry": profile.get("industry"),
        "business": profile.get("business"),
        "business_model": profile.get("business_model"),
        "company_stage": profile.get("company_stage"),
        "company_size": profile.get("company_size"),
        "main_products": profile.get("main_products", []),
        "tech_stack": profile.get("tech_stack", []),
        "hiring_positions": profile.get("hiring_positions", []),
        "candidate_preferences": profile.get("candidate_preferences", []),
        "risk_signals": profile.get("risk_signals", []),
        "missing_info": profile.get("missing_info", []),
        "summary": profile.get("summary"),
    }


def to_company_profile_api_response(result: Dict[str, Any]) -> Dict[str, Any]:
    profile = result.get("company_profile", {})
    raw_evidence = _public_raw_evidence(profile)
    errors = result.get("errors", [])
    has_core_info = any(
        [
            profile.get("industry"),
            profile.get("business"),
            profile.get("main_products"),
            profile.get("tech_stack"),
            profile.get("hiring_positions"),
        ]
    )

    if not raw_evidence:
        return {
            "status": "failed",
            "reason": "未找到有效公司信息",
            "missing_info": profile.get("missing_info") or result.get("missing_info", []),
            "raw_evidence": [],
            "errors": errors,
        }

    if has_core_info and not any("extraction failed" in error.lower() for error in errors):
        return {
            "status": "success",
            "company_profile": _public_profile(profile),
            "raw_evidence": raw_evidence,
        }

    return {
        "status": "failed",
        "reason": "未找到有效公司信息",
        "missing_info": profile.get("missing_info") or result.get("missing_info", []),
        "raw_evidence": raw_evidence,
        "errors": errors,
    }


def company_profile_search_tool(
    company_name: str,
    company_website: str | None = None,
    job_description: str | None = None,
    max_iterations: int = 2,
) -> dict:
    """Search and extract a structured company profile JSON.

    Args:
        company_name: Company name to research.
        company_website: Optional official website URL or domain.
        job_description: Optional JD text to infer hiring roles and candidate preferences.
        max_iterations: Hard cap for search/extract loops. Clamped to 1-3.

    Returns:
        A stable JSON-serializable dict containing company_profile, missing_info,
        raw evidence, iteration count, and non-fatal errors.
    """
    if not company_name or not company_name.strip():
        raise ValueError("company_name is required")

    capped_iterations = max(1, min(int(max_iterations), 3))
    app = build_company_profile_graph()
    final_state = app.invoke(
        {
            "company_name": company_name.strip(),
            "company_website": (company_website or "").strip(),
            "job_description": (job_description or "").strip(),
            "max_iterations": capped_iterations,
            "iteration": 0,
            "queries": [],
            "searched_queries": [],
            "search_results": [],
            "missing_info": [],
            "errors": [],
            "is_complete": False,
        }
    )

    profile = final_state.get("company_profile") or _empty_profile(
        company_name.strip(),
        (company_website or "").strip(),
    )
    return {
        "company_profile": profile,
        "missing_info": final_state.get("missing_info", profile.get("missing_info", [])),
        "is_complete": final_state.get("is_complete", False),
        "iterations": final_state.get("iteration", 0),
        "searched_queries": final_state.get("searched_queries", []),
        "errors": final_state.get("errors", []),
    }


def company_profile_search_api(
    company_name: str,
    company_website: Optional[str] = None,
    job_description: Optional[str] = None,
    max_iterations: int = 1,
) -> Dict[str, Any]:
    result = company_profile_search_tool(
        company_name=company_name,
        company_website=company_website,
        job_description=job_description,
        max_iterations=max_iterations,
    )
    return to_company_profile_api_response(result)


if __name__ == "__main__":
    demo = company_profile_search_tool(
        company_name="阿里云",
        company_website="https://www.aliyun.com",
        job_description="Python 后端工程师，AI Agent，搜索推荐，向量检索",
    )
    print(json.dumps(demo, ensure_ascii=False, indent=2))
