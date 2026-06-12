"""ReAct AgentLoop — the core interview simulation engine.

Thought → Action → Observation cycle:
  Thought: assess what to ask next based on current state
  Action: call tool (generate question, evaluate answer)
  Observation: process result, update state

Dynamic question-type selection (simulates real interview adaptability):
  - Project scores high → keep digging deeper into projects
  - Project scores low → switch to fundamentals to give candidate a chance
  - Coding: exactly 1 round, placed in the second half (technical roles only)

~250 lines. Mention this in your own interviews.
"""

import json
import queue
from dataclasses import dataclass, field
from llm_client import truncate_text
from tools import (
    parse_resume,
    parse_jd,
    cross_analyze,
    generate_first_question,
    generate_question,
    evaluate_answer,
    generate_detailed_feedback,
    generate_final_report,
)


@dataclass
class InterviewState:
    session_id: str = ""
    resume: dict = field(default_factory=dict)
    jd: dict = field(default_factory=dict)
    analysis: dict = field(default_factory=dict)
    rounds: list = field(default_factory=list)
    current_round: int = 0
    max_rounds: int = 8
    current_depth: int = 1
    current_question_type: str = "project"
    status: str = "ready"
    weak_points: list = field(default_factory=list)
    covered_weaknesses: list = field(default_factory=list)
    asked_topics: list = field(default_factory=list)
    consecutive_high: int = 0
    consecutive_low: int = 0
    current_question: str = ""
    current_topic: str = ""
    # Multi-type support
    must_ask_projects: list = field(default_factory=list)
    must_ask_fundamentals: list = field(default_factory=list)
    must_ask_coding: list = field(default_factory=list)
    must_ask_case_studies: list = field(default_factory=list)
    coding_done: bool = False
    case_study_done: bool = False
    is_technical: bool = True
    interview_exp_context: str = ""
    asked_project_topics: list = field(default_factory=list)
    asked_fundamentals_topics: list = field(default_factory=list)
    asked_coding_topics: list = field(default_factory=list)
    asked_case_study_topics: list = field(default_factory=list)


