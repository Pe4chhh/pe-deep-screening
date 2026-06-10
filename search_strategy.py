"""Search planning and result governance for PE screening."""
from __future__ import annotations

import re
from urllib.parse import urlparse

_SPAM_DOMAINS = {
    # 爬虫聚合站 / 无意义快照站
    "dayinmao.com",
    # 低质量爬虫镜像
    "bjx.com", "china-10.com",
}

_SEARCH_TOPIC_LABELS = {
    "identity": "主体与主营业务",
    "operations": "产品、客户与持续经营",
    "scale": "营收、产能与规模",
    "ownership": "股权与交易障碍",
    "risk": "诉讼、处罚与合规",
    "market": "行业位置与协同价值",
    "official": "公司官网",
}

_SEARCH_COVERAGE_PATTERNS = {
    "identity": r"主营|业务|产品|生产|加工|制造|代工|OEM|ODM|公司简介",
    "operations": r"客户|供应商|供货|采购|订单|排产|产量|招标|合作",
    "scale": r"营收|收入|销售额|产能|产量|吨|员工|融资|亿元|万元",
    "ownership": (
        r"股东.{0,30}(?:持股|出资|自然人|有限|公司)|"
        r"(?:实际控制人|法定代表人|最终受益人).{0,30}[\u4e00-\u9fff]{2,}|"
        r"(?:控股股东|控股公司|母公司|集团体系|上市公司|外资企业|国有企业|国企)|"
        r"(?:股权结构|股权变更|企业类型|统一社会信用代码)"
    ),
    "risk": r"行政处罚|处罚|诉讼|失信|被执行|经营异常|监管|召回|通报",
    "market": r"市场|行业|竞争|份额|领先|排名|品牌|渠道|协同",
}

_WECHAT_MAX_ARTICLES = 6

_WECHAT_MAX_FULLTEXT = 3

_VERIFIED_RESULTS_PER_QUERY = 5

_PER_QUERY_PROVIDER_LIMITS = {
    "Tavily": 3,
}

_ADMINISTRATIVE_PREFIXES = (
    "苏州工业园区",
    "上海市",
    "北京市",
    "天津市",
    "重庆市",
    "江苏省",
    "浙江省",
    "广东省",
    "山东省",
    "河南省",
    "河北省",
    "湖南省",
    "湖北省",
    "安徽省",
    "福建省",
    "四川省",
    "江西省",
    "辽宁省",
    "吉林省",
    "黑龙江省",
    "陕西省",
    "山西省",
    "云南省",
    "贵州省",
    "甘肃省",
    "青海省",
    "海南省",
    "台湾省",
    "内蒙古自治区",
    "广西壮族自治区",
    "西藏自治区",
    "宁夏回族自治区",
    "新疆维吾尔自治区",
    "香港特别行政区",
    "澳门特别行政区",
    "上海",
    "北京",
    "天津",
    "重庆",
    "江苏",
    "浙江",
    "广东",
    "山东",
    "河南",
    "河北",
    "湖南",
    "湖北",
    "安徽",
    "福建",
    "四川",
    "江西",
    "辽宁",
    "吉林",
    "陕西",
    "山西",
    "云南",
    "贵州",
    "甘肃",
    "青海",
    "海南",
    "苏州",
    "南京",
    "无锡",
    "常州",
    "南通",
    "扬州",
    "镇江",
    "泰州",
    "徐州",
    "盐城",
    "淮安",
    "宿迁",
    "连云港",
)

_GENERIC_ALIAS_STOPWORDS = {
    "工业园区",
    "开发区",
    "高新区",
    "经开区",
    "园区",
    "食品",
    "饮料",
    "科技",
    "实业",
    "贸易",
    "商贸",
    "农业",
    "生物",
    "供应链",
    "管理",
    "有限",
    "公司",
    "集团",
    "股份",
    "唯亭",
    "胜浦",
}


def _normalize_company_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _strip_company_suffix(value: str) -> str:
    return re.sub(r"(有限责任公司|股份有限公司|集团有限公司|控股有限公司|有限公司|股份公司)$", "", value)


