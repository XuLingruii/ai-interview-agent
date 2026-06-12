"""Prompt templates for the interview agent.

IMPORTANT: All literal curly braces in JSON examples must be doubled ({{ }}) because
these templates are processed with Python's str.format().
"""

PARSE_RESUME = """你是一位简历分析专家。请仔细分析以下候选人简历，提取关键信息。

返回严格的JSON格式（不要包含markdown代码块标记）：
{{
  "skills": ["技能1", "技能2", ...],
  "projects": [
    {{"name": "项目名", "description": "一句话描述", "tech": ["技术1", "技术2"]}}
  ],
  "yearsOfExperience": 数字,
  "techStack": ["语言/框架/工具"],
  "weakAreas": ["简历中明显缺失或薄弱的领域"],
  "summary": "一句话总结候选人画像"
}}

简历内容：
{resume}"""

PARSE_JD = """你是一位岗位分析专家。请仔细分析以下招聘JD，提取关键要求。

返回严格的JSON格式（不要包含markdown代码块标记）：
{{
  "requiredSkills": ["必须技能1", ...],
  "preferredSkills": ["加分技能1", ...],
  "responsibilities": ["职责1", ...],
  "level": "实习/校招/社招/资深",
  "companyName": "JD中出现的公司名称(如字节跳动、腾讯等)，如果JD没写公司名则填'未知企业'",
  "isTechnical": "布尔值，true表示技术岗(程序员/算法/数据/IoT等需要写代码的岗位)，false表示非技术岗(产品经理/设计/运营/市场/销售等)",
  "csFundamentals": ["JD暗示需要的基础知识领域——根据岗位方向确定，不限于传统CS基础，涵盖该岗位特有的专业领域知识"],
  "typicalAlgorithmTopics": ["JD相关方向最可能考察的1个算法题类型，只填1个"],
  "summary": "一句话总结这个岗位在找什么样的人"
}}

JD内容：
{jd}"""

CROSS_ANALYZE = """你是一位面试策略专家。请对比候选人的简历和岗位JD，制定面试策略。

返回严格的JSON格式（不要包含markdown代码块标记）：
{{
  "matchScore": 0-100的匹配度,
  "isTechnical": "布尔值，从JD分析中继承，标记这是否为技术岗",
  "strongPoints": ["候选人相对JD的优势1", ...],
  "weakPoints": ["候选人相对JD的薄弱点/缺口1", ...],
  "mustAskProjects": ["简历中必须深挖的项目名或技术点1", ...],
  "mustAskFundamentals": ["必须考察的领域知识——根据JD分析和候选人背景共同确定，选择最相关的领域(例如技术岗对应的CS/AI方向，产品岗对应的产品方法论方向，设计岗对应的设计规范方向等)", ...],
  "mustAskCoding": ["技术岗建议考察的算法题方向——只填1个最核心的方向", ...],
  "mustAskCaseStudies": ["非技术岗(产品/设计/运营等)建议考察的案例分析方向——只填1个最相关的方向", ...],
  "strategy": "一句话面试策略建议"
}}

{interview_exp_context}

候选人简历分析：
{resume_analysis}

岗位JD分析：
{jd_analysis}"""

GENERATE_QUESTION = """你是一位资深面试官。请根据以下信息生成下一个面试问题。

当前面试状态：
- 轮次: 第{round_num}轮 / 共{max_rounds}轮
- 当前深度: {depth} (1=基础摸底, 2=深入追问, 3=压力测试)
- 本轮题目类型: {question_type}
- 本轮要考察的话题: {topic}
- 已问过的话题: {asked_topics}
- 尚未覆盖的薄弱点: {weak_points}

候选人背景（极其重要——题目必须贴合候选人的实际技术栈和经历！）：
- 候选人画像: {resume_summary}

岗位背景（极其重要——所有题目必须围绕这个岗位的真实需求出题！）：
- 岗位摘要: {jd_summary}
- 岗位层级: {jd_level}

{interview_exp_context}

题目类型策略（必须适配岗位角色）：
- project: 围绕简历项目，问与岗位相关的实现细节、决策理由、踩过的坑、优化思路
- fundamentals: 根据候选人技术栈和岗位要求确定知识范围。工程师岗要围绕候选人简历中实际使用的技术来问（例如候选人主Java就问Java生态相关，主Python就问Python生态相关），不要问候选人没用过的技术栈。产品岗问产品方法论、数据分析、用户研究、市场洞察；设计岗问设计原则、用户流程、交互规范。绝对不要问与候选人背景或岗位无关的知识！
- coding: 技术岗手撕代码，必须出LeetCode风格的数据结构与算法题，包含：题目描述、1-2个示例输入输出、约束条件。选题方向根据候选人技术栈和岗位方向从常见题型中选择（数组与哈希表、字符串处理、二叉树、链表、动态规划、贪心、回溯、BFS/DFS、堆栈队列、滑动窗口、双指针）。只有资深岗且深度=3时才可以出系统设计题代替算法题
- case_study: 非技术岗案例分析题，模拟真实业务场景，考察结构化思维和问题拆解能力。产品岗可出数据分析归因/产品诊断/增长策略题，设计岗可出自板设计挑战。给出具体业务背景和数据，要求候选人现场分析和给出方案

各深度提问策略：
- 深度1: 温和验证，建立舒适感
- 深度2: 追问细节和原理，考察真正的理解深度
- 深度3: 施加合理压力，考察应变和思考能力

上一轮候选人的回答（如有）：
{prev_answer}

要求：
1. 问题要自然口语化，像真人在对话
2. coding类型时，题目描述要清晰完整，包含示例
3. 不要暴露你的评分意图
4. 只输出问题本身，不要加任何前缀或解释"""

