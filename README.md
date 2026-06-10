# PE Deep Screening

AI 驱动的私募股权（PE）并购标的筛选 Agent 系统。给 LLM 装上搜索引擎，让它自主完成从信息搜集到多维评分的完整尽调分析。

## 核心思路

传统方法：程序搜索 → 过滤 → 截断 → AI 被动分析。LLM 只能分析给定的静态文本。

本系统：程序预搜索提供信息起点 → **LLM 持有搜索工具，自主决定搜什么、搜几轮** → 多轮迭代 → 结构化评分输出。

## 技术架构

| 层级 | 技术 |
|------|------|
| **Agent 引擎** | LLM Tool Calling（search_web / fetch_page），最多 3 轮自主补搜 |
| **搜索管线** | Exa → Tavily → 百度（中文源） → 微信公众号 → Playwright 全文抓取 |
| **工商核验** | 企查查 MCP 协议集成，自动拉取工商登记 / 股东 / 实控人 / 参保等数据 |
| **多模型路由** | DeepSeek V4 Pro（默认）/ Kimi K2.6（256K 长上下文）/ Moonshot V1 128K |
| **评分引擎** | Compounder 透镜 5 维加权（RR 30% + 市场地位 25% + 商业模式 20% + 客户粘性 15% + 行业 10%）|
| **Guardrails** | AI 打分 → 程序公式重算 → 14 项 PE 红旗规则强制封顶 → 交易可行性硬否决 → 自我审查 |
| **Structured Output** | `---JSON---` 标记 + 10 种容错 JSON 解析策略 + 终极 regex 兜底 |
| **流式响应** | SSE streaming，分析阶段实时展示 AI 思考过程 |
| **前端** | 原生 HTML/CSS/JS，FastAPI 后端，Nginx 部署 |

## 工程亮点

### Agentic RAG
不是传统的"搜一次 → 拼进 prompt → 输出"流程。LLM 在分析过程中发现信息缺口时，**自主调用搜索工具**，搜索结果自动纳入统一编号引用体系。程序预搜索提供信息起点，AI 动态补搜。

### LLM-as-Judge + Guardrails
核心设计原则：**AI 负责观察和推理，程序负责裁判**。
- 每个维度 AI 给 1-5 分 + 理由 + 证据等级
- 程序用固定权重（非 AI 输出的权重）重算总分和评级
- 14 项 PE 红旗（大客户依赖、老板关系、技术替代等）触发时，强制对相关维度分封顶
- 交易可行性为 `evidence_no` 时硬否决推进
- 评分完成后自动检查内部矛盾（A 级 + 规模过小 → 推进？），发现矛盾自动修正

### 鲁棒的 JSON 解析
LLM 输出结构化 JSON 是经典工程难题。本系统实现了 **10 层容错策略**：
1. 提取 `json` 代码块
2. 直接解析
3. 首尾大括号截取
4. 移除 JS 注释 / 尾部逗号 / 单引号
5. 控制字符处理
6. 嵌入引号修复
7. json5 宽松解析
8. 正则逐字段提取（终极兜底）

所有策略失败时，正则提取核心字段补齐默认值，**绝不因 JSON 损坏而丢弃整条分析**。

### 两步式批量预筛选
上传企查查 Excel → 先用表格中的工商数据跑 8 条硬性规则（经营状态 / 地域 / 成立年限 / 参保 / 注册资本 / 企业类型），纯 Python 判断，**零 API 消耗，秒级完成**。通常可筛掉 50-70% 的公司。排除结果即时可见，用户确认后再对通过公司启动完整 AI 分析。

## 运行

### 环境变量

```bash
export DEEPSEEK_API_KEY=sk-xxx
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-v4-pro
export KIMI_API_KEY=sk-xxx      # 可选
export TAVILY_API_KEY=tvly-xxx  # 可选
export QCC_MCP_KEY=xxx          # 可选，企查查
```

### 启动

```bash
cd pe-screening-web
pip install -r requirements.txt
python server.py
# 访问 http://localhost:8000
```

### 生产部署

```bash
systemctl start pe-screening  # systemd 服务
nginx -s reload               # Nginx 反向代理
```

## 已知局限 & 下一步

- **搜索不确定性**：每次搜索 API 返回结果不同，导致同一公司多次分析结论有波动。已通过 `temperature=0` 消除 LLM 侧随机性，搜索侧的不确定性仍需缓存或搜索去重解决
- **缺少评测集**：改 prompt 后无法自动化验证效果变化。计划建立 30 家黄金标准公司的评测集
- **单文件架构**：`server.py` 承载过多逻辑，后续考虑拆分为 `engine/search.py` / `engine/scoring.py` / `engine/llm.py`
- **Agent 决策日志缺失**：工具调用的 trace 仅通过 print 输出，缺少结构化日志

## License

MIT
