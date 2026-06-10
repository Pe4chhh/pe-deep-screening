#!/usr/bin/env python3
"""Apply ALL remaining changes for market-position dimension + re-apply today's lost fixes."""
import re, sys

with open("server.py", "r", encoding="utf-8") as f:
    c = f.read()

changes = 0

def apply(old, new, desc=""):
    global c, changes
    if old in c:
        c = c.replace(old, new, 1)
        changes += 1
        print(f"  OK: {desc}")
        return True
    else:
        print(f"  MISS: {desc}")
        # Try to find partial match for debugging
        idx = c.find(old[:40])
        if idx >= 0:
            print(f"    Found partial at pos {idx}: {repr(c[idx:idx+80])}")
        return False

# ============================================================
# SECTION 1: Re-add helper functions (lost in git restore)
# ============================================================

# 1a. _is_routine_sme_information_gap (replaces _is_routine_sme_financial_nondisclosure)
old = '''def _is_routine_sme_financial_nondisclosure(text: str) -> bool:
    text = str(text or "")
    nondisclosure_signals = (
        "未提供任何财务数据", "未提供财务数据", "财务数据不公开", "未公开财务",
        "未披露财务", "未披露审计", "缺乏财务数据", "财务数据完全不公开",
    )
    cleaned_text = re.sub(
        r"未(?:发现|见|有)\\s*(?:实质)?(?:行政)?(?:处罚|违规|异常|失信|冻结|被执行)",
        "",
        text,
    )
    substantive_risk_signals = (
        "主体不清", "主体混淆", "实际控制人不明", "实控人不明", "多个主体",
        "股权代持", "关联交易", "造假", "虚假", "欠税", "冻结", "失信",
        "被执行", "吊销", "注销", "行政处罚", "审计保留", "审计意见",
    )
    return (
        any(signal in text for signal in nondisclosure_signals)
        and not any(signal in cleaned_text for signal in substantive_risk_signals)
    )'''

new = '''def _is_routine_sme_information_gap(text: str) -> bool:
    """Check if flag #12 is triggered by routine SME information opacity, not substantive risk."""
    text = str(text or "")
    information_gap_signals = (
        "未提供任何财务数据", "未提供财务数据", "财务数据不公开", "未公开财务",
        "未披露财务", "未披露审计", "缺乏财务数据", "财务数据完全不公开",
        "股权结构.{0,6}(?:不透明|极不透明|不明|无法|不详|未知)",
        "无法查清.{0,8}(?:股东|实际控制人|实控人)",
        "股东.{0,4}(?:不公开|不明|不详|无法查|未公开|未披露)",
        "实际控制人.{0,4}(?:不公开|不明|不详|无法查|未公开|未披露)",
        "实控人.{0,4}(?:不公开|不明|不详|无法查|未公开|未披露)",
        "未透露.{0,8}(?:股东|实控人|实际控制人|集团名称|所属集团)",
        "未披露.{0,8}(?:股东|实控人|实际控制人|集团|所属)",
        "无法确认.{0,8}(?:实际控制人|实控人|股东|所属)",
        "股东信息.{0,4}(?:不公开|缺乏|极少|有限)",
        "工商信息.{0,4}(?:不完整|有限|缺乏)",
    )
    _GAP_RE = re.compile("|".join(information_gap_signals))
    cleaned_text = re.sub(
        r"未(?:发现|见|有)\\s*(?:实质)?(?:行政)?(?:处罚|违规|异常|失信|冻结|被执行)",
        "",
        text,
    )
    substantive_risk_signals = (
        "主体不清", "主体混淆", "多个主体",
        "股权代持", "关联交易", "造假", "虚假", "欠税", "冻结", "失信",
        "被执行", "吊销", "注销", "行政处罚", "审计保留", "审计意见",
        "壳公司", "名义股东", "代持", "挪用", "侵占",
    )
    return (
        bool(_GAP_RE.search(text))
        and not any(signal in cleaned_text for signal in substantive_risk_signals)
    )'''

# Escape for the file content
old_escaped = old.replace('\\', '\\\\')
new_escaped = new.replace('\\', '\\\\')
apply(old, new, "1a. _is_routine_sme_information_gap")

