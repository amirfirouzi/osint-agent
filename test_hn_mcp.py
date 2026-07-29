# test_hn_mcp.py
import sys
sys.path.insert(0, "tests")

from mcp_servers.hackernews_mcp.server import search_hackernews, get_hackernews_top_stories

print("=== Searching HN for 'openssl' ===")
result = search_hackernews(query="anthropic vulnerability", hours_ago=720, limit=3)
print(f"Total found: {result['total']}")
for r in result["results"]:
    print(f"  [{r['points']} pts] {r['title']}")
    print(f"    {r['hn_url']}")

print("\n=== Top HN stories right now ===")
top = get_hackernews_top_stories(limit=5)
for r in top["results"]:
    print(f"  [{r['points']} pts] {r['title']}")