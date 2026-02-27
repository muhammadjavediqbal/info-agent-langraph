"""
Production-Ready LangGraph ReAct Agent
LLM: OpenRouter (OpenAI-compatible)
Model: Meta LLaMA 3.1 8B Instruct
"""

import os
import re
from typing import Annotated, TypedDict, Literal

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
)
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from calculator import calculator
from weather import get_weather
from search import search_web

# ─────────────────────────────────────────────
# 1. STATE
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iteration_count: int  # guards against infinite loops

# ─────────────────────────────────────────────
# 2. TOOLS
# ─────────────────────────────────────────────
TOOLS = [calculator, get_weather, search_web]
MAX_ITERATIONS = 5  # hard cap on reasoning loops

def _get_secret(key: str) -> str:
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")
# ─────────────────────────────────────────────
# 3. LLM
# ─────────────────────────────────────────────
def _get_secret(key: str) -> str:
    """Read from st.secrets (Streamlit Cloud) with os.environ fallback (local)."""
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

OPENROUTER_API_KEY = _get_secret("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not set. Add it to .streamlit/secrets.toml or Streamlit Cloud secrets.")

MODEL_NAME = "meta-llama/llama-3.1-8b-instruct"

llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    model=MODEL_NAME,
    temperature=0,
    max_retries=2,
)

llm_with_tools = llm.bind_tools(TOOLS)

# ─────────────────────────────────────────────
# 4. SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a helpful, accurate AI assistant with access to tools.\n\n"
        "## Available Tools\n"
        "- `calculator` — evaluate math expressions (e.g. '2 + 2', 'sqrt(144)')\n"
        "- `get_weather` — get current weather for a city\n"
        "- `search_web` — search for recent news, facts, or any web information\n\n"
        "## How to respond\n"
        "1. Carefully read the user's question.\n"
        "2. If a tool would help, call it ONCE. Do NOT call multiple tools for the same question.\n"
        "3. After receiving tool output, use it to write a clear, direct answer.\n"
        "4. If no tool is needed, answer directly from your knowledge.\n\n"
        "## Response format\n"
        "Always end with a **Final Answer** section that directly addresses the user's question.\n"
        "Keep answers concise and relevant — avoid unnecessary disclaimers.\n\n"
        "## Rules\n"
        "- Do not call a tool if you already have enough information.\n"
        "- Do not speculate about tool results before calling them.\n"
        "- If a tool returns an error, acknowledge it and answer as best you can.\n"
        "- Never fabricate facts or data.\n"
        "- NEVER wrap your response in HTML tags, div tags, code blocks, or markdown fences.\n"
        "- Always respond in plain text only."
    )
)

# ─────────────────────────────────────────────
# 5. AGENT NODE
# ─────────────────────────────────────────────
def agent_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    iteration = state.get("iteration_count", 0)

    # Inject system prompt once
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM_PROMPT] + messages

    print(f"🤖 Agent thinking... (iteration {iteration + 1})")
    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response],
        "iteration_count": iteration + 1,
    }

# ─────────────────────────────────────────────
# 6. ROUTER
# ─────────────────────────────────────────────
def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state["messages"][-1]
    iteration = state.get("iteration_count", 0)

    # Hard stop to prevent infinite loops
    if iteration >= MAX_ITERATIONS:
        print(f"⚠️  Max iterations ({MAX_ITERATIONS}) reached. Stopping.")
        return "__end__"

    # Tool call requested → execute it
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print(f"🔧 Tool requested: {[t['name'] for t in last_message.tool_calls]}")
        return "tools"

    print("✅ Final answer ready")
    return "__end__"

# ─────────────────────────────────────────────
# 7. BUILD GRAPH
# ─────────────────────────────────────────────
def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "__end__": END,
        },
    )

    graph.add_edge("tools", "agent")

    return graph.compile()

# ─────────────────────────────────────────────
# 8. RESPONSE FORMATTER
# ─────────────────────────────────────────────
def _execute_tool_call(name: str, parameters: dict) -> str:
    """
    Fallback: manually execute a tool when the LLM leaks a raw tool-call JSON
    as its final message content instead of invoking the tool properly.
    """
    tool_map = {t.name: t for t in TOOLS}
    if name not in tool_map:
        return f"(Unknown tool: {name})"
    try:
        return tool_map[name].invoke(parameters)
    except Exception as e:
        return f"(Tool execution error: {e})"