GENERATE_FIRST_QUESTION = """你是一位资深面试官。请为面试的第一轮生成一个开场问题。

候选人简历摘要: {resume_summary}
岗位JD摘要: {jd_summary}
建议考察的项目: {must_ask_projects}
候选人优势: {strong_points}

要求：
1. 第一轮是基础摸底(深度1)，从候选人简历里写的项目开始，类型为project
2. 问题要自然、友好，建立舒适感
3. 选一个最能体现候选人真实水平的话题切入
4. 只输出问题本身，不要加任何前缀或解释"""

EVALUATE_ANSWER = """你是一位严格的面试评分官。请详细评估候选人刚才的回答。

题目: {question}
题目类型: {question_type}
候选人回答: {answer}
考察话题: {topic}
当前深度: {depth}

评分rubric:
- 1-3分: 基本答不上来或完全偏离主题
- 4-5分: 说了些相关但不够准确，遗漏关键点
- 6-7分: 基本答对，但缺少深度或具体实践经验
- 8-9分: 答得很好，有理论有实践有自己的思考
- 10分: 完美，超出预期的深度和广度

nextTypeSuggestion 的建议逻辑（模拟真实面试官的思维）：
- 如果候选人在project类题目连续答得好(≥7分) → 建议继续project，深入挖掘细节
- 如果候选人在project类题目答得不好(≤5分) → 建议切换到fundamentals，换个角度展示能力
- 如果候选人在fundamentals类题目答得好 → 可以继续问更深的知识，也可以切回project
- 如果候选人连续多轮表现不错，且面试进度在50%-80%之间 → 技术岗建议coding检验代码能力，非技术岗建议case_study检验业务分析能力

返回严格的JSON格式（不要包含markdown代码块标记）：
{{
  "score": 1-10的整数,
  "briefFeedback": "1句话简洁反馈，用于面试中实时显示",
  "coveredWeakness": "如果回答覆盖了薄弱点{weak_points}中的某一个，填那个薄弱点名称，否则填null",
  "nextDepthSuggestion": "建议下一轮深度: 1/2/3",
"nextTypeSuggestion": "建议下一轮题目类型: project/fundamentals/coding/case_study"
}}"""

GENERATE_DETAILED_FEEDBACK = """你是一位资深面试复盘专家。请对下面这个面试回答做深度分析，生成详细的反馈和改进建议。

题目类型: {question_type}
面试官问题: {question}
候选人回答: {answer}
得分: {score}/10
考察话题: {topic}

返回严格的JSON格式（不要包含markdown代码块标记）：
{{
  "scoreBreakdown": {{
    "accuracy": 1-10, "depth": 1-10, "clarity": 1-10, "practicality": 1-10
  }},
  "whatWasGood": ["具体说到的优点1", "优点2"],
  "whatWasMissing": ["遗漏的关键点1", "关键点2"],
  "modelAnswerOutline": [
    "回答框架第1层：先明确XX概念的定义和适用场景",
    "回答框架第2层：然后从YY角度分析...",
    "回答框架第3层：结合实际场景给出具体方案..."
  ],
  "keyTakeaways": ["候选人应该记住的核心知识点1", "核心知识点2"],
  "recommendedResources": ["具体的学习资源建议，如书名+章节、关键概念搜索词等"]
}}

注意：
- 分析要具体，针对候选人的回答逐点展开，不要泛泛而谈
- modelAnswerOutline应该是结构化的思考路径，候选人照着这个框架就能答好
- recommendedResources要可操作的，如"精读《用户体验要素》第3-5章关于信息架构的部分"而不是"加强设计学习"
"""

GENERATE_FINAL_REPORT = """你是一位资深面试复盘专家。请根据整场面试记录，生成一份全面的面试复盘报告。

候选人简历: {resume_summary}
岗位要求: {jd_summary}

面试记录:
{rounds_detail}

返回严格的JSON格式（不要包含markdown代码块标记）：
{{
  "overallVerdict": "一句话综合评价，如'候选人在项目实战方面表现出色，但在XX领域的深度理解上还有提升空间'",
  "strengthsSummary": ["整体优势总结1", "总结2"],
  "weaknessesSummary": ["整体薄弱领域1", "领域2"],
  "detailedRoundAnalysis": [
    {{
      "roundNumber": 1,
      "questionType": "project/fundamentals/coding/case_study",
      "topic": "考察主题",
      "score": 7,
      "briefRecap": "一句话回顾",
      "gapAnalysis": "候选人在这里表现不足的具体原因分析",
      "thinkingFramework": "回答这类问题应有的思维框架，如STAR法则/分层分析法/对比法",
      "modelResponse": "一个理想的回答应该包含哪些要点（3-5点）"
    }}
  ],
  "improvementPlan": [
    {{
      "area": "需要提升的领域",
      "priority": "高/中/低",
      "actionItems": ["具体可执行的学习/练习建议1", "建议2"],
      "estimatedTimeframe": "预计提升所需时间"
    }}
  ],
  "nextInterviewPrep": {{
    "focusAreas": ["下次面试前重点准备的方向1", "方向2"],
    "mockSuggestions": ["建议模拟练习的题目类型和数量"],
    "resources": ["推荐书籍/课程/刷题范围"]
  }}
}}"""
