# test_rss_mcp.py
import sys
sys.path.insert(0, "tests")

from mcp_servers.rss_mcp.server import (
    search_security_feeds,
    get_latest_from_feed,
    list_available_feeds
)

print("=== Available feeds ===")
feeds = list_available_feeds()
for f in feeds["feeds"]:
    print(f"  [{f['key']}] {f['name']} — {f['description']}")

print("\n=== Latest from CISA ===")
cisa = get_latest_from_feed(source="cisa_advisories", limit=3)
print(f"  Fetched {cisa['total']} articles")
for r in cisa["results"]:
    print(f"  {r['published_at'][:10]} | {r['title'][:80]}")
    print(f"    {r['url']}")

print("\n=== Searching all feeds for 'vulnerability' ===")
results = search_security_feeds(query="anthropic", limit=5)
print(f"  Total matches: {results['total_matches']}")
for r in results["results"]:
    print(f"  [{r['source_name']}] {r['title'][:70]}")
    print(f"    {r['url']}")