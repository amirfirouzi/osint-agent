# agent/osint_agent.py

import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from mcp.agent.mcp_clients import get_mcp_client
from mcp.agent.prompts import SYSTEM_PROMPT

load_dotenv()


def create_agent(tools: list):
    """Create a ReAct agent with Claude and the provided tools."""
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0,
        max_tokens=8096,
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
    return agent


async def run_investigation(query: str) -> str:
    """
    Run a full OSINT investigation for a given query.
    Returns the agent's final response.
    """
    print(f"\n{'='*60}")
    print(f"  OSINT Investigation")
    print(f"  Query: {query}")
    print(f"{'='*60}\n")

    # get all tools from MCP servers
    client = get_mcp_client()
    tools  = await client.get_tools()

    print(f"✓ {len(tools)} tools loaded from MCP servers\n")

    # create agent
    agent = create_agent(tools)

    # run the investigation
    messages = [{"role": "user", "content": query}]

    print("── Agent thinking ──────────────────────────────────────\n")

    final_response = ""
    step_count     = 0

    async for chunk in agent.astream(
        {"messages": messages},
        stream_mode="updates",
    ):
        for node_name, node_output in chunk.items():

            if node_name == "agent":
                messages_out = node_output.get("messages", [])
                for msg in messages_out:
                    # tool call — show what the agent decided to do
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            step_count += 1
                            args_preview = str(tc.get("args", {}))[:80]
                            print(f"  [{step_count}] 🔧 {tc['name']}({args_preview}...)")

                    # final text response
                    elif hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
                        final_response = msg.content

            elif node_name == "tools":
                messages_out = node_output.get("messages", [])
                for msg in messages_out:
                    if hasattr(msg, "name") and hasattr(msg, "content"):
                        content_preview = str(msg.content)[:100].replace("\n", " ")
                        print(f"       ↳ {msg.name}: {content_preview}...")

    print(f"\n── Investigation complete ({step_count} tool calls) ──────────\n")
    return final_response