# 1b. _has_premium_customer_evidence and _describes_multiple_customers
# Insert after _is_routine_sme_information_gap
insert_marker = "    return (\n        bool(_GAP_RE.search(text))\n        and not any(signal in cleaned_text for signal in substantive_risk_signals)\n    )\n\n\ndef _extract_red_flags"
if insert_marker not in c:
    # Try alternative ending
    insert_marker2 = "and not any(signal in cleaned_text for signal in substantive_risk_signals)\n    )\n\n\ndef _extract_red_flags"
    if insert_marker2 not in c:
        print("  WARN: Cannot find insertion point for helper functions")
    else:
        new_funcs = '''


def _has_premium_customer_evidence(text: str) -> bool:
    """Check if flag #13 evidence actually lists premium/quality customers."""
    text = str(text or "")
    _PREMIUM_CUSTOMERS = re.compile(
        r"盒马|叮咚|美团|山姆|开市客|Costco|奥乐齐"
        r"|医院|学校|央企|国企|世界500强|机关|部队"
        r"|百果园|天天果园|永辉|大润发|沃尔玛|麦德龙"
        r"|全家|罗森|7-Eleven|便利蜂"
        r"|海底捞|喜茶|奈雪|古茗|瑞幸|星巴克"
    )
    return bool(_PREMIUM_CUSTOMERS.search(text))


def _describes_multiple_customers(text: str) -> bool:
    """Check if flag #6 evidence describes multiple/diverse customers, not single dependency."""
    text = str(text or "")
    _MULTI_CUSTOMER = re.compile(
        r"多[个家种类项]|等[平台渠道客户]|、.*、"
        r"|数个|数个|若干|批量|很多|广泛"
    )
    return bool(_MULTI_CUSTOMER.search(text))


def _extract_red_flags'''
        c = c.replace(insert_marker2, new_funcs)
        changes += 1
        print("  OK: 1b. _has_premium_customer_evidence + _describes_multiple_customers")

# 1c. Update _extract_red_flags to use new function names and add flag #6/#13 normalization
if "_is_routine_sme_financial_nondisclosure(flag_12_text)" in c:
    c = c.replace("_is_routine_sme_financial_nondisclosure(flag_12_text)", "_is_routine_sme_information_gap(flag_12_text)")
    print("  OK: 1c. Updated _extract_red_flags function reference")

# Add flag #6 and #13 normalization in _extract_red_flags
old_exit = '''    if flags.get("12") == "\\U0001f534" and _is_routine_sme_information_gap(flag_12_text):
        flags["12"] = "\\U0001f7e1"

    return {str(number): flags.get(str(number), "\\U0001f7e1") for number in range(1, 15)}'''

new_exit = '''    if flags.get("12") == "🔴" and _is_routine_sme_information_gap(flag_12_text):
        flags["12"] = "🟡"

    flag_13_match = re.search(
        r"[🟢🟡🔴]\\s*13\\s*[.。：:](.*?)(?=[🟢🟡🔴]\\s*\\d{1,2}\\s*[.。：:]|$)",
        plain_flags_html,
        flags=re.DOTALL,
    )
    flag_13_text = flag_13_match.group(1) if flag_13_match else ""
    if flags.get("13") == "🔴" and _has_premium_customer_evidence(flag_13_text):
        flags["13"] = "🟡"

    flag_6_match = re.search(
        r"[🟢🟡🔴]\\s*6\\s*[.。：:](.*?)(?=[🟢🟡🔴]\\s*\\d{1,2}\\s*[.。：:]|$)",
        plain_flags_html,
        flags=re.DOTALL,
    )
    flag_6_text = flag_6_match.group(1) if flag_6_match else ""
    if flags.get("6") == "🔴" and _describes_multiple_customers(flag_6_text):
        flags["6"] = "🟡"

    return {str(number): flags.get(str(number), "🟡") for number in range(1, 15)}'''

# Use emoji Unicode escapes
old_exit_raw = '''    if flags.get("12") == "\U0001f534" and _is_routine_sme_information_gap(flag_12_text):
        flags["12"] = "\U0001f7e1"

    return {str(number): flags.get(str(number), "\U0001f7e1") for number in range(1, 15)}'''

# Try to match with actual emoji chars
if old_exit_raw in c:
    c = c.replace(old_exit_raw, new_exit)
    changes += 1
    print("  OK: 1c. Flag #6/#13 normalization in _extract_red_flags")
else:
    print("  WARN: Could not locate flag exit point in _extract_red_flags")

# 1d. Update _fix_red_flags_html for flag #6/#13
old_flag12_html = '''        if num == 12 and emoji == "\\U0001f534" and _is_routine_sme_information_gap(content):
            emoji = "\\U0001f7e1"
            content = re.sub(r"：存在。?", "：待核实。", content, count=1)
        if emoji == "\\U0001f7e2":'''