def _strip_leading_administrative_prefix(value: str) -> str:
    current = value
    changed = True
    while changed:
        changed = False
        for prefix in sorted(_ADMINISTRATIVE_PREFIXES, key=len, reverse=True):
            if current.startswith(prefix) and len(current) - len(prefix) >= 4:
                current = current[len(prefix):]
                changed = True
                break
    return current


def _company_core_aliases(company_name: str, short_name: str = "") -> list[str]:
    names = []
    for raw in (company_name, short_name):
        normalized = _normalize_company_text(raw)
        if not normalized:
            continue
        trimmed = _strip_company_suffix(normalized)
        core = _strip_leading_administrative_prefix(trimmed)
        names.extend([normalized, trimmed, core])
    return list(dict.fromkeys(alias for alias in names if len(alias) >= 4 and alias not in _GENERIC_ALIAS_STOPWORDS))


def _discriminative_chunks(alias: str) -> list[str]:
    chunks = []
    for size in (4, 3):
        for index in range(max(0, len(alias) - size + 1)):
            chunk = alias[index:index + size]
            if chunk in _GENERIC_ALIAS_STOPWORDS:
                continue
            if any(stop in chunk and len(chunk) <= len(stop) + 1 for stop in _GENERIC_ALIAS_STOPWORDS):
                continue
            chunks.append(chunk)
    return list(dict.fromkeys(chunks))


def _has_company_reference(text: str, company_name: str, short_name: str = "") -> bool:
    normalized = _normalize_company_text(text)
    if not normalized:
        return False
    aliases = _company_core_aliases(company_name, short_name)
    if not aliases:
        return True
    if any(alias in normalized for alias in aliases):
        return True
    core_aliases = [
        alias for alias in aliases
        if alias not in {company_name, short_name} and alias == _strip_leading_administrative_prefix(alias)
    ]
    return any(chunk in normalized for alias in core_aliases for chunk in _discriminative_chunks(alias))

def _dedupe_search_plan(plan: list[dict]) -> list[dict]:
    """Keep the first query for each unique search string and drop empties."""
    deduped = []
    seen = set()
    for item in plan:
        query = str(item.get("query", "")).strip()
        if not query or query in seen:
            continue
        seen.add(query)
        deduped.append({**item, "query": query})
    return deduped

def _build_screening_search_plan(
    company_name: str, short_name: str = "", industry: str = "", website: str = ""
) -> list[dict]:
    """Define a repeatable first-pass diligence search.

    Identity and ownership queries are skipped — QCC MCP provides better 工商 data.
    Web search focuses on what QCC can't provide: operations, scale, risk articles, market.
    """
    name = company_name.strip()
    plan = [
        {"topic": "identity", "query": f"{name} 官网 公司简介 主营业务 产品 生产"},
        {"topic": "operations", "query": f"{name} 客户 供应商 供货 订单 合作"},
        {"topic": "scale", "query": f"{name} 营收 销售额 产能 产量 员工 招聘"},
        {"topic": "risk", "query": f"{name} 行政处罚 诉讼 失信 被执行 经营异常"},
        {"topic": "market", "query": f"{name} 行业 竞争 渠道 市场地位"},
    ]
    if industry:
        plan.append({"topic": "market", "query": f"{name} {industry} OEM ODM 代工"})
        # 独立行业查询：不绑公司名，获取行业竞争格局
        plan.append({"topic": "industry", "query": f"{industry} 市场规模 竞争格局 头部企业 2025"})
    if website:
        plan.append({"topic": "official", "query": f"site:{website} {name} 主营 产品"})
    return _dedupe_search_plan(plan)

def _build_baidu_search_plan(company_name: str, short_name: str = "") -> list[dict]:
    name = company_name.strip()
    plan = [
        {"topic": "operations", "query": f"{name} 客户 供货 产量 新闻"},
        {"topic": "risk", "query": f"{name} 处罚 诉讼 经营异常"},
    ]
    return _dedupe_search_plan(plan)

