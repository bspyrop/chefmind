"""
agent/agent.py
LangChain 1.x agent for ChefMind.

LangChain 1.x uses `create_agent` (backed by LangGraph) instead of the old
AgentExecutor. Memory is handled by a `MemorySaver` checkpointer and a
per-session `thread_id` passed at invoke time.
"""

import json
import logging
import re

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from agent.prompts import SYSTEM_PROMPT
from tools.tools import ALL_TOOLS

logger = logging.getLogger(__name__)


# ── Agent factory ─────────────────────────────────────────────────────────────

def build_agent():
    """
    Build and return a LangGraph agent with in-memory checkpointing.

    Memory is scoped per `thread_id`; pass the same thread_id across calls
    to maintain conversation history within a session.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    checkpointer = MemorySaver()

    return create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


# ── UI_JSON extraction ────────────────────────────────────────────────────────

_UI_JSON_PATTERN = re.compile(r"UI_JSON:\s*(\{.*\})", re.DOTALL)


def extract_ui_json(text: str) -> tuple[str, dict]:
    """
    Split the agent's raw output into (display_text, ui_json_dict).

    The UI_JSON line is removed from displayed text so users don't see raw JSON.
    """
    match = _UI_JSON_PATTERN.search(text)
    if not match:
        return text.strip(), {}

    json_str = match.group(1)
    display_text = _UI_JSON_PATTERN.sub("", text).strip()

    try:
        ui_data = json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning("Could not parse UI_JSON: %s", json_str[:200])
        ui_data = {}

    return display_text, ui_data


# ── Run helper ────────────────────────────────────────────────────────────────

def run_agent(
    agent,
    user_input: str,
    thread_id: str = "chefmind-session",
) -> tuple[str, dict, list[dict]]:
    """
    Invoke the agent and return (display_text, ui_json_dict, tool_calls_list).

    Args:
        agent:      The compiled LangGraph agent from build_agent()
        user_input: The user's chat message
        thread_id:  Session identifier for memory continuity

    Returns:
        display_text  — the assistant's response with UI_JSON stripped out
        ui_json       — parsed UI_JSON dict for updating Streamlit panels
        tool_calls    — list of {tool, input, output} dicts for the Tools panel
    """
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 12,   # max tool-call rounds before forcing a final answer
    }
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )

    messages = result.get("messages", [])

    # Extract the last AI message as the final response
    ai_messages = [m for m in messages if isinstance(m, AIMessage) and not m.tool_calls]
    raw_output: str = ai_messages[-1].content if ai_messages else ""

    # Extract tool calls + results for the UI panel
    # LangGraph returns the full message history; find AIMessages with tool_calls
    # and match them to their ToolMessage responses.
    tool_calls: list[dict] = []
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                # Find the corresponding ToolMessage by tool_call_id
                tool_result = ""
                for j in range(i + 1, len(messages)):
                    if (
                        isinstance(messages[j], ToolMessage)
                        and messages[j].tool_call_id == tc["id"]
                    ):
                        tool_result = messages[j].content
                        break
                tool_calls.append({
                    "tool": tc["name"],
                    "input": tc["args"],
                    "output": str(tool_result),  # full output; truncation happens in app.py display
                })

    display_text, ui_json = extract_ui_json(raw_output)
    return display_text, ui_json, tool_calls