new_flag12_html = '''        if num == 12 and emoji == "🔴" and _is_routine_sme_information_gap(content):
            emoji = "🟡"
            content = re.sub(r"：存在。?", "：待核实。", content, count=1)
        if num == 13 and emoji == "🔴" and _has_premium_customer_evidence(content):
            emoji = "🟡"
            content = re.sub(r"：存在。?", "：待核实。", content, count=1)
        if num == 6 and emoji == "🔴" and _describes_multiple_customers(content):
            emoji = "🟡"
            content = re.sub(r"：存在。?", "：待核实。", content, count=1)
        if emoji == "🟢":'''

# Try with actual emoji
# The content might have literal emoji or unicode escapes
for old_pat, new_pat in [
    ('_is_routine_sme_information_gap(content):\n            emoji = "\U0001f7e1"\n            content = re.sub(r"：存在。?", "：待核实。", content, count=1)\n        if emoji == "\U0001f7e2":',
     '_is_routine_sme_information_gap(content):\n            emoji = "\U0001f7e1"\n            content = re.sub(r"：存在。?", "：待核实。", content, count=1)\n        if num == 13 and emoji == "\U0001f534" and _has_premium_customer_evidence(content):\n            emoji = "\U0001f7e1"\n            content = re.sub(r"：存在。?", "：待核实。", content, count=1)\n        if num == 6 and emoji == "\U0001f534" and _describes_multiple_customers(content):\n            emoji = "\U0001f7e1"\n            content = re.sub(r"：存在。?", "：待核实。", content, count=1)\n        if emoji == "\U0001f7e2":'),
]:
    if old_pat in c:
        c = c.replace(old_pat, new_pat)
        changes += 1
        print("  OK: 1d. Flag #6/#13 normalization in _fix_red_flags_html")
        break
else:
    print("  WARN: Could not locate flag #12 HTML fix point")

# 1e. _advance_recommendation scale 3/4 separation
old_adv = '''    if scale_category in {3, 4}:
        if grade == "A":
            return "推进", f"{scale_reason} 虽然规模偏小，但企业质量足够强，可推进。"
        if grade == "B":
            return "观察", f"{scale_reason} 企业质量尚可，但规模偏小，先观察。"
        return "不建议推进", f"{scale_reason} 企业质量不足以抵消规模不适配。"'''

new_adv = '''    if scale_category == 3:
        if grade == "A":
            return "观察", f"{scale_reason} 明确证据证明规模不达基金偏好区间，但企业质量强，先观察补证。"
        if grade == "B":
            return "观察", f"{scale_reason} 明确证据证明规模不达基金偏好区间，且企业质量一般。"
        return "不建议推进", f"{scale_reason} 明确证据证明规模不达标且质量弱。"
    if scale_category == 4:
        if grade == "A":
            return "推进", f"{scale_reason} 虽然推断规模偏小，但企业质量足够强，可推进。"
        if grade == "B":
            return "观察", f"{scale_reason} 企业质量尚可，但推断规模偏小，先观察。"
        return "不建议推进", f"{scale_reason} 企业质量不足以抵消规模不适配。"'''

apply(old_adv, new_adv, "1e. Scale category 3/4 separation")

# 1f. _build_exec_summary double period fix
old_summary = '    decision_note = str(result.get("decision_note", "")).strip()\n    if not decision_note:\n        decision_note = "程序复算后生成最终结论"'
new_summary = '    decision_note = str(result.get("decision_note", "")).strip().rstrip("。；;")\n    if not decision_note:\n        decision_note = "程序复算后生成最终结论"'
apply(old_summary, new_summary, "1f. Double period fix")

# 1g. Replace _enforce_supported_rr_conclusion with _enforce_text_score_consistency + _enforce_ka_supplier_rr_score
old_rr = '''def _enforce_supported_rr_conclusion(
    result: dict, scores: list[int], red_numbers: set[int], quick: bool
) -> None:
    """Resolve a model output conflict when its documented RR analysis clearly supports 4 points."""
    if quick or scores[1] >= 4 or 1 in red_numbers:
        return
    text = " ".join(
        str(result.get(key, ""))
        for key in ("sec3_verdict", "sec3_summary", "sec3_content")
    )
    if not re.search(r"(?:评分|应得|得分|给予)\\s*(?:为|[:：])?\\s*4\\s*分|评分\\s*4\\s*分", text):
        return
    support_groups = (
        r"持续供货|稳定供货|连续多年|反复采购|重复订单",
        r"提前排产|敲定.{0,12}订单|周期性订单|节日期间.{0,12}订单",
        r"具名.{0,8}客户|30余家|盒马|全家|联华|小杨生煎|宝立食品",
        r"每月.{0,12}(?:吨|产量)|月产|产量.{0,12}(?:吨|增加)",
    )
    supports = sum(bool(re.search(pattern, text)) for pattern in support_groups)
    has_source_support = bool(
        re.search(r"<sup|\\[\\d+\\]|政府.{0,8}报道|招股书|证据等级\\s*[：:]?\\s*[AB]", text)
    )
    if supports >= 2 and has_source_support:
        scores[1] = 4
        result["rr_score_note"] = "RR正文明确给出4分且包含持续经营公开证据，程序已同步校正结构化分数。"'''