def format_response(raw: str) -> str:
    """
    Clean up LLM output for display.

    Steps:
    1. Detect raw tool-call JSON leaked into content and execute the tool.
    2. Strip markdown code fences and inline backticks.
    3. Strip any raw HTML tags that leaked through.
    4. If 'Final Answer:' exists → return only what comes after it.
    5. Otherwise strip any leading Thoughts block.
    6. Fall back to returning the cleaned text as-is.
    """
    import json

    if not raw:
        return "(No response)"

    text = raw.strip()

    # ── 1. Detect raw tool-call JSON in content ───────────────────────────────
    # Handles both:
    #   {"name": "calculator", "parameters": {"expression": "56000 * 34 / 100"}}
    #   {"name": "calculator", "arguments": {"expression": "56000 * 34 / 100"}}
    try:
        # Strip any surrounding code fences before trying JSON parse
        json_candidate = re.sub(r"```[\w]*\n?", "", text)
        json_candidate = re.sub(r"```", "", json_candidate).strip()
        parsed = json.loads(json_candidate)
        if isinstance(parsed, dict) and "name" in parsed:
            tool_name   = parsed["name"]
            tool_params = parsed.get("parameters", parsed.get("arguments", parsed.get("input", {})))
            if isinstance(tool_params, dict):
                print(f"⚠️  Raw tool-call JSON detected in content. Executing: {tool_name}({tool_params})")
                return _execute_tool_call(tool_name, tool_params)
    except (json.JSONDecodeError, ValueError):
        pass  # Not JSON — continue with normal cleaning

    # ── 2. Strip markdown code fences (```lang ... ``` or ```) ───────────────
    text = re.sub(r"```[\w]*\n?", "", text)   # opening fence with optional lang
    text = re.sub(r"```", "", text)            # closing fence
    text = re.sub(r"`([^`]*)`", r"\1", text)  # inline backticks → plain text

    # ── 3. Strip any raw HTML / XML tags ─────────────────────────────────────
    text = re.sub(r"<[^>]+>", "", text)

    text = text.strip()

    # ── 4. Extract everything after the last "Final Answer" marker ───────────
    # Handles: "Final Answer:", "**Final Answer**", "**Final Answer:**", etc.
    fa_match = re.search(r"(?i)\*{0,2}final\s+answer\*{0,2}\s*:?\s*", text)
    if fa_match:
        return text[fa_match.end():].strip().lstrip("*").strip()

    # ── 5. Strip a leading Thoughts / Reasoning block ────────────────────────
    thought_pattern = re.compile(
        r"(?i)^(thoughts?|reasoning|thinking|chain.of.thought)\s*:.*?(\n\n|\Z)",
        re.DOTALL,
    )
    text = thought_pattern.sub("", text).strip()

    # Also drop any remaining isolated "Thoughts:" header lines
    lines = [
        line for line in text.splitlines()
        if not re.match(r"(?i)^\s*(thoughts?|reasoning)\s*:", line)
    ]
    return "\n".join(lines).strip() or "(No response)"

# ─────────────────────────────────────────────
# 9. RUN
# ─────────────────────────────────────────────
def run_agent(user_input: str) -> str:
    app = build_agent()

    print("\n" + "=" * 55)
    print(f"👤 User: {user_input}")
    print("=" * 55)

    final_state = app.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "iteration_count": 0,
        }
    )

    last_msg = final_state["messages"][-1]

    # Safety net: if the last message is a bare tool-call with no text content,
    # walk back through messages to find the last real text response.
    raw_answer = last_msg.content if last_msg.content else ""
    if not raw_answer.strip():
        for msg in reversed(final_state["messages"]):
            if msg.content and not (hasattr(msg, "tool_calls") and msg.tool_calls):
                raw_answer = msg.content
                break

    answer = format_response(raw_answer)

    print("\n💬 Answer:\n", answer)
    print("=" * 55)
    return answer

# ─────────────────────────────────────────────
# 10. CLI LOOP
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 LangGraph ReAct Agent  |  Model: {MODEL_NAME}")
    print("Type 'exit' to quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            if user_input:
                run_agent(user_input)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
