# test_es_mcp.py
import sys
sys.path.insert(0, "tests")

from mcp_servers.elasticsearch_mcp.server import (
    search_threat_indicators,
    get_knowledge_base_stats,
    get_related_indicators
)

print("=== Knowledge base stats ===")
stats = get_knowledge_base_stats()
print(f"  Total indicators: {stats['total_indicators']}")
print(f"  By type: {stats['indicators_by_type']}")
print(f"  By severity: {stats['indicators_by_severity']}")

print("\n=== Searching for 'openssl tls' ===")
results = search_threat_indicators(query="openssl tls", limit=3)
print(f"  Matches: {results['total_matches']}")
for m in results["matches"]:
    print(f"  [{m['severity'].upper()}] {m['indicator_id']}: {m['description'][:80]}...")

print("\n=== Related indicators for CVE-2024-0001 ===")
related = get_related_indicators("CVE-2024-0001")
print(f"  Related to: {[r['indicator_id'] for r in related.get('related', [])]}")