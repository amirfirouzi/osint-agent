# data/setup_indices.py
"""
Creates three Elasticsearch indices:
  - threat_indicators  : known IOCs, actor profiles, CVEs
  - intelligence_reports : synthesized reports the agent writes
  - raw_signals        : raw ingested data from external sources
"""

import os
import sys
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

es = Elasticsearch(
    os.getenv("ES_HOST", "http://localhost:9200"),
    basic_auth=(
        os.getenv("ES_USERNAME", "elastic"),
        os.getenv("ES_PASSWORD", "osint_password")
    )
)

def create_indices():
    # ── 1. threat_indicators ─────────────────────────────────────────────────
    if not es.indices.exists(index="threat_indicators"):
        es.indices.create(
            index="threat_indicators",
            body={
                "mappings": {
                    "properties": {
                        "indicator_id":  {"type": "keyword"},
                        "type":          {"type": "keyword"},   # cve, actor, domain, ip, campaign
                        "value":         {"type": "keyword"},
                        "description":   {"type": "text"},
                        "tags":          {"type": "keyword"},
                        "severity":      {"type": "keyword"},   # critical, high, medium, low
                        "source":        {"type": "keyword"},
                        "first_seen":    {"type": "date"},
                        "last_seen":     {"type": "date"},
                        "related_to":    {"type": "keyword"},   # list of related indicator_ids
                        "metadata":      {"type": "object", "enabled": False}
                    }
                }
            }
        )
        print("✓ Created index: threat_indicators")
    else:
        print("  Index already exists: threat_indicators")

    # ── 2. intelligence_reports ───────────────────────────────────────────────
    if not es.indices.exists(index="intelligence_reports"):
        es.indices.create(
            index="intelligence_reports",
            body={
                "mappings": {
                    "properties": {
                        "report_id":     {"type": "keyword"},
                        "title":         {"type": "text"},
                        "summary":       {"type": "text"},
                        "full_report":   {"type": "text"},
                        "topic":         {"type": "keyword"},
                        "sources_used":  {"type": "keyword"},
                        "indicators_found": {"type": "keyword"},
                        "severity":      {"type": "keyword"},
                        "created_at":    {"type": "date"},
                        "tags":          {"type": "keyword"}
                    }
                }
            }
        )
        print("✓ Created index: intelligence_reports")
    else:
        print("  Index already exists: intelligence_reports")

    # ── 3. raw_signals ────────────────────────────────────────────────────────
    if not es.indices.exists(index="raw_signals"):
        es.indices.create(
            index="raw_signals",
            body={
                "mappings": {
                    "properties": {
                        "signal_id":     {"type": "keyword"},
                        "source":        {"type": "keyword"},   # github, reddit, hackernews, rss
                        "source_url":    {"type": "keyword"},
                        "title":         {"type": "text"},
                        "content":       {"type": "text"},
                        "author":        {"type": "keyword"},
                        "topic_tags":    {"type": "keyword"},
                        "collected_at":  {"type": "date"},
                        "score":         {"type": "integer"},   # upvotes/stars/points
                        "metadata":      {"type": "object", "enabled": False}
                    }
                }
            }
        )
        print("✓ Created index: raw_signals")
    else:
        print("  Index already exists: raw_signals")

    print("\n✓ All indices ready.")


if __name__ == "__main__":
    try:
        info = es.info()
        print(f"✓ Connected to Elasticsearch {info['version']['number']}\n")
    except Exception as e:
        print(f"✗ Cannot connect to Elasticsearch: {e}")
        print("  Make sure Docker is running: docker compose up -d")
        sys.exit(1)

    create_indices()