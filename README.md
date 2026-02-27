# 🤖 MVP AI Agent with LangGraph

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

## Project Structure

```
langgraph-agent/
├── agent.py              # Main graph definition & entry point
├── test_agent.py         # Example test queries
├── graph_diagram.py      # Prints the graph structure
├── requirements.txt
└── tools/
    ├── __init__.py
    ├── calculator.py     # Safe math evaluator
    ├── weather.py        # Weather lookup (simulated)
    └── search.py         # Web search (simulated)
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."


# 3. Run the interactive agent
python agent.py

# 4. Run test suite
python test_agent.py

# 5. View graph structure
python graph_diagram.py
```

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

## Upgrading to Production

### Real Web Search (Tavily)
```python
# pip install tavily-python
from langchain_community.tools.tavily_search import TavilySearchResults
search = TavilySearchResults(max_results=3)
TOOLS = [calculator, get_weather, search]
```

### Real Weather (OpenWeatherMap)
```python
import requests
def get_weather(city: str) -> str:
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}"
    return requests.get(url).json()
```

### Persistent Memory (Checkpointing)
```python
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("agent_memory.db")
app = graph.compile(checkpointer=checkpointer)

# Now pass thread_id to maintain conversation across sessions
config = {"configurable": {"thread_id": "user_123"}}
app.invoke({"messages": [HumanMessage(content="Hello")]}, config=config)
```

### Human-in-the-Loop
```python
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
app = graph.compile(
    checkpointer=memory,
    interrupt_before=["tools"]  # Pause BEFORE any tool execution
)
# Call app.invoke() to reach the interrupt
# User reviews the tool call
# Call app.invoke(None, config) to resume
```

## Extending the Agent

To add a new tool, just:
1. Create `tools/my_tool.py` with `@tool` decorator
2. Add it to `TOOLS` list in `agent.py`

That's it — the graph automatically routes to it.
