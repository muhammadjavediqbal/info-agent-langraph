# AI Agent with LangGraph

A minimal but complete ReAct agent using LangGraph + Claude.

## Architecture

```
User Input → [Agent Node] → (conditional edge) → [Tool Node] → (loop back) → [Agent Node] → END
```

The agent runs a **Reason → Act → Observe** loop:
1. LLM receives messages and decides: call a tool or answer directly
2. If tool needed → ToolNode executes it → result appended to state
3. LLM sees result → decides next step
4. Repeat until final answer


## Key LangGraph Concepts

| Concept | What it does |
|---|---|
| `StateGraph` | The graph container; holds nodes + edges |
| `AgentState` | Typed dict passed to every node |
| `add_messages` | Reducer: appends messages instead of replacing |
| `set_entry_point` | Which node runs first |
| `add_conditional_edges` | Route based on state (tool vs end) |
| `ToolNode` | Built-in node that executes tool calls |
| `bind_tools` | Attaches tool schemas to the LLM |