class AgentLoop:
    """ReAct interview agent loop with dynamic question-type selection.

    Simulates real interviewer behavior:
    - Strong project answers → drill deeper, the conversation is interesting
    - Weak project answers → pivot to fundamentals to explore other strengths
    - Coding round inserted once in the second half as a structured check
    """

    def __init__(self, max_rounds: int = 8):
        self.state = InterviewState(max_rounds=max_rounds)

    def initialize(self, resume_text: str, jd_text: str) -> dict:
        """Parse resume & JD, search for interview experiences, cross-analyze."""
        self.state.resume = parse_resume(resume_text)
        self.state.jd = parse_jd(jd_text)

        # 搜索目标企业/岗位的面经作为出题参考
        from web_search import search_interview_experiences
        company = self.state.jd.get("companyName") or ""
        position = self.state.jd.get("summary", "")
        self.state.interview_exp_context = search_interview_experiences(company, position)

        self.state.analysis = cross_analyze(
            self.state.resume, self.state.jd,
            interview_exp_context=self.state.interview_exp_context,
        )
        self.state.weak_points = list(self.state.analysis.get("weakPoints", []))
        self.state.must_ask_projects = list(self.state.analysis.get("mustAskProjects", []))
        self.state.must_ask_fundamentals = list(self.state.analysis.get("mustAskFundamentals", []))
        self.state.must_ask_coding = list(self.state.analysis.get("mustAskCoding", []))
        self.state.must_ask_case_studies = list(self.state.analysis.get("mustAskCaseStudies", []))
        self.state.is_technical = bool(self.state.analysis.get("isTechnical", True))
        self.state.status = "ready"

        return {
            "resume": self.state.resume,
            "jd": self.state.jd,
            "analysis": self.state.analysis,
        }

    def start_interview(self) -> str:
        """First question: always project type (warm-up, verify resume)."""
        self.state.current_depth = 1
        self.state.current_round = 1
        self.state.current_question_type = "project"
        self.state.status = "in_progress"

        topic = self._pick_topic_for_type("project")
        self.state.current_topic = topic

        question = generate_first_question(
            resume_summary=self.state.resume.get("summary", ""),
            jd_summary=self.state.jd.get("summary", ""),
            must_ask_projects=self.state.must_ask_projects,
            strong_points=self.state.analysis.get("strongPoints", []),
        )
        self.state.current_question = question
        return question

    def process_answer(self, answer: str, sse_queue: queue.Queue | None = None) -> dict:
        """Thought-Action-Observation: evaluate, adapt depth, decide next question type.

        Returns a dict event for the UI. If sse_queue is provided, pushes streaming
        progress events so the frontend can show real-time feedback.
        """
        # Truncate very long answers to avoid context overflow
        answer = truncate_text(answer, max_chars=3000)

        # Push: evaluating
        if sse_queue:
            sse_queue.put_nowait({"type": "evaluating", "round": self.state.current_round})

        # Action: evaluate
        evaluation = evaluate_answer(
            question=self.state.current_question,
            answer=answer,
            topic=self.state.current_topic,
            depth=self.state.current_depth,
            question_type=self.state.current_question_type,
            weak_points=self.state.weak_points,
        )

        score = int(evaluation.get("score", 5))
        feedback = evaluation.get("briefFeedback", "")
        covered = evaluation.get("coveredWeakness")

        # Push: score ready
        if sse_queue:
            sse_queue.put_nowait({
                "type": "evaluated",
                "round": self.state.current_round,
                "score": score,
                "feedback": feedback,
            })

        # Action: generate detailed feedback for this round (for final report)
        if sse_queue:
            sse_queue.put_nowait({"type": "analyzing", "round": self.state.current_round})
        try:
            detail = generate_detailed_feedback(
                question=self.state.current_question,
                answer=answer,
                score=score,
                topic=self.state.current_topic,
                question_type=self.state.current_question_type,
            )
        except Exception:
            detail = {}

        # Observation: update state
        self.state.rounds.append({
            "roundNumber": self.state.current_round,
            "depth": self.state.current_depth,
            "questionType": self.state.current_question_type,
            "topic": self.state.current_topic,
            "question": self.state.current_question,
            "answer": answer,
            "score": score,
            "briefFeedback": feedback,
            "coveredWeakness": covered,
            "detailedFeedback": detail,
        })

        self.state.asked_topics.append(self.state.current_topic)
        self._track_asked_by_type(self.state.current_question_type, self.state.current_topic)

        if covered and covered != "null" and covered in self.state.weak_points:
            self.state.weak_points.remove(covered)
            self.state.covered_weaknesses.append(covered)

        # Track coding / case_study done
        if self.state.current_question_type == "coding":
            self.state.coding_done = True
        elif self.state.current_question_type == "case_study":
            self.state.case_study_done = True

        # Thought: adapt depth
        if score >= 8:
            self.state.consecutive_high += 1
            self.state.consecutive_low = 0
        elif score <= 5:
            self.state.consecutive_low += 1
            self.state.consecutive_high = 0
        else:
            self.state.consecutive_high = 0
            self.state.consecutive_low = 0

        if self.state.consecutive_high >= 2:
            self.state.current_depth = min(3, self.state.current_depth + 1)
        elif self.state.consecutive_low >= 2:
            self.state.current_depth = max(1, self.state.current_depth - 1)

        # Check completion
        self.state.current_round += 1
        if self.state.current_round > self.state.max_rounds:
            if sse_queue:
                sse_queue.put_nowait({"type": "generating_report"})
            report = self.generate_report()
            return {
                "type": "completed",
                "report": report,
            }

        # Push: deciding next question type
        if sse_queue:
            sse_queue.put_nowait({"type": "deciding_next", "round": self.state.current_round})

        return self._next_question(evaluation, sse_queue)

    # ---- Dynamic question-type selection ----

    def _decide_next_type(self, prev_eval: dict) -> str:
        """Simulate real interviewer behavior: adapt question type based on performance.

        Rules (in priority order):
        1. Non-technical role → NEVER coding (hard constraint)
        2. Coding already done → NEVER coding again (hard constraint)
        3. Second half, technical role, coding not done → coding (exactly once)
        4. Project score was good → keep drilling projects
        5. Project score was weak → pivot to fundamentals
        6. Otherwise → follow LLM's suggestion
        """
        rounds_left = self.state.max_rounds - self.state.current_round + 1
        suggestion = prev_eval.get("nextTypeSuggestion", "project")

        # Rule 1: HARD CONSTRAINT — never allow coding for non-technical roles
        if not self.state.is_technical and suggestion == "coding":
            return self._pick_alternative_type()

        # Rule 2: HARD CONSTRAINT — never allow coding if already done
        if self.state.coding_done and suggestion == "coding":
            return self._pick_alternative_type()

        # Rule 3: coding (tech) or case_study (non-tech) exactly once in second half
        progress = self.state.current_round / self.state.max_rounds
        if 0.5 <= progress <= 0.85 and rounds_left >= 2:
            if self.state.is_technical and not self.state.coding_done:
                return "coding"
            if not self.state.is_technical and not self.state.case_study_done:
                return "case_study"

        # Rule 4 & 5: adapt based on recent performance
        recent_project_scores = [
            r["score"] for r in self.state.rounds[-3:]
            if r["questionType"] == "project"
        ]
        was_project = self.state.current_question_type == "project"

        if was_project and recent_project_scores:
            avg = sum(recent_project_scores) / len(recent_project_scores)
            if avg >= 7:
                return "project"
            if avg <= 5:
                return "fundamentals"

        # Rule 6: follow LLM's suggestion (but respect constraints)
        if suggestion == "coding":
            if self.state.coding_done or not self.state.is_technical:
                return self._pick_alternative_type()
            return "coding"
        if suggestion == "case_study":
            if self.state.case_study_done or self.state.is_technical:
                return self._pick_alternative_type()
            return "case_study"
        if suggestion in ("project", "fundamentals"):
            return suggestion
        # closing → redirect to reasonable alternative
        if suggestion == "closing":
            return self._pick_alternative_type()

        return self._pick_alternative_type()

    def _pick_alternative_type(self) -> str:
        """Pick between project and fundamentals based on what's been asked less."""
        n_project = len(self.state.asked_project_topics)
        n_fund = len(self.state.asked_fundamentals_topics)
        if n_project <= n_fund:
            return "project"
        return "fundamentals"

    def _next_question(self, evaluation: dict = None, sse_queue: queue.Queue | None = None) -> dict:
        """Generate next question with dynamic type selection."""
        qtype = self._decide_next_type(evaluation or {})
        self.state.current_question_type = qtype

        # Push: question type decided
        if sse_queue:
            sse_queue.put_nowait({
                "type": "question_type_decided",
                "round": self.state.current_round,
                "questionType": qtype,
            })

        # Pick topic for this type
        topic = self._pick_topic_for_type(qtype)
        self.state.current_topic = topic

        # Set appropriate depth
        if qtype in ("coding", "case_study"):
            self.state.current_depth = max(self.state.current_depth, 2)
        elif qtype == "fundamentals":
            # Fundamentals can start at depth 1 if transitioning from poor project perf
            if self._was_last_question_project():
                self.state.current_depth = 1
            self.state.current_depth = max(1, self.state.current_depth)

        if sse_queue:
            sse_queue.put_nowait({
                "type": "generating_question",
                "round": self.state.current_round,
                "questionType": qtype,
                "topic": topic,
            })

        question = generate_question(
            topic=topic,
            depth=self.state.current_depth,
            round_num=self.state.current_round,
            max_rounds=self.state.max_rounds,
            question_type=qtype,
            prev_answer=self.state.rounds[-1]["answer"] if self.state.rounds else "",
            asked_topics=self.state.asked_topics,
            weak_points=self.state.weak_points,
            jd_summary=self.state.jd.get("summary", ""),
            jd_level=self.state.jd.get("level", ""),
            resume_summary=self.state.resume.get("summary", ""),
            interview_exp_context=self.state.interview_exp_context,
        )
        self.state.current_question = question

        return {
            "type": "question",
            "round": self.state.current_round,
            "depth": self.state.current_depth,
            "questionType": qtype,
            "content": question,
            "evaluation": self._last_eval(),
        }

    def _was_last_question_project(self) -> bool:
        if not self.state.rounds:
            return True
        return self.state.rounds[-1]["questionType"] == "project"

    def _last_eval(self) -> dict | None:
        if not self.state.rounds:
            return None
        last = self.state.rounds[-1]
        return {"score": last["score"], "feedback": last["briefFeedback"]}

    def _pick_topic_for_type(self, qtype: str) -> str:
        """Pick next topic to examine based on question type."""
        if qtype == "project":
            pool = [t for t in self.state.must_ask_projects if t not in self.state.asked_project_topics]
            if not pool:
                pool = self.state.must_ask_projects
            if pool:
                return pool[0]
            return "项目经验深挖"

        elif qtype == "fundamentals":
            pool = [t for t in self.state.must_ask_fundamentals if t not in self.state.asked_fundamentals_topics]
            if not pool:
                pool = self.state.must_ask_fundamentals
            if pool:
                return pool[0]
            # 兜底话题：根据岗位类型选择不同的领域
            if self.state.is_technical:
                fallbacks = [
                    "数据结构与算法",
                    "操作系统核心概念",
                    "计算机网络基础",
                    "数据库原理与优化",
                    "Python/Go语言底层原理",
                    "大模型基础架构(Transformer/Attention)",
                    "RAG系统设计与优化",
                    "Agent范式对比(ReAct/Tool Use/Plan-Execute)",
                    "Prompt Engineering最佳实践",
                    "系统设计方法论",
                ]
            else:
                fallbacks = [
                    "产品方法论与思维框架",
                    "数据分析与驱动决策",
                    "用户研究与人种志方法",
                    "竞品分析与市场洞察",
                    "需求管理与优先级排序",
                    "跨部门协作与沟通",
                    "设计原则与交互规范",
                    "用户流程与信息架构",
                    "增长策略与运营体系",
                    "商业模型与价值分析",
                ]
            for f in fallbacks:
                if f not in self.state.asked_fundamentals_topics:
                    return f
            return "领域基础综合"

        elif qtype == "coding":
            # coding轮统一手撕LeetCode算法题，不使用cross_analyze的mustAskCoding(可能被填成"系统设计")
            leetcode_topics = [
                "数组与哈希表",
                "字符串处理",
                "二叉树与遍历",
                "链表操作",
                "动态规划",
                "贪心算法",
                "回溯算法",
                "BFS与DFS",
                "堆栈与队列",
                "滑动窗口",
                "双指针",
                "排序与搜索",
            ]
            pool = [t for t in leetcode_topics if t not in self.state.asked_coding_topics]
            return pool[0] if pool else "数组与哈希表"

        elif qtype == "case_study":
            pool = [t for t in self.state.must_ask_case_studies if t not in self.state.asked_case_study_topics]
            if not pool:
                pool = self.state.must_ask_case_studies
            if pool:
                return pool[0]
            # 非技术岗case study兜底话题
            fallbacks = [
                "产品功能诊断与优化",
                "市场进入策略分析",
                "用户增长与留存",
                "竞品分析与差异化",
                "业务流程优化",
                "数据指标异常归因",
                "商业化与盈利模型",
                "产品功能从0到1设计",
                "跨部门协作与资源分配",
            ]
            for f in fallbacks:
                if f not in self.state.asked_case_study_topics:
                    return f
            return "综合案例分析"

        return "综合能力评估"

    def _track_asked_by_type(self, qtype: str, topic: str):
        if qtype == "project":
            self.state.asked_project_topics.append(topic)
        elif qtype == "fundamentals":
            self.state.asked_fundamentals_topics.append(topic)
        elif qtype == "coding":
            self.state.asked_coding_topics.append(topic)
        elif qtype == "case_study":
            self.state.asked_case_study_topics.append(topic)

    def generate_report(self) -> dict:
        """Generate comprehensive post-interview report with LLM deep analysis."""
        self.state.status = "completed"
        rounds = self.state.rounds
        if not rounds:
            return {
                "sessionId": self.state.session_id,
                "totalRounds": 0,
                "rounds": [],
                "metrics": {
                    "overallScore": 0,
                    "weaknessCoverage": 0,
                    "depthAdaptability": None,
                    "knowledgeAuthenticity": None,
                    "improvementTrajectory": 0,
                },
                "weakPointsRemaining": self.state.weak_points,
                "weakPointsCovered": [],
                "llmReport": {
                    "overallVerdict": "面试未进行任何问答，无法生成复盘报告。",
                    "strengthsSummary": [],
                    "weaknessesSummary": [],
                    "detailedRoundAnalysis": [],
                    "improvementPlan": [],
                    "nextInterviewPrep": {},
                },
            }

        scores = [r["score"] for r in rounds]
        avg_score = sum(scores) / len(scores)

        depth3_rounds = [r for r in rounds if r["depth"] >= 3]
        depth3_avg = sum(r["score"] for r in depth3_rounds) / len(depth3_rounds) if depth3_rounds else None

        resume_rounds = [r for r in rounds if r["questionType"] == "project"]
        resume_avg = sum(r["score"] for r in resume_rounds) / len(resume_rounds) if resume_rounds else None

        total_weak = len(self.state.covered_weaknesses) + len(self.state.weak_points)
        coverage = len(self.state.covered_weaknesses) / total_weak if total_weak > 0 else 1.0

        first3 = scores[:3]
        last3 = scores[-3:] if len(scores) >= 6 else scores
        trajectory = sum(last3) / len(last3) - sum(first3) / len(first3)

        rounds_lines = []
        for r in rounds:
            rounds_lines.append(
                f"第{r['roundNumber']}轮 [{r['questionType']}] [{r['topic']}] 深度{r['depth']} 得分{r['score']}/10\n"
                f"Q: {r['question']}\n"
                f"A: {r['answer']}\n"
            )
        rounds_detail = "\n---\n".join(rounds_lines)

        try:
            llm_report = generate_final_report(
                resume_summary=self.state.resume.get("summary", ""),
                jd_summary=self.state.jd.get("summary", ""),
                rounds_detail=rounds_detail,
            )
        except Exception as e:
            print(f"[report] LLM final report failed: {e}", file=__import__('sys').stderr)
            llm_report = {}
            # Build fallback from per-round detailed feedback
            fallback_rounds = []
            for r in rounds:
                detail = r.get("detailedFeedback", {})
                fallback_rounds.append({
                    "roundNumber": r["roundNumber"],
                    "questionType": r["questionType"],
                    "topic": r["topic"],
                    "score": r["score"],
                    "briefRecap": r.get("briefFeedback", ""),
                    "gapAnalysis": (detail.get("whatWasMissing") or ["无详细分析"])[0] if detail.get("whatWasMissing") else "",
                    "thinkingFramework": detail.get("modelAnswerOutline", [""])[0] if detail.get("modelAnswerOutline") else "",
                    "modelResponse": detail.get("modelAnswerOutline") or detail.get("keyTakeaways") or [],
                })
            llm_report = {
                "overallVerdict": f"面试综合评分 {round(avg_score, 1)}/10",
                "detailedRoundAnalysis": fallback_rounds,
                "improvementPlan": [],
                "nextInterviewPrep": {},
            }

        return {
            "sessionId": self.state.session_id,
            "totalRounds": len(rounds),
            "rounds": rounds,
            "metrics": {
                "overallScore": round(avg_score, 1),
                "weaknessCoverage": round(coverage * 100, 1),
                "depthAdaptability": round(depth3_avg, 1) if depth3_avg else None,
                "knowledgeAuthenticity": round(resume_avg, 1) if resume_avg else None,
                "improvementTrajectory": round(trajectory, 1),
            },
            "weakPointsRemaining": self.state.weak_points,
            "weakPointsCovered": self.state.covered_weaknesses,
            "llmReport": llm_report,
        }
