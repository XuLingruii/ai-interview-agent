"""Session and report storage using JSON files under data/ directory."""

import json
import uuid
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    return DATA_DIR / f"{session_id}.json"


def create_session(state_dict: dict) -> str:
    """Persist interview state and return session ID."""
    _ensure_data_dir()
    session_id = uuid.uuid4().hex[:12]
    doc = {
        "sessionId": session_id,
        "createdAt": datetime.now().isoformat(),
        "state": state_dict,
    }
    with open(_session_path(session_id), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return session_id


def get_session(session_id: str) -> dict | None:
    """Load interview state by session ID."""
    path = _session_path(session_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return doc["state"]


def update_session(session_id: str, state_dict: dict):
    """Update interview state for an existing session."""
    path = _session_path(session_id)
    doc = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    doc["state"] = state_dict
    doc["updatedAt"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def save_report(session_id: str, report: dict):
    """Save the final report for a session."""
    path = _session_path(session_id)
    doc = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    doc["report"] = report
    doc["completedAt"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def get_report(session_id: str) -> dict | None:
    """Get the saved report for a session."""
    path = _session_path(session_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return doc.get("report")


def list_sessions() -> list[dict]:
    """List all sessions with summary info, newest first."""
    _ensure_data_dir()
    sessions = []
    for path in sorted(DATA_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            continue
        sid = doc.get("sessionId", path.stem)
        state = doc.get("state", {})
        report = doc.get("report", {})
        rounds = state.get("rounds", [])
        metrics = report.get("metrics", {})
        sessions.append({
            "sessionId": sid,
            "createdAt": doc.get("createdAt", ""),
            "completedAt": doc.get("completedAt", ""),
            "totalRounds": len(rounds),
            "maxRounds": state.get("maxRounds", 0),
            "overallScore": metrics.get("overallScore"),
            "weaknessCoverage": metrics.get("weaknessCoverage"),
            "status": "completed" if report else state.get("status", "unknown"),
        })
    return sessions


def delete_session(session_id: str) -> bool:
    """Delete a session and its data file. Returns True if deleted."""
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False
