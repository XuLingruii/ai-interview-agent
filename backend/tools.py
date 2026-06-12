"""Tool functions for the interview agent. Each tool calls DeepSeek with a specific prompt."""

import json

from llm_client import chat, chat_json
from prompt_templates import (
    PARSE_RESUME,
    PARSE_JD,
    CROSS_ANALYZE,
    GENERATE_QUESTION,
    GENERATE_FIRST_QUESTION,
    EVALUATE_ANSWER,
    GENERATE_DETAILED_FEEDBACK,
    GENERATE_FINAL_REPORT,
)


def parse_resume(text: str) -> dict:
    return chat_json("你是一位专业的简历分析专家。请严格按照JSON格式返回分析结果。", PARSE_RESUME.format(resume=text))


def parse_jd(text: str) -> dict:
    return chat_json("你是一位专业的岗位分析专家。请严格按照JSON格式返回分析结果。", PARSE_JD.format(jd=text))


def cross_analyze(resume_analysis: dict, jd_analysis: dict, interview_exp_context: str = "") -> dict:
    return chat_json(
        "你是一位专业的面试策略专家。请严格按照JSON格式返回分析结果。",
        CROSS_ANALYZE.format(
            resume_analysis=json.dumps(resume_analysis, ensure_ascii=False, indent=2),
            jd_analysis=json.dumps(jd_analysis, ensure_ascii=False, indent=2),
            interview_exp_context=interview_exp_context or "（无相关面经参考）",
        ),
    )


def generate_first_question(
    resume_summary: str, jd_summary: str, must_ask_projects: list, strong_points: list
) -> str:
    return chat(
        "你是一位友好的资深面试官，正在进行面试第一轮。只输出问题本身。",
        GENERATE_FIRST_QUESTION.format(
            resume_summary=resume_summary,
            jd_summary=jd_summary,
            must_ask_projects=", ".join(must_ask_projects),
            strong_points=", ".join(strong_points),
        ),
    )


def generate_question(
    topic: str,
    depth: int,
    round_num: int,
    max_rounds: int,
    question_type: str,
    prev_answer: str,
    asked_topics: list,
    weak_points: list,
    jd_summary: str = "",
    jd_level: str = "",
    resume_summary: str = "",
    interview_exp_context: str = "",
) -> str:
    return chat(
        "你是一位专业的资深面试官。请只输出面试问题本身，不要加任何前缀或解释。",
        GENERATE_QUESTION.format(
            round_num=round_num,
            max_rounds=max_rounds,
            depth=depth,
            question_type=question_type,
            topic=topic,
            asked_topics=", ".join(asked_topics) if asked_topics else "无",
            weak_points=", ".join(weak_points) if weak_points else "无",
            prev_answer=prev_answer if prev_answer else "这是第一轮，无上一轮回答",
            jd_summary=jd_summary or "未提供",
            jd_level=jd_level or "未指定",
            resume_summary=resume_summary or "未提供",
            interview_exp_context=interview_exp_context or "",
        ),
    )


def evaluate_answer(
    question: str, answer: str, topic: str, depth: int, question_type: str, weak_points: list
) -> dict:
    return chat_json(
        "你是一位严格的面试评分官。请严格按照JSON格式返回评估结果。",
        EVALUATE_ANSWER.format(
            question=question,
            answer=answer,
            topic=topic,
            depth=depth,
            question_type=question_type,
            weak_points=", ".join(weak_points) if weak_points else "无",
        ),
    )


def generate_detailed_feedback(
    question: str, answer: str, score: int, topic: str, question_type: str
) -> dict:
    """Generate deep detailed feedback for a single round, used in the final report."""
    return chat_json(
        "你是一位资深面试复盘专家。请严格按照JSON格式返回详细分析。",
        GENERATE_DETAILED_FEEDBACK.format(
            question_type=question_type,
            question=question,
            answer=answer,
            score=score,
            topic=topic,
        ),
    )


def generate_final_report(resume_summary: str, jd_summary: str, rounds_detail: str) -> dict:
    """Generate the comprehensive post-interview report."""
    return chat_json(
        "你是一位资深面试复盘专家。请严格按照JSON格式返回完整的复盘报告。",
        GENERATE_FINAL_REPORT.format(
            resume_summary=resume_summary,
            jd_summary=jd_summary,
            rounds_detail=rounds_detail,
        ),
    )