def _build_quick_search_plan(company_name: str) -> list[dict]:
    """Short version of the same diligence structure used by batch screening."""
    name = company_name.strip()
    return _dedupe_search_plan([
        {"topic": "identity", "query": f"{name} 官网 主营业务 产品 生产"},
        {"topic": "operations", "query": f"{name} 客户 供应商 供货 订单"},
        {"topic": "scale", "query": f"{name} 营收 产能 规模"},
        {"topic": "ownership", "query": f"{name} 股东 股权 工商"},
        {"topic": "risk", "query": f"{name} 处罚 诉讼 经营异常"},
    ])

def _assess_search_coverage(text: str) -> dict[str, bool]:
    normalized = str(text or "")
    return {
        topic: bool(re.search(pattern, normalized, re.IGNORECASE))
        for topic, pattern in _SEARCH_COVERAGE_PATTERNS.items()
    }

def _build_gap_search_plan(company_name: str, coverage: dict[str, bool]) -> list[dict]:
    """Run one targeted follow-up for each uncovered diligence topic."""
    gap_queries = {
        "identity": f"{company_name} 官网 主营 产品 生产 公司简介",
        "operations": f"{company_name} 客户 供应商 供货 订单 合作",
        "scale": f"{company_name} 营收 销售额 产能 产量 员工 招聘",
        "ownership": f"{company_name} 股东 实际控制人 法定代表人 企业类型 母公司",
        "risk": f"{company_name} 行政处罚 诉讼 失信 被执行 经营异常",
        "market": f"{company_name} 行业 地位 客户 渠道 品牌 竞争",
    }
    plan = [
        {"topic": topic, "query": query}
        for topic, query in gap_queries.items()
        if not coverage.get(topic, False)
    ]
    if not coverage.get("ownership", False):
        plan.append({
            "topic": "ownership",
            "query": f"{company_name} 控股 股权变更 集团 上市公司 外资 国企",
        })
    return _dedupe_search_plan(plan)

def _coverage_text_from_results(*groups: dict[str, list]) -> str:
    return "\n".join(
        f"{item.get('title', '')} {item.get('content', '')}"
        for grouped in groups
        for results in grouped.values()
        for item in results
        if item.get("type", "result") == "result"
    )

def _wechat_supplement_queries(company_name: str, short_name: str, industry: str, base_text: str) -> list[str]:
    """Gap-driven WeChat search for operating evidence across the missing dimensions."""
    text = str(base_text or "")
    coverage = _assess_search_coverage(text)
    queries = []

    def add(query: str) -> None:
        query = query.strip()
        if query and query not in queries:
            queries.append(query)

    if not coverage.get("identity", False):
        add(f"{company_name} 主营 产品 生产")
    if not coverage.get("operations", False):
        add(f"{company_name} 客户 供应 合作")
    if not coverage.get("scale", False):
        add(f"{company_name} 营收 产能 规模")
    if industry and not coverage.get("market", False):
        add(f"{company_name} {industry} 市场 竞争")
    return queries[:4]

def _dedupe_wechat_results(results: list[dict], limit: int = _WECHAT_MAX_ARTICLES) -> list[dict]:
    selected = []
    seen = set()
    for article in results:
        url = str(article.get("url", "")).strip()
        title = re.sub(r"\s+", "", str(article.get("title", "")).strip().lower())
        account = re.sub(r"\s+", "", str(article.get("account", "")).strip().lower())
        key = url or f"{title}|{account}"
        if not key or key in seen:
            continue
        seen.add(key)
        selected.append(article)
        if len(selected) >= limit:
            break
    return selected

def _company_reference_aliases(company_name: str, short_name: str = "") -> list[str]:
    """Accept the legal name and deterministic abbreviations used in published sources."""
    return _company_core_aliases(company_name, short_name)

