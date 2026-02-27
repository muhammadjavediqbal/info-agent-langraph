"""
Web Search Tool using Tavily
"""

import os
from langchain_core.tools import tool

try:
    import streamlit as st
    api_key = st.secrets["TAVILY_API_KEY"]
except Exception:
    api_key = os.environ.get("TAVILY_API_KEY", "")

try:
    from tavily import TavilyClient
except ImportError:
    raise ImportError("Run: pip install tavily-python")


@tool
def search_web(query: str) -> str:
    """
    Search the web for current information, news, or facts.

    Args:
        query: The search query string.

    Returns:
        Top search results as a formatted string.
    """
    # Read from st.secrets (Streamlit Cloud) with os.environ fallback (local)
    try:
        import streamlit as st
        api_key = st.secrets.get("TAVILY_API_KEY", os.environ.get("TAVILY_API_KEY", ""))
    except Exception:
        api_key = os.environ.get("TAVILY_API_KEY", "")

    if not api_key:
        return "Search unavailable: TAVILY_API_KEY not set."

    client = TavilyClient(api_key=api_key)

    try:
        response = client.search(query, max_results=3)

        results_list = (
            response.get("results", [])
            if isinstance(response, dict)
            else response
            if isinstance(response, list)
            else []
        )

        if not results_list:
            return f"No results found for: '{query}'"

        formatted = []
        for i, r in enumerate(results_list[:3], 1):
            if isinstance(r, dict):
                title   = r.get("title", "").strip()
                content = r.get("content", r.get("snippet", "")).strip()
                url     = r.get("url", "").strip()
                parts   = [p for p in [title, content, url] if p]
                if parts:
                    formatted.append(f"[{i}] " + "\n    ".join(parts))
            elif isinstance(r, str) and r.strip():
                formatted.append(f"[{i}] {r.strip()}")

        return "\n\n".join(formatted) if formatted else f"No usable results for: '{query}'"

    except Exception as e:
        return f"Search error: {e}"