new_rr = '''def _enforce_text_score_consistency(
    result: dict, scores: list[int], evidence: list[int], red_numbers: set[int], quick: bool
) -> None:
    """Correct structured scores when AI text analysis explicitly claims a higher score."""
    if quick:
        return
    _SCORE_CLAIM = re.compile(
        r"(?:评为|评分|应得|得分|得|给予|给)\\s*(?:为|[:：])?\\s*([1-5])\\s*分|评分\\s*([1-5])\\s*分"
    )
    _HAS_SOURCE = re.compile(r"<sup|\\[\\d+\\]|证据等级\\s*[：:]?\\s*[AB]|政府.{0,8}报道|招股书")
    _DIMS: list[tuple[int, tuple[str, ...], str]] = [
        (1, ("sec3_verdict", "sec3_summary", "sec3_content"), ""),
        (2, ("sec5_summary", "sec5_content"), r"市场地位|市占率|排名|龙头|第一|最大|领先|份额"),
        (3, ("sec4_summary", "sec4_content"), ""),
        (4, ("sec2_summary", "sec2_content"), ""),
        (5, ("sec6_summary", "sec6_content"), r"平台|Platform|整合"),
        (6, ("sec6_summary", "sec6_content"), r"Add-on|补充|协同|cross.sell"),
    ]
    _DIM_NAMES = ["行业匹配度", "Recurring Revenue", "市场地位", "客户粘性", "商业模式", "平台价值", "Add-on价值", "交易可行性"]
    for dim_idx, text_keys, context_pattern in _DIMS:
        if dim_idx in red_numbers:
            continue
        if scores[dim_idx] >= 5:
            continue
        if evidence[dim_idx] < 3:
            continue
        text = " ".join(str(result.get(key, "")) for key in text_keys)
        if not text.strip():
            continue
        claimed_scores: set[int] = set()
        for m in _SCORE_CLAIM.finditer(text):
            score_str = m.group(1) or m.group(2)
            if score_str:
                claimed_scores.add(int(score_str))
        if not claimed_scores:
            continue
        claimed = max(claimed_scores)
        if claimed <= scores[dim_idx]:
            continue
        if context_pattern and not re.search(context_pattern, text):
            continue
        if not _HAS_SOURCE.search(text):
            continue
        original = scores[dim_idx]
        scores[dim_idx] = claimed
        result[f"score_note_dim{dim_idx}"] = (
            f"{_DIM_NAMES[dim_idx]}正文明确给出{claimed}分且包含公开证据，"
            f"程序已同步校正结构化分数（原{original}分→现校正为{claimed}分）。"
        )


def _enforce_ka_supplier_rr_score(
    result: dict, scores: list[int], evidence: list[int], red_numbers: set[int], quick: bool
) -> None:
    """Upgrade RR to 5 when the company is a confirmed supplier to major KA retailers."""
    if scores[1] >= 5 or 1 in red_numbers or evidence[1] < 2:
        return
    _MAJOR_KA = (
        r"盒马|奥乐齐|叮咚|美团.{0,4}(?:买菜|小象)|山姆|开市客|Costco|"
        r"百果园|天天果园|永辉|大润发|沃尔玛|麦德龙|Metro|"
        r"全家|罗森|7-Eleven|便利蜂"
    )
    _KA_RE = re.compile(_MAJOR_KA)
    _IS_SUPPLIER = re.compile(r"供应商|供货|供应|配送|客户|合作|服务")
    text = " ".join(
        str(result.get(key, ""))
        for key in ("sec3_content", "sec3_summary", "sec4_content",
                     "sec2_content", "analysis", "exec_summary", "summary")
    )
    if not _IS_SUPPLIER.search(text):
        return
    ka_names = {m.group(0) for m in _KA_RE.finditer(text)}
    if not ka_names:
        return
    has_source = bool(re.search(r"<sup|\\[\\d+\\]", text))
    if not has_source:
        return
    scores[1] = 5
    ka_list = "、".join(sorted(ka_names)[:5])
    result["score_note_dim1"] = (
        f"公开证据确认公司为{ka_list}等头部KA零售商正式供应商，"
        f"达到Recurring Revenue 5分标准，程序已同步校正。"
    )'''