def _search_result_quality_score(item: dict, company_name: str, short_name: str = "") -> int:
    """Rank verified results by source credibility and diligence usefulness."""
    title = str(item.get("title", ""))
    content = str(item.get("content", ""))
    url = str(item.get("url", ""))
    text = re.sub(r"\s+", "", f"{title} {content}")
    domain = (urlparse(url).hostname or "").lower()
    score = 0

    if _has_company_reference(text, company_name, short_name):
        score += 8
    if domain.endswith(".gov.cn") or "court.gov.cn" in domain:
        score += 8
    if "mp.weixin.qq.com" in domain:
        score += 7
    if any(site in domain for site in ("qcc.com", "tianyancha.com", "aiqicha.baidu.com", "xiniudata.com")):
        score += 6
    if any(site in domain for site in ("36kr.com", "thepaper.cn", "stcn.com", "eastmoney.com", "sina.com.cn")):
        score += 4
    if any(site in domain for site in ("11467.com", "huangye88.com", "shunqi.com", "mingluji.com")):
        score -= 5

    score += sum(
        3 for term in ("主营", "产品", "生产", "客户", "供应商", "供货", "订单", "产能", "营收", "股东", "处罚")
        if term in text
    )
    score += sum(1 for term in ("合作", "工厂", "招聘", "员工", "渠道", "市场", "品牌", "行业") if term in text)
    score -= sum(3 for term in ("黄页", "号码", "电话", "地址", "查询", "名录") if term in text)
    return score

def _filter_relevant_wechat_results(
    results: list[dict], company_name: str, short_name: str = "", limit: int = _WECHAT_MAX_ARTICLES
) -> list[dict]:
    """Keep company-specific articles, prioritizing operating evidence over announcements."""
    candidates = []
    for article in results:
        text = re.sub(
            r"\s+", "", " ".join(str(article.get(key, "")) for key in ("title", "digest", "account"))
        )
        if not _has_company_reference(text, company_name, short_name):
            continue
        clean_text = re.sub(r"<[^>]+>", "", text)
        score = sum(
            3 for term in ("主营", "产品", "生产", "客户", "供应", "订单", "代工", "OEM", "ODM")
            if term in clean_text
        ) + sum(
            2 for term in ("调研", "平台", "冷链", "配送", "预制菜", "渠道", "合作", "品牌",
                           "简介", "产能", "工厂", "食品", "加工", "制造", "研发", "专利", "技术")
            if term in clean_text
        ) + sum(
            1 for term in ("招聘", "员工", "团队", "规模", "融资", "投资", "行业", "市场",
                           "增长", "出口", "认证", "质量", "检测", "标准")
            if term in clean_text
        )
        # Only penalize clearly ceremonial posts
        score -= sum(2 for term in ("开工大吉", "团圆", "年会") if term in clean_text)
        candidates.append((score, len(candidates), article))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [article for _, _, article in candidates[:limit]]

def _filter_verified_search_results(
    results: list[dict], company_name: str, short_name: str = "", seen_urls: set[str] | None = None
) -> list[dict]:
    """Exclude unrelated or duplicate web results before analysis and reference rendering."""
    seen = seen_urls if seen_urls is not None else set()
    selected = []
    accepted_result = False
    for item in results:
        if item.get("type", "result") != "result":
            continue
        text = re.sub(r"\s+", "", f"{item.get('title', '')} {item.get('content', '')}")
        if not _has_company_reference(text, company_name, short_name):
            continue
        url = str(item.get("url", "")).strip()
        # Skip known spam/scraper domains
        if any(d in url.lower() for d in _SPAM_DOMAINS):
            continue
        key = url.rstrip("/").lower()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        selected.append((_search_result_quality_score(item, company_name, short_name), len(selected), item))
        accepted_result = True
    if accepted_result:
        selected.sort(key=lambda row: (-row[0], row[1]))
        selected_items = []
        provider_counts: dict[str, int] = {}
        for _, _, item in selected:
            provider = str(item.get("provider", "") or "")
            limit = _PER_QUERY_PROVIDER_LIMITS.get(provider)
            if limit is not None and provider_counts.get(provider, 0) >= limit:
                continue
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            selected_items.append(item)
            if len(selected_items) >= _VERIFIED_RESULTS_PER_QUERY:
                break
        answer_items = [
            item for item in results
            if item.get("type") == "answer"
            and _has_company_reference(item.get("content", ""), company_name, short_name)
        ]
        selected = answer_items + selected_items
    return selected

def _govern_search_result_groups(
    grouped_results: dict[str, list], company_name: str, short_name: str = "", seen_urls: set[str] | None = None
) -> dict[str, list]:
    seen = seen_urls if seen_urls is not None else set()
    return {
        query: _filter_verified_search_results(results, company_name, short_name, seen)
        for query, results in grouped_results.items()
    }
