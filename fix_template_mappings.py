"""Update fill_report_template with card-based placeholder mappings."""
with open("server.py", "r", encoding="utf-8") as f:
    c = f.read()

# Build card-based placeholders
card_placeholders = """        # ---- Card-based section placeholders (maps to template cards) ----
        # Card 1: 行业匹配度 (identity + product merged)
        "{{card1_industry_summary}}": _escape_text(
            f"{analysis_json.get('industry', '')} | {analysis_json.get('business_type', '')}"
        ),
        "{{card1_industry_content}}": (
            _sanitize_html_fragment(analysis_json.get("sec1_content", ""))
            + "<hr>" + _sanitize_html_fragment(analysis_json.get("sec2_content", ""))
        ),

        # Card 2: Recurring Revenue
        "{{card2_rr_summary}}": _escape_text(analysis_json.get("sec3_summary", "")),
        "{{card2_rr_verdict}}": _escape_text(analysis_json.get("sec3_verdict", "暂无法确认")),
        "{{card2_rr_content}}": _sanitize_html_fragment(analysis_json.get("sec3_content", "")),

        # Card 3: 市场地位 (market position + competition merged)
        "{{card3_market_summary}}": _escape_text(analysis_json.get("sec5_summary", "")),
        "{{card3_market_content}}": (
            '<div class="sub-section"><h4>市场地位分析</h4>'
            + _sanitize_html_fragment(analysis_json.get("sec5_content", ""))
            + '</div><hr><div class="sub-section"><h4>竞争位置与差异化</h4>'
            + _sanitize_html_fragment(analysis_json.get("sec6_content", ""))
            + '</div>'
        ),

        # Card 4: 客户粘性
        "{{card4_stickiness_summary}}": _escape_text(analysis_json.get("sec4_summary", "")),
        "{{card4_stickiness_content}}": _sanitize_html_fragment(analysis_json.get("sec4_content", "")),

        # Card 5: 商业模式
        "{{card5_bizmodel_summary}}": _escape_text(analysis_json.get("sec2_summary", "")),
        "{{card5_bizmodel_content}}": _sanitize_html_fragment(analysis_json.get("sec2_content", "")),

        # Card 6: Platform / Add-on
        "{{card6_platform_summary}}": _escape_text(analysis_json.get("sec7_summary", "")),
        "{{card6_platform_verdict}}": _escape_text(analysis_json.get("sec7_verdict", "待判断")),
        "{{card6_platform_content}}": _sanitize_html_fragment(analysis_json.get("sec7_content", "")),

        # Card 7: 交易可行性 & 规模适配
        "{{card7_trade_summary}}": _escape_text(analysis_json.get("sec8_summary", "")),
        "{{card7_revenue}}": _escape_text(
            f"{analysis_json.get('revenue_range', '待推算')} ({analysis_json.get('revenue_evidence', 'C')})"
        ),
        "{{card7_scale}}": _escape_text(analysis_json.get("scale_fit_label", "")),
        "{{card7_obstacle}}": _escape_text(analysis_json.get("transaction_obstacle_label", "")),
        "{{card7_trade_content}}": _sanitize_html_fragment(
            (analysis_json.get("revenue_process_html", "") or "")
            + (analysis_json.get("sec8_table", "") or "")
        ),

        # Card 8: 红旗核查
        "{{card8_flags_summary}}": _escape_text(analysis_json.get("sec9_summary", "")),

        # Card 9: 最终建议
        "{{card9_final_summary}}": _escape_text(analysis_json.get("sec10_summary", "")),
        "{{card9_final_content}}": _sanitize_html_fragment(
            _sanitize_html_fragment(analysis_json.get("next_steps_html", ""))
        ),

"""

# Find the replacement dict section
old_start = c.find('"{{一句话摘要：行业归属+成立时间+实控人+规模概况}}"')
old_end = c.find('"{{参考来源清单}}"')

if old_start < 0 or old_end < 0:
    print("ERROR: Could not find section placeholders")
    exit(1)

# Replace the section placeholders (keep the old ones for backward compat + add new card ones)
# Insert card placeholders before "{{参考来源清单}}"
c = c[:old_end] + "\n" + card_placeholders + c[old_end:]

with open("server.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Done!")