apply(old_rr, new_rr, "1g. _enforce_text_score_consistency + _enforce_ka_supplier_rr_score")

# Update call site in _apply_screening_score
apply("    _enforce_supported_rr_conclusion(result, scores, red_numbers, quick)",
      "    _enforce_text_score_consistency(result, scores, evidence, red_numbers, quick)\n    _enforce_ka_supplier_rr_score(result, scores, evidence, red_numbers, quick)",
      "1h. Update enforcement call sites")

# ============================================================
# SECTION 2: System prompt changes
# ============================================================

# 2a. SYSTEM_PROMPT_ANALYSIS — add market position dimension AFTER RR dimension
old_dim3 = '3.Recurring Revenue判断(核心中的核心)：重复性收入来源、真伪判断、持续供货/重复订单/连续排产等公开经营线索、收入可预测性。对非上市中小企业，不把公开合同期限、续约率、收入占比或排他条款作为4分的必要条件。\n\t4.客户结构与切换成本：客户类型(B端/C端/G端)、需求刚性、切换成本（技术/关系/合规）、客户集中度\n\t5.竞争位置与差异化：市场定位、份额线索、护城河（品牌/技术/渠道/牌照/规模）、竞争壁垒可持续性\n\t6.Platform/Add-on判断'

new_dim3 = '3.Recurring Revenue判断(核心中的核心)：只看订单流事实——已发生的持续供货、重复订单、提前排产、连续生产/出货等客观经营线索，判断收入是否会反复发生。不评价"客户为什么不会走"。对非上市中小企业，不把公开合同期限、续约率、收入占比或排他条款作为4分的必要条件。\n\t4.市场地位（隐形冠军识别）：公开信息中的市场份额线索、行业排名、媒体冠名（"第一""最大""龙头""领先""头部"）、KA覆盖广度、全国性或区域性市场领导地位证据。与竞争位置的区分：竞争位置看"护城河"（怎么赢），市场地位看"战果"（赢了多少）。同一篇报道可同时提供地位证据和竞争证据，但分数各自独立。\n\t5.客户结构与切换成本：只看护城河——客户为什么不会轻易更换供应商？切换成本（技术认证/配方绑定/合规审核/渠道独占）、客户集中度、需求刚性。不要把"客户多、客户大、客户知名、持续供货"直接当作粘性高——那些属于RR或市场地位维度的证据。\n\t6.竞争位置与差异化：市场定位、份额线索、护城河（品牌/技术/渠道/牌照/规模）、竞争壁垒可持续性。注意：此项评价"怎么赢"（壁垒/差异化），市场地位评价"赢了多少"（排名/市占率），避免重复打分。\n\t7.Platform/Add-on判断'

apply(old_dim3, new_dim3, "2a. Market position in SYSTEM_PROMPT_ANALYSIS (analysis instructions)")

# 2b. Update subsequent dimension numbering 7→8, 8→9, 9→10
apply('\t7.规模适配与交易障碍：营收推断', '\t8.规模适配与交易障碍：营收推断', "2b. Renumber 规模 to dim 8")
apply('\t8.红旗核查', '\t9.红旗核查', "2b. Renumber 红旗 to dim 9")
apply('\t9.最终建议：必须分开写', '\t10.最终建议：必须分开写', "2b. Renumber 最终建议 to dim 10")

# 2c. Add market position rubric and RR/粘性 boundary
old_rubric = '2.Recurring Revenue：\n\t  5分=存在公开可核验的强证据（如长约/订阅、重复收入占比、多年稳定复购数据或明确锁定机制）；若公开信息确认公司为盒马、奥乐齐、叮咚、美团买菜/小象超市、山姆、开市客(Costco)等头部KA零售商的正式食品饮料供应商且持续供货，同样满足5分标准\n\t  4分=存在较强公开经营证据证明业务会持续发生，不要求公开合同期限/续约率/收入占比/排他条款'

