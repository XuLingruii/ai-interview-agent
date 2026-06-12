"""Web search utility for fetching interview experiences (面经) via DuckDuckGo.

Free, no API key required. Falls back silently on failure so the interview
flow is never blocked by search issues.
"""

import sys
import time


def search_interview_experiences(company: str, position: str, max_results: int = 5) -> str:
    """Search for interview experiences related to a company + position.

    Returns a plain-text summary of top search results, or empty string on failure.
    """
    if not company or company == "未知企业":
        return ""

    query = f"{company} {position} 面经 面试题"
    results = []

    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                if title and body:
                    results.append(f"- [{title}]({href})\n  {body[:300]}")
    except ImportError:
        print("[web_search] ddgs not installed, skipping", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"[web_search] Search failed: {e}", file=sys.stderr)
        return ""

    if not results:
        return ""

    summary = f"以下是从网络搜索到的 {company} {position} 相关面经参考：\n" + "\n".join(results)
    return summary
