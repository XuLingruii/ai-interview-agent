"""FastAPI + SSE backend for the interview simulation agent.

API:
  POST /api/interview/start       — init session, return analysis + first question
  POST /api/interview/answer      — submit answer, return evaluation + next question
  GET  /api/interview/chat        — SSE stream for real-time interview flow
  GET  /api/interview/report/{sid}— get final report

CLI mode: python main.py --cli
"""

import sys
import json
import asyncio
import traceback
import io
import queue
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import uvicorn

from agent_loop import AgentLoop
from tools import evaluate_answer
from session_store import create_session, get_session, update_session, save_report, get_report, list_sessions, delete_session


# ============================================================
# Data models
# ============================================================

class StartRequest(BaseModel):
    resume: str
    jd: str
    maxRounds: int = 8


class AnswerRequest(BaseModel):
    sessionId: str
    answer: str


# ============================================================
# App setup
# ============================================================

from fastapi import Request
from fastapi.responses import JSONResponse as FastJSONResponse

app = FastAPI(title="AI Interview Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return all errors as JSON, never HTML."""
    traceback.print_exc()
    return FastJSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

# Thread-safe queues per session for SSE coordination
_queues: dict[str, queue.Queue] = {}


def _serialize_state(agent: AgentLoop) -> dict:
    """Serialize the agent state for storage."""
    return {
        "resume": agent.state.resume,
        "jd": agent.state.jd,
        "analysis": agent.state.analysis,
        "rounds": agent.state.rounds,
        "currentRound": agent.state.current_round,
        "maxRounds": agent.state.max_rounds,
        "currentDepth": agent.state.current_depth,
        "currentQuestionType": agent.state.current_question_type,
        "status": agent.state.status,
        "weakPoints": agent.state.weak_points,
        "coveredWeaknesses": agent.state.covered_weaknesses,
        "askedTopics": agent.state.asked_topics,
        "consecutiveHigh": agent.state.consecutive_high,
        "consecutiveLow": agent.state.consecutive_low,
        "currentQuestion": agent.state.current_question,
        "currentTopic": agent.state.current_topic,
        "mustAskProjects": agent.state.must_ask_projects,
        "mustAskFundamentals": agent.state.must_ask_fundamentals,
        "mustAskCoding": agent.state.must_ask_coding,
        "mustAskCaseStudies": agent.state.must_ask_case_studies,
        "codingDone": agent.state.coding_done,
        "caseStudyDone": agent.state.case_study_done,
        "isTechnical": agent.state.is_technical,
        "interviewExpContext": agent.state.interview_exp_context,
        "askedProjectTopics": agent.state.asked_project_topics,
        "askedFundamentalsTopics": agent.state.asked_fundamentals_topics,
        "askedCodingTopics": agent.state.asked_coding_topics,
        "askedCaseStudyTopics": agent.state.asked_case_study_topics,
    }


def _deserialize_state(data: dict, agent: AgentLoop):
    """Restore agent state from storage."""
    s = agent.state
    s.resume = data.get("resume", {})
    s.jd = data.get("jd", {})
    s.analysis = data.get("analysis", {})
    s.rounds = data.get("rounds", [])
    s.current_round = data.get("currentRound", 0)
    s.max_rounds = data.get("maxRounds", 8)
    s.current_depth = data.get("currentDepth", 1)
    s.current_question_type = data.get("currentQuestionType", "project")
    s.status = data.get("status", "ready")
    s.weak_points = data.get("weakPoints", [])
    s.covered_weaknesses = data.get("coveredWeaknesses", [])
    s.asked_topics = data.get("askedTopics", [])
    s.consecutive_high = data.get("consecutiveHigh", 0)
    s.consecutive_low = data.get("consecutiveLow", 0)
    s.current_question = data.get("currentQuestion", "")
    s.current_topic = data.get("currentTopic", "")
    s.must_ask_projects = data.get("mustAskProjects", [])
    s.must_ask_fundamentals = data.get("mustAskFundamentals", [])
    s.must_ask_coding = data.get("mustAskCoding", [])
    s.must_ask_case_studies = data.get("mustAskCaseStudies", [])
    s.coding_done = data.get("codingDone", False)
    s.case_study_done = data.get("caseStudyDone", False)
    s.is_technical = data.get("isTechnical", True)
    s.interview_exp_context = data.get("interviewExpContext", "")
    s.asked_project_topics = data.get("askedProjectTopics", [])
    s.asked_fundamentals_topics = data.get("askedFundamentalsTopics", [])
    s.asked_coding_topics = data.get("askedCodingTopics", [])
    s.asked_case_study_topics = data.get("askedCaseStudyTopics", [])


# ============================================================
# REST Endpoints
# ============================================================

@app.post("/api/parse-resume")
async def parse_resume_pdf(file: UploadFile = File(...)):
    """Upload a PDF resume and extract its text content."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext == '.pdf':
        try:
            import pdfplumber
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="pdfplumber 未安装，请运行: pip install pdfplumber"
            )
        try:
            contents = await file.read()
            text_parts = []
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            text = '\n'.join(text_parts)
            if not text.strip():
                raise HTTPException(status_code=400, detail="PDF中未提取到文字，可能是扫描件或图片型PDF")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF解析失败: {e}")
    elif ext in ('.txt', '.md'):
        contents = await file.read()
        text = contents.decode('utf-8')
    else:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，请上传PDF/TXT/MD")

    return {"filename": file.filename, "text": text, "charCount": len(text)}


@app.post("/api/interview/start")
async def start_interview(req: StartRequest):
    """Initialize a new interview session. Returns analysis + first question."""
    agent = AgentLoop(max_rounds=req.maxRounds)
    try:
        result = agent.initialize(req.resume, req.jd)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失败: {e}")

    # Start the interview to get the first question
    first_question = agent.start_interview()

    # Persist session
    state_dict = _serialize_state(agent)
    session_id = create_session(state_dict)
    agent.state.session_id = session_id
    # Update with session_id
    update_session(session_id, _serialize_state(agent))

    return {
        "sessionId": session_id,
        "maxRounds": req.maxRounds,
        "analysis": {
            "resume": result["resume"],
            "jd": result["jd"],
            "matchScore": result["analysis"].get("matchScore", 0),
            "strongPoints": result["analysis"].get("strongPoints", []),
            "weakPoints": result["analysis"].get("weakPoints", []),
            "mustAskProjects": result["analysis"].get("mustAskProjects", []),
            "mustAskFundamentals": result["analysis"].get("mustAskFundamentals", []),
            "mustAskCoding": result["analysis"].get("mustAskCoding", []),
        },
        "firstQuestion": {
            "round": 1,
            "depth": agent.state.current_depth,
            "questionType": agent.state.current_question_type,
            "topic": agent.state.current_topic,
            "content": first_question,
        },
    }


@app.post("/api/interview/answer")
async def submit_answer(req: AnswerRequest):
    """Submit an answer and get evaluation + next question (or completion)."""
    # Load session
    state_dict = get_session(req.sessionId)
    if not state_dict:
        raise HTTPException(status_code=404, detail="Session not found")

    # Reconstruct agent
    agent = AgentLoop(max_rounds=state_dict.get("maxRounds", 8))
    _deserialize_state(state_dict, agent)
    agent.state.session_id = req.sessionId

    if agent.state.status == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    # Process answer in thread so SSE consumer can receive events during LLM calls
    q = _queues.get(req.sessionId)
    result = await asyncio.to_thread(agent.process_answer, req.answer, sse_queue=q)

    # Persist updated state
    update_session(req.sessionId, _serialize_state(agent))

    # Push to SSE queue if one is listening
    q = _queues.get(req.sessionId)
    if q:
        await q.put(result)

    if result["type"] == "completed":
        save_report(req.sessionId, result["report"])
        return {
            "status": "completed",
            "evaluation": {
                "score": agent.state.rounds[-1]["score"],
                "briefFeedback": agent.state.rounds[-1]["briefFeedback"],
            } if agent.state.rounds else None,
            "report": result["report"],
        }

    return {
        "status": "in_progress",
        "evaluation": {
            "score": agent.state.rounds[-1]["score"],
            "briefFeedback": agent.state.rounds[-1]["briefFeedback"],
        } if agent.state.rounds else None,
        "nextQuestion": {
            "round": result["round"],
            "depth": result["depth"],
            "questionType": result.get("questionType", agent.state.current_question_type),
            "topic": agent.state.current_topic,
            "content": result["content"],
        },
    }


@app.post("/api/interview/end")
async def end_interview(req: AnswerRequest):
    """End interview early and get a partial report."""
    state_dict = get_session(req.sessionId)
    if not state_dict:
        raise HTTPException(status_code=404, detail="Session not found")

    agent = AgentLoop(max_rounds=state_dict.get("maxRounds", 8))
    _deserialize_state(state_dict, agent)
    agent.state.session_id = req.sessionId

    # Save last answer if provided
    if req.answer.strip():
        evaluation = evaluate_answer(
            question=agent.state.current_question,
            answer=req.answer,
            topic=agent.state.current_topic,
            depth=agent.state.current_depth,
            question_type=agent.state.current_question_type,
            weak_points=agent.state.weak_points,
        )
        agent.state.rounds.append({
            "roundNumber": agent.state.current_round,
            "depth": agent.state.current_depth,
            "questionType": agent.state.current_question_type,
            "topic": agent.state.current_topic,
            "question": agent.state.current_question,
            "answer": req.answer,
            "score": int(evaluation.get("score", 5)),
            "briefFeedback": evaluation.get("briefFeedback", "面试提前结束"),
            "coveredWeakness": evaluation.get("coveredWeakness"),
            "detailedFeedback": {},
        })

    report = agent.generate_report()
    update_session(req.sessionId, _serialize_state(agent))
    save_report(req.sessionId, report)
    return {"status": "ended_early", "report": report}


@app.get("/api/interview/chat")
async def interview_chat(sessionId: str = Query(...)):
    """SSE endpoint for streaming the interview flow.

    Connect after POST /start to receive the first question.
    Then POST /answer to submit, and this stream will emit evaluation + next question.
    """

    # Load session
    state_dict = get_session(sessionId)
    if not state_dict:
        raise HTTPException(status_code=404, detail="Session not found")

    agent = AgentLoop(max_rounds=state_dict.get("maxRounds", 8))
    _deserialize_state(state_dict, agent)
    agent.state.session_id = sessionId

    # Create queue for this session (thread-safe sync queue used with asyncio.to_thread)
    q: queue.Queue = queue.Queue()
    _queues[sessionId] = q

    loop = asyncio.get_event_loop()

    async def event_stream():
        try:
            # NOTE: first question is delivered via POST /start response.
            # SSE only streams events from POST /answer onwards.

            # Stream subsequent events
            while agent.state.status != "completed":
                # Wait for a new event from POST /answer (uses sync queue with run_in_executor)
                try:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, q.get), timeout=600
                    )
                except asyncio.TimeoutError:
                    yield {
                        "event": "timeout",
                        "data": json.dumps({"type": "timeout", "message": "Session timed out"}, ensure_ascii=False),
                    }
                    break

                ev_type = result.get("type", "")
                if ev_type in ("evaluating", "evaluated", "analyzing", "deciding_next",
                               "generating_question", "question_type_decided", "generating_report"):
                    yield {
                        "event": ev_type,
                        "data": json.dumps(result, ensure_ascii=False),
                    }

                elif ev_type == "question":
                    yield {
                        "event": "question",
                        "data": json.dumps({
                            "type": "question",
                            "round": result["round"],
                            "depth": result["depth"],
                            "questionType": result.get("questionType", ""),
                            "topic": agent.state.current_topic,
                            "content": result["content"],
                            "evaluation": result.get("evaluation"),
                        }, ensure_ascii=False),
                    }

                elif ev_type == "completed":
                    save_report(sessionId, result["report"])
                    yield {
                        "event": "completed",
                        "data": json.dumps({
                            "type": "completed",
                            "evaluation": {
                                "score": agent.state.rounds[-1]["score"],
                                "briefFeedback": agent.state.rounds[-1]["briefFeedback"],
                            } if agent.state.rounds else None,
                            "report": result["report"],
                        }, ensure_ascii=False),
                    }
                    break
        finally:
            _queues.pop(sessionId, None)

    return EventSourceResponse(event_stream())


@app.get("/api/interview/report/{sessionId}")
async def get_report_endpoint(sessionId: str):
    """Get the final report for a completed interview."""
    report = get_report(sessionId)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/history")
async def list_history():
    """List all past interview sessions with summary info."""
    return list_sessions()


@app.delete("/api/history/{sessionId}")
async def delete_history(sessionId: str):
    """Delete a session and its data."""
    if delete_session(sessionId):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="Session not found")


# ============================================================
# CLI mode (python main.py --cli)
# ============================================================


def run_cli():
    print("=" * 60)
    print("   AI 面试模拟 Agent — 基于 ReAct 范式")
    print("   命令行验证模式")
    print("=" * 60)
    print()

    print("请粘贴简历内容 (输入空行结束):")
    resume_lines = []
    while True:
        line = input()
        if line == "":
            break
        resume_lines.append(line)
    if not resume_lines:
        print("错误: 必须提供简历内容")
        return
    resume = "\n".join(resume_lines)

    print("\n请粘贴JD内容 (输入空行结束):")
    jd_lines = []
    while True:
        line = input()
        if line == "":
            break
        jd_lines.append(line)
    if not jd_lines:
        print("错误: 必须提供JD内容")
        return
    jd = "\n".join(jd_lines)

    max_rounds_str = input("\n面试轮数 (默认8): ").strip()
    max_rounds = int(max_rounds_str) if max_rounds_str else 8

    print("\n[Agent] 正在分析简历和JD...\n")
    agent = AgentLoop(max_rounds=max_rounds)
    try:
        analysis_result = agent.initialize(resume, jd)
    except RuntimeError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        traceback.print_exc()
        sys.exit(1)

    analysis = analysis_result["analysis"]
    print(f"  简历画像: {analysis_result['resume'].get('summary', 'N/A')}")
    print(f"  JD摘要: {analysis_result['jd'].get('summary', 'N/A')}")
    print(f"  匹配度: {analysis.get('matchScore', 'N/A')}/100")
    print(f"  优势: {', '.join(analysis.get('strongPoints', []))}")
    print(f"  薄弱点: {', '.join(analysis.get('weakPoints', []))}")
    print(f"  必问项目: {', '.join(analysis.get('mustAskProjects', []))}")
    print(f"  必问八股: {', '.join(analysis.get('mustAskFundamentals', []))}")
    print(f"  必问算法: {', '.join(analysis.get('mustAskCoding', []))}")
    print(f"\n  (题目类型将根据回答表现动态调整)\n")
    print(f"  ReAct循环开始，共{max_rounds}轮\n")
    print("-" * 60)

    question = agent.start_interview()
    for _ in range(max_rounds):
        qtype = agent.state.current_question_type
        d = agent.state.current_depth
        type_label = {"project": "项目深挖", "fundamentals": "基础八股", "coding": "代码手撕", "case_study": "案例分析"}
        depth_label = {1: "基础摸底", 2: "深入追问", 3: "压力测试"}

        rn = agent.state.current_round
        print(f"\n[第{rn}轮 · {type_label.get(qtype, qtype)} · {depth_label.get(d, '深度'+str(d))}]")
        print(f"[考察: {agent.state.current_topic}]")
        print(f"\n🤖 面试官: {question}\n")

        answer = input("👤 你: ").strip()
        while not answer:
            print("请至少输入一些内容...")
            answer = input("👤 你: ").strip()

        result = agent.process_answer(answer)
        if result["type"] == "completed":
            last = agent.state.rounds[-1]
            print(f"\n  → 评分: {last['score']}/10")
            print(f"  → 反馈: {last['briefFeedback']}")
            print("\n" + "=" * 60)
            print("   面试结束！正在生成深度复盘报告...")
            print("=" * 60)
            print_report(result["report"])
            break

        last = agent.state.rounds[-1]
        print(f"\n  → 评分: {last['score']}/10")
        print(f"  → 反馈: {last['briefFeedback']}")
        question = result["content"]
        nqt = result.get("questionType", "project")
        nd = result["depth"]
        print(f"\n[下一轮 → {type_label.get(nqt, nqt)} · {depth_label.get(nd, '深度'+str(nd))}]")

    print("\n感谢使用 AI 面试模拟 Agent！")


def print_report(report: dict):
    m = report["metrics"]
    llm = report.get("llmReport", {})
    print(f"\n{'='*50}")
    print("  📋 完整复盘报告")
    print(f"{'='*50}")
    print(f"  总轮次: {report['totalRounds']}")
    print(f"  综合评分: {m['overallScore']}/10")
    print(f"  薄弱点覆盖率: {m['weaknessCoverage']}%")
    if m.get("depthAdaptability"):
        print(f"  深度适应性: {m['depthAdaptability']}/10")
    if m.get("knowledgeAuthenticity"):
        print(f"  知识真实度: {m['knowledgeAuthenticity']}/10")
    print(f"  提升轨迹: {m['improvementTrajectory']:+.1f}")

    if llm.get("overallVerdict"):
        print(f"\n  综合评价: {llm['overallVerdict']}")
    if llm.get("strengthsSummary"):
        print(f"\n  ✅ 整体优势:")
        for s in llm["strengthsSummary"]:
            print(f"     + {s}")
    if llm.get("weaknessesSummary"):
        print(f"\n  ⚠️  主要短板:")
        for w in llm["weaknessesSummary"]:
            print(f"     - {w}")

    print(f"\n{'─'*50}")
    print("  📝 逐题深度分析")
    print(f"{'─'*50}")

    llm_rounds = llm.get("detailedRoundAnalysis", [])
    llm_by_round = {r["roundNumber"]: r for r in llm_rounds} if llm_rounds else {}

    for r in report["rounds"]:
        rn = r["roundNumber"]
        type_label = {"project": "项目深挖", "fundamentals": "基础八股", "coding": "代码手撕", "case_study": "案例分析"}
        qtype = r.get("questionType", "project")
        print(f"\n  ┌─ Q{rn} [{type_label.get(qtype, qtype)} · {r['topic']}] — {r['score']}/10")

        lr = llm_by_round.get(rn, {})
        if lr.get("gapAnalysis"):
            print(f"  │ 🔍 {lr['gapAnalysis'][:150]}")
        if lr.get("thinkingFramework"):
            print(f"  │ 💡 思维框架: {lr['thinkingFramework'][:150]}")
        if lr.get("modelResponse"):
            print(f"  │ 📖 理想回答要点:")
            points = lr["modelResponse"] if isinstance(lr["modelResponse"], list) else [lr["modelResponse"]]
            for p in points[:3]:
                print(f"  │    • {str(p)[:120]}")

        detail = r.get("detailedFeedback", {})
        if detail.get("whatWasMissing"):
            print(f"  │ 👎 遗漏: {', '.join(detail['whatWasMissing'][:2])}")
        if detail.get("recommendedResources"):
            print(f"  │ 📚 {', '.join(detail['recommendedResources'][:2])}")
        print(f"  └─")

    if llm.get("improvementPlan"):
        print(f"\n{'─'*50}")
        print("  🎯 提升计划")
        print(f"{'─'*50}")
        for plan in llm["improvementPlan"][:5]:
            print(f"\n  [{plan.get('priority', '?')}优先级] {plan.get('area', '')}")
            for item in (plan.get("actionItems") or [])[:2]:
                print(f"      → {item}")

    nxt = llm.get("nextInterviewPrep", {})
    if nxt.get("focusAreas"):
        print(f"\n  🔜 下次面试重点:")
        for f in nxt["focusAreas"]:
            print(f"    → {f}")


if __name__ == "__main__":
    if "--cli" in sys.argv:
        run_cli()
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