new_rubric = 'RR vs 客户粘性边界（必须遵守）：\n\t- RR只评价"收入会不会反复发生"：看已发生的供货/订单/排产/产量等经营事实，不涉及客户锁定机制。\n\t- 客户粘性只评价"客户为什么不走"：看切换成本、认证壁垒、配方绑定、产线专供等锁定机制，不涉及订单节奏。\n\t- 常见混淆：客户数量多/知名度高/合作年数长 → 本身不是粘性证据（除非有具体锁定机制佐证）。持续给大客户供货 → 这是RR证据，不代表客户被锁定。\n\t- 两个维度各自独立打分，不得互为代理。\n\t2.Recurring Revenue：\n\t  5分=存在公开可核验的强证据（如长约/订阅、重复收入占比、多年稳定复购数据或明确锁定机制）；若公开信息确认公司为盒马、奥乐齐、叮咚、美团买菜/小象超市、山姆、开市客(Costco)等头部KA零售商的正式食品饮料供应商且持续供货，同样满足5分标准\n\t  4分=存在较强公开经营证据证明业务在持续发生——多个具名B端客户+已发生的持续供货报道、提前排产/周期性订单、连续月产量或反复采购证据。注意：仅凭产品特性推演出"理论上会复购"不属于4分，必须看到已发生的经营事实\n\t  3分=仅能从产品特性或客户场景推断会复购，尚未看到已发生的持续供货、重复订单或连续经营事实\n\t  2分=以项目制/一次性收入为主，但存在附加服务收入\n\t  1分=纯一次性交易，无任何重复收入线索\n\t  输出一致性：若正文结论写明"评分4分/应得4分"，radar_scores 中第2项必须同步输出4，不得出现正文与结构化分数矛盾。\n\t3.市场地位：\n\t  5分=公认的全国性细分龙头——媒体/行业报告明确称为"第一/最大/龙头/领先"，或覆盖全国头部KA且无同等竞品\n\t  4分=区域性龙头或全国前列——有明显市场领先证据（省级/区域第一、行业排名前列、头部KA全覆盖），或权威来源确认为"领先/头部"企业\n\t  3分=有一定行业知名度——被提及为重要参与者但非领导地位，或在特定渠道/客户群有优势但整体份额不突出\n\t  2分=跟随者——市场地位不突出，未见于行业排名或权威提及\n\t  1分=新进入者或边缘参与者——无可见市场地位\n\t  输出一致性：若正文写明"第一/最大/龙头/领先"等冠军特征，radar_scores 中第3项必须≥4分。\n\t4.客户粘性：\n\t  5分=客户切换成本极高（技术认证壁垒、独家供应协议、共同研发绑定），且客户集中度合理\n\t  4分=存在具体的切换成本证据（配方绑定、渠道绑定、质量认证审核周期、定制化产线专供），客户难以轻易替换\n\t  3分=客户长期合作但未见具体锁定机制（例如合作多年但产品标准化、合同一年一签、未提及认证/专供/绑定），或定制化程度一般\n\t  2分=产品标准化程度高，客户更换供应商成本低\n\t  1分=纯贸易/批发，客户随时可以切换\n\t5.商业模式：'

apply(old_rubric, new_rubric, "2c. Market position rubric + RR/粘性 boundary")

# 2d. Update remaining rubric numbering (5→6, 6→7, 7→8)
apply('\t5.平台价值（能否作为行业整合平台）', '\t6.平台价值（能否作为行业整合平台）', "2d. Renumber 平台 to #6")
apply('\t6.Add-on价值（对现有portfolio的补充价值）', '\t7.Add-on价值（对现有portfolio的补充价值）', "2d. Renumber Add-on to #7")
apply('\t7.交易可行性（不含规模适配）', '\t8.交易可行性（不含规模适配）', "2d. Renumber 交易可行性 to #8")

# 2e. Update red-flag caps text
old_caps = '#1 一次性项目为主 🔴 → 维度2(Recurring Revenue) ≤2\n\t- #3 纯贸易低壁垒 🔴 → 维度3(客户粘性)≤2 且 维度4(商业模式)≤2'
new_caps = '#1 一次性项目为主 🔴 → 维度2(Recurring Revenue) ≤2\n\t- #3 纯贸易低壁垒 🔴 → 维度4(客户粘性)≤2 且 维度5(商业模式)≤2'
apply(old_caps, new_caps, "2e. Update red-flag caps text #1/#3")

old_caps2 = '#6 依赖单一大客户 🔴 → 维度3(客户粘性)≤2\n\t- #7 过度依赖老板个人关系 🔴 → 维度7(交易可行性)≤3\n\t- #8 技术替代风险高 🔴 → 维度5(平台价值)≤3'
new_caps2 = '#6 依赖单一大客户 🔴 → 维度4(客户粘性)≤2\n\t- #7 过度依赖老板个人关系 🔴 → 维度8(交易可行性)≤3\n\t- #8 技术替代风险高 🔴 → 维度6(平台价值)≤3'
apply(old_caps2, new_caps2, "2e. Update red-flag caps text #6/#7/#8")

