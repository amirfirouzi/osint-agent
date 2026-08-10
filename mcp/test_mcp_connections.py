# test_mcp_connections.py

import asyncio
import json
import sys
from agent.mcp_clients import get_mcp_client


async def test_connections():
    print("\n🔌 Testing MCP server connections...\n")

    client = get_mcp_client()
    tools  = await client.get_tools()

    print(f"✓ Connected to all servers. Total tools available: {len(tools)}\n")

    for tool in tools:
        print(f"  🔧 {tool.name}")
        print(f"     {(tool.description or '')[:80]}...")
        print()


async def test_single_tool():
    print("\n🧪 Testing one tool call per server...\n")

    client  = get_mcp_client()
    tools   = await client.get_tools()

    def find(fragment: str):
        return next((t for t in tools if fragment in t.name), None)

    def parse_result(result):
        """Handle both string JSON and already-parsed objects."""
        if isinstance(result, str):
            import json
            return json.loads(result)
        return result

    # ── HackerNews ────────────────────────────────────────────────────────────
    print("[ HackerNews ] search_hackernews")
    tool = find("search_hackernews")
    if tool:
        result = await tool.ainvoke({"query": "openssl", "hours_ago": 720, "limit": 2})
        data   = parse_result(result)
        hits   = data.get("results", data) if isinstance(data, dict) else data
        print(f"  ✓ Got {len(hits)} results")
        for h in (hits if isinstance(hits, list) else []):
            print(f"    - {h.get('title', str(h))[:70]}")
    print()

    # ── RSS ───────────────────────────────────────────────────────────────────
    print("[ RSS ] get_latest_from_feed")
    tool = find("get_latest_from_feed")
    if tool:
        result = await tool.ainvoke({"source": "krebs", "limit": 2})
        data   = parse_result(result)
        hits   = data.get("results", data) if isinstance(data, dict) else data
        print(f"  ✓ Got {len(hits)} articles")
        for h in (hits if isinstance(hits, list) else []):
            print(f"    - {h.get('title', str(h))[:70]}")
    print()

    # ── Elasticsearch ─────────────────────────────────────────────────────────
    print("[ Elasticsearch ] get_knowledge_base_stats")
    tool = find("get_knowledge_base_stats")
    if tool:
        result = await tool.ainvoke({})
        data   = parse_result(result)
        if isinstance(data, dict):
            print(f"  ✓ Total indicators: {data.get('total_indicators')}")
            print(f"    By type:          {data.get('indicators_by_type')}")
        else:
            print(f"  ✓ Result: {str(data)[:120]}")
    print()

    # ── GitHub ────────────────────────────────────────────────────────────────
    print("[ GitHub ] search_repositories")
    tool = find("search_repositories")
    if tool:
        result = await tool.ainvoke({"query": "openssl vulnerability CVE"})
        data   = parse_result(result)
        if isinstance(data, dict):
            items = data.get("items", data.get("repositories", []))
        else:
            items = data if isinstance(data, list) else []
        print(f"  ✓ Got {len(items)} repositories")
        for r in items[:3]:
            if isinstance(r, dict):
                print(f"    - {r.get('full_name', '')}: ⭐ {r.get('stargazers_count', 0)}")
    print()

    print("✅ All servers responding.\n")


if __name__ == "__main__":
    asyncio.run(test_connections())
    asyncio.run(test_single_tool())