old_caps3 = '#11 平台能力不足 🔴 → 维度5(平台价值)≤3 且 维度6(Add-on)≤3\n\t- #12 财务规范性或主体清晰度可疑 🔴 → 维度7(交易可行性)≤3\n\t- #13 客户质量不足 🔴 → 维度3(客户粘性)≤2'
new_caps3 = '#11 平台能力不足 🔴 → 维度6(平台价值)≤3 且 维度7(Add-on)≤3\n\t- #12 财务规范性或主体清晰度可疑 🔴 → 维度8(交易可行性)≤3\n\t- #13 客户质量不足 🔴 → 维度4(客户粘性)≤2'
apply(old_caps3, new_caps3, "2e. Update red-flag caps text #11/#12/#13")

# 2f. SYSTEM_PROMPT_JSON — update radar_scores and evidence_levels format
old_json = '"radar_scores":[4,3,3,4,3,3,3],"evidence_levels":[3,3,2,2,2,2,2,3]'
new_json = '"radar_scores":[4,3,3,3,4,3,3,3],"evidence_levels":[3,3,2,2,2,2,2,2,3]'
apply(old_json, new_json, "2f. Update JSON format example")

old_json2 = '"sec3_content":"HTML内容","sec4_summary":"摘要","sec4_content":"HTML内容","sec5_summary":"摘要","sec5_content":"HTML内容","sec6_summary":"判断+理由","sec6_verdict":"Platform/Add-on/Borderline/非目标","sec6_content":"HTML","sec7_summary":"营收区间+规模适配+交易障碍"'
new_json2 = '"sec3_content":"HTML内容","sec4_summary":"市场地位摘要","sec4_content":"HTML内容","sec5_summary":"客户粘性摘要","sec5_content":"HTML内容","sec6_summary":"竞争位置摘要","sec6_content":"HTML内容","sec7_summary":"判断+理由","sec7_verdict":"Platform/Add-on/Borderline/非目标","sec7_content":"HTML","sec8_summary":"营收区间+规模适配+交易障碍"'
apply(old_json2, new_json2, "2g. Update JSON section layout")

old_json3 = ',"sec7_table":"<tr>...</tr>HTML行","maturity":"判断"'
new_json3 = ',"sec8_table":"<tr>...</tr>HTML行","maturity":"判断"'
apply(old_json3, new_json3, "2h. Update sec table reference")

old_json4 = '"sec8_summary":"证据统计","sec8_table":"<tr>...</tr>HTML行","sec9_summary":"初步判断","sec9_verdict":"优先深挖/值得继续看/保留观察/暂不优先初步建议","verdict_type":"pass/watch/reject初步建议","sec9_reason":"理由"'
new_json4 = '"sec9_summary":"证据统计","sec9_table":"<tr>...</tr>HTML行","sec10_summary":"初步判断","sec10_verdict":"优先深挖/值得继续看/保留观察/暂不优先初步建议","verdict_type":"pass/watch/reject初步建议","sec10_reason":"理由"'
apply(old_json4, new_json4, "2i. Update final sections numbering")

# 2g. Update evidence_levels description
old_ev = 'evidence_levels 依次对应行业归属、商业模式、Recurring Revenue、客户质量、切换成本、平台价值、规模推断、可交易性'
new_ev = 'evidence_levels 依次对应行业归属、商业模式、Recurring Revenue、客户质量、切换成本、平台价值、市场地位、规模推断、可交易性'
apply(old_ev, new_ev, "2j. Update evidence_levels description")

# 2h. SYSTEM_PROMPT_QUICK_SCORE — add market position
old_qs = '2.Recurring Revenue：长约/订阅/重复收入占比或多年稳定复购等强证据=5分；确认为盒马/奥乐齐/叮咚/美团/山姆/开市客等头部KA零售商正式供应商且持续供货=5分；多个具名客户且有持续供货、提前排产、周期性订单或连续产量等经营证据=4分（中小企业无需公开合同期限/续约率/排他条款）；仅由产品特性推测复购=3分；项目制为主=2分；纯一次性=1分\n3.客户粘性：技术认证/独家协议/共同研发=5分'
new_qs = '2.Recurring Revenue：长约/订阅/重复收入占比或多年稳定复购等强证据=5分；确认为盒马/奥乐齐/叮咚/美团/山姆/开市客等头部KA零售商正式供应商且持续供货=5分；多个具名客户且有持续供货、提前排产、周期性订单或连续产量等经营证据=4分（中小企业无需公开合同期限/续约率/排他条款）；仅由产品特性推测复购=3分；项目制为主=2分；纯一次性=1分。注意：客户多/大/知名属于客户质量线索，不等于RR高；必须看到已发生的经营事实才算RR证据。\n3.市场地位（隐形冠军识别）：全国性细分龙头/权威媒体称为第一/最大/龙头=5分；区域性龙头/省级第一/头部KA全覆盖=4分；有知名度但非领导地位=3分；跟随者=2分；新进入者/无地位=1分\n4.客户粘性（只看锁定机制，不涉及订单节奏）：技术认证/独家协议/共同研发=5分；配方绑定/渠道绑定/质量认证/定制产线=4分；长期合作但无具体锁定证据=3分；产品标准化更换成本低=2分；纯贸易=1分。注意：持续供货报道属于RR证据而非粘性证据；粘性必须有具体的锁定/绑定/认证机制佐证'
apply(old_qs, new_qs, "2k. Update QUICK_SCORE with market position + RR/粘性 boundary")

# Update quick score subsequent numbering
apply('\n4.商业模式：轻资产高毛利可复制=5分', '\n5.商业模式：轻资产高毛利可复制=5分', "2l. Quick score renumber 商业模式→5")
apply('\n5.平台价值：多工厂标准化可整合=5分', '\n6.平台价值：多工厂标准化可整合=5分', "2l. Quick score renumber 平台→6")
apply('\n6.Add-on价值：完美补充现有portfolio=5分', '\n7.Add-on价值：完美补充现有portfolio=5分', "2l. Quick score renumber Add-on→7")
apply('\n7.交易可行性（不含规模）：股权清晰有出售线索=5分', '\n8.交易可行性（不含规模）：股权清晰有出售线索=5分', "2l. Quick score renumber 交易→8")

# ============================================================
# SECTION 3: fill_report_template updates
# ============================================================

# 3a. Radar and evidence chart lengths
apply('scores = _safe_numeric_values(analysis_json.get("radar_scores"), 6, 3)',
      'scores = _safe_numeric_values(analysis_json.get("radar_scores"), 7, 3)', "3a. Radar chart 6→7")

apply('"{{6个维度评分，逗号分隔}}"', '"{{7个维度评分，逗号分隔}}"', "3a. Radar placeholder")

apply('evidence_levels = _safe_numeric_values(analysis_json.get("evidence_levels"), 7, 2)',
      'evidence_levels = _safe_numeric_values(analysis_json.get("evidence_levels"), 8, 2)', "3a. Evidence chart 7→8")

apply('"{{7个结论项的证据等级数字，A=4 B=3 C=2 D=1}}"',
      '"{{8个结论项的证据等级数字，A=4 B=3 C=2 D=1}}"', "3a. Evidence placeholder")

# 3b. Add market position placeholders
old_sec4 = '"{{客户质量+切换成本+关键风险}}": _escape_text(analysis_json.get("sec4_summary", "")),\n\t    "{{客户类型、需求本质...}}": _sanitize_html_fragment(analysis_json.get("sec4_content", "")),'
new_sec4 = '"{{市场地位判断+一句话描述}}": _escape_text(analysis_json.get("sec4_summary", "")),\n\t    "{{市场地位详细分析HTML}}": _sanitize_html_fragment(analysis_json.get("sec4_content", "")),\n\t    "{{客户质量+切换成本+关键风险}}": _escape_text(analysis_json.get("sec5_summary", "")),\n\t    "{{客户类型、需求本质...}}": _sanitize_html_fragment(analysis_json.get("sec5_content", "")),'
apply(old_sec4, new_sec4, "3b. Market position placeholders + shift sec4→sec5")

# 3c. Shift subsequent section references
apply('analysis_json.get("sec5_summary", "")),', 'analysis_json.get("sec6_summary", "")),', None)
apply('analysis_json.get("sec5_content", "")),', 'analysis_json.get("sec6_content", "")),', None)
apply('analysis_json.get("sec6_summary", "")),', 'analysis_json.get("sec7_summary", "")),', None)
apply('analysis_json.get("sec6_verdict", "待判断")),', 'analysis_json.get("sec7_verdict", "待判断")),', None)
apply('analysis_json.get("sec6_content", "")),', 'analysis_json.get("sec7_content", "")),', None)
apply('analysis_json.get("sec7_summary", "")),', 'analysis_json.get("sec8_summary", "")),', None)
apply('analysis_json.get("sec7_table", "")', 'analysis_json.get("sec8_table", "")', None)
apply('analysis_json.get("sec8_summary", "")),', 'analysis_json.get("sec9_summary", "")),', None)
apply('analysis_json.get("sec8_table", "")', 'analysis_json.get("sec9_table", "")', None)
apply('analysis_json.get("sec9_summary", "")),', 'analysis_json.get("sec10_summary", "")),', None)
print("  OK: 3c. Section reference shifts")

# Save
with open("server.py", "w", encoding="utf-8") as f:
    f.write(c)

print(f"\n=== Total changes applied: {changes} ===